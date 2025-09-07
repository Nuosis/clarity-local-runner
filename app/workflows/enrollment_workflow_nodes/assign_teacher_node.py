"""
Simple rule-based teacher assignment node.
"""

import logging
from typing import Any, Dict, Optional

from core.nodes.base import Node
from core.task import TaskContext
from database.session import db_session
from models.student import Student
from models.teacher import Teacher
from sqlalchemy.orm import Session


class AssignTeacherNode(Node):
    """Simple rule-based teacher assignment."""

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Simple rule-based teacher assignment.

        Assigns teacher based on:
        - Find teachers for requested instrument
        - Check teacher availability and capacity
        - Assign first available teacher (simple algorithm)
        - Update student record with teacher assignment

        Args:
            task_context: The task context containing account creation results

        Returns:
            Updated task context with teacher assignment results
        """
        try:
            logging.info(f"Starting {self.node_name} teacher assignment")

            # Check if account creation was successful
            account_results = task_context.nodes.get("CreateStudentAccountNode", {})
            if not account_results.get("success", False):
                logging.error("Cannot assign teacher - account creation failed")
                task_context.update_node(
                    self.node_name,
                    success=False,
                    error="Account creation failed - cannot assign teacher",
                )
                task_context.stop_workflow()
                return task_context

            # Get student ID and enrollment data
            student_id = account_results.get("student_id")
            if not student_id:
                raise Exception("Student ID not found in account creation results")

            # Get validated data from previous nodes
            validation_results = task_context.nodes.get("ValidateEnrollmentNode", {})
            validated_data = validation_results.get("validated_data", {})
            instrument = validated_data.get("instrument")

            if not instrument:
                raise Exception("Instrument not found in validation results")

            # Initialize assignment results
            assignment_results = {
                "success": False,
                "teacher_id": None,
                "teacher_name": None,
                "assignment_method": "rule_based_simple",
                "available_teachers": 0,
                "assignment_reason": None,
            }

            # Get database session
            db_session_gen = db_session()
            db_session_obj = next(db_session_gen)

            try:
                # Find available teachers for the instrument
                available_teachers = await self._find_available_teachers(
                    db_session_obj, instrument
                )

                assignment_results["available_teachers"] = len(available_teachers)
                logging.info(
                    f"Found {len(available_teachers)} available teachers for {instrument}"
                )

                if not available_teachers:
                    assignment_results["assignment_reason"] = (
                        f"No available teachers found for {instrument}"
                    )
                    logging.warning(
                        f"No available teachers found for instrument: {instrument}"
                    )
                    # Don't stop workflow - this could be handled by admin later
                    task_context.update_node(self.node_name, **assignment_results)
                    return task_context

                # Select teacher using simple algorithm (first available with lowest student count)
                selected_teacher = await self._select_teacher_simple_algorithm(
                    db_session_obj, available_teachers
                )

                if not selected_teacher:
                    assignment_results["assignment_reason"] = (
                        "Teacher selection algorithm failed"
                    )
                    logging.error("Teacher selection algorithm failed")
                    task_context.update_node(self.node_name, **assignment_results)
                    return task_context

                # Assign teacher to student
                assignment_success = await self._assign_teacher_to_student(
                    db_session_obj, student_id, selected_teacher.id
                )

                if assignment_success:
                    assignment_results["success"] = True
                    assignment_results["teacher_id"] = selected_teacher.id
                    assignment_results["teacher_name"] = (
                        f"{selected_teacher.user.first_name} {selected_teacher.user.last_name}"
                    )
                    assignment_results["assignment_reason"] = (
                        f"Assigned to teacher with lowest student count ({await self._get_teacher_student_count(db_session_obj, selected_teacher.id)} students)"
                    )

                    # Commit the assignment
                    db_session_obj.commit()

                    logging.info(
                        f"Successfully assigned teacher {assignment_results['teacher_name']} to student {student_id}"
                    )
                else:
                    assignment_results["assignment_reason"] = (
                        "Failed to update student record with teacher assignment"
                    )
                    logging.error("Failed to assign teacher to student")

            except Exception as e:
                db_session_obj.rollback()
                raise e
            finally:
                db_session_obj.close()

            # Store assignment results in task context
            task_context.update_node(self.node_name, **assignment_results)

            return task_context

        except Exception as e:
            logging.error(f"Error in {self.node_name}: {str(e)}")
            task_context.update_node(
                self.node_name,
                success=False,
                error=str(e),
                assignment_reason=f"Error during assignment: {str(e)}",
            )
            task_context.stop_workflow()
            return task_context

    async def _find_available_teachers(
        self, db_session_obj: Session, instrument: str
    ) -> list[Teacher]:
        """Find available teachers for the specified instrument."""
        try:
            # Query teachers who:
            # 1. Teach the requested instrument
            # 2. Are available (is_available = True)
            # 3. Have not reached their maximum student capacity
            available_teachers = (
                db_session_obj.query(Teacher)
                .join(Teacher.user)
                .filter(
                    Teacher.instruments.contains(
                        [instrument]
                    ),  # PostgreSQL array contains
                    Teacher.is_available == True,
                    Teacher.user.is_active == True,
                )
                .all()
            )

            # Filter by capacity (check current student count vs max_students)
            capacity_filtered_teachers = []
            for teacher in available_teachers:
                current_student_count = await self._get_teacher_student_count(
                    db_session_obj, teacher.id
                )
                if current_student_count < teacher.max_students:
                    capacity_filtered_teachers.append(teacher)
                    logging.debug(
                        f"Teacher {teacher.user.first_name} {teacher.user.last_name}: {current_student_count}/{teacher.max_students} students"
                    )
                else:
                    logging.debug(
                        f"Teacher {teacher.user.first_name} {teacher.user.last_name} at capacity: {current_student_count}/{teacher.max_students} students"
                    )

            return capacity_filtered_teachers

        except Exception as e:
            logging.error(f"Error finding available teachers: {str(e)}")
            return []

    async def _get_teacher_student_count(
        self, db_session_obj: Session, teacher_id: int
    ) -> int:
        """Get current active student count for a teacher."""
        try:
            student_count = (
                db_session_obj.query(Student)
                .filter(Student.teacher_id == teacher_id, Student.is_active == True)
                .count()
            )
            return student_count
        except Exception as e:
            logging.error(f"Error getting teacher student count: {str(e)}")
            return 0

    async def _select_teacher_simple_algorithm(
        self, db_session_obj: Session, available_teachers: list[Teacher]
    ) -> Optional[Teacher]:
        """
        Select teacher using simple algorithm.

        Algorithm: Select teacher with the lowest current student count.
        If tied, select the first one (could be enhanced with other criteria).
        """
        try:
            if not available_teachers:
                return None

            # Calculate current student count for each teacher
            teacher_loads = []
            for teacher in available_teachers:
                student_count = await self._get_teacher_student_count(
                    db_session_obj, teacher.id
                )
                teacher_loads.append(
                    {
                        "teacher": teacher,
                        "student_count": student_count,
                        "capacity_ratio": student_count / teacher.max_students,
                    }
                )

            # Sort by student count (ascending), then by capacity ratio
            teacher_loads.sort(key=lambda x: (x["student_count"], x["capacity_ratio"]))

            selected_teacher = teacher_loads[0]["teacher"]
            logging.info(
                f"Selected teacher: {selected_teacher.user.first_name} {selected_teacher.user.last_name} "
                f"({teacher_loads[0]['student_count']}/{selected_teacher.max_students} students)"
            )

            return selected_teacher

        except Exception as e:
            logging.error(f"Error in teacher selection algorithm: {str(e)}")
            return None

    async def _assign_teacher_to_student(
        self, db_session_obj: Session, student_id: int, teacher_id: int
    ) -> bool:
        """Assign teacher to student by updating the student record."""
        try:
            # Get the student record
            student = (
                db_session_obj.query(Student).filter(Student.id == student_id).first()
            )

            if not student:
                logging.error(f"Student with ID {student_id} not found")
                return False

            # Check if student already has a teacher assigned
            if student.teacher_id:
                logging.warning(
                    f"Student {student_id} already has teacher {student.teacher_id} assigned, updating to {teacher_id}"
                )

            # Assign the teacher
            student.teacher_id = teacher_id
            db_session_obj.flush()  # Ensure the change is persisted

            logging.info(
                f"Successfully assigned teacher {teacher_id} to student {student_id}"
            )
            return True

        except Exception as e:
            logging.error(f"Error assigning teacher to student: {str(e)}")
            return False
