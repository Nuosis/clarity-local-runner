"""
Schedule initial demo lesson node.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from core.nodes.base import Node
from core.task import TaskContext
from database.session import db_session
from models.lesson import Lesson
from models.student import Student
from models.teacher import Teacher, TeacherAvailability
from sqlalchemy.orm import Session


class ScheduleDemoLessonNode(Node):
    """Schedule initial demo lesson."""

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Schedule initial demo lesson.

        Schedules:
        - Find next available slot for assigned teacher
        - Create demo lesson record
        - Block time in teacher's schedule

        Args:
            task_context: The task context containing teacher assignment results

        Returns:
            Updated task context with demo lesson scheduling results
        """
        try:
            logging.info(f"Starting {self.node_name} demo lesson scheduling")

            # Check if teacher assignment was successful
            assignment_results = task_context.nodes.get("AssignTeacherNode", {})
            if not assignment_results.get("success", False):
                logging.warning(
                    "Teacher assignment not successful - scheduling demo lesson anyway for manual assignment"
                )
                # Don't stop workflow - demo lesson can be scheduled later by admin
                task_context.update_node(
                    self.node_name,
                    success=False,
                    error="Teacher assignment failed - demo lesson not scheduled",
                    requires_manual_scheduling=True,
                )
                return task_context

            # Get teacher and student information
            teacher_id = assignment_results.get("teacher_id")
            account_results = task_context.nodes.get("CreateStudentAccountNode", {})
            student_id = account_results.get("student_id")

            if not teacher_id or not student_id:
                raise Exception(
                    f"Missing required IDs - teacher_id: {teacher_id}, student_id: {student_id}"
                )

            # Initialize scheduling results
            scheduling_results = {
                "success": False,
                "demo_lesson_id": None,
                "scheduled_at": None,
                "teacher_id": teacher_id,
                "student_id": student_id,
                "duration_minutes": 30,  # Standard demo lesson duration
                "scheduling_method": "next_available_slot",
                "requires_manual_scheduling": False,
            }

            # Get database session
            db_session_gen = db_session()
            db_session_obj = next(db_session_gen)

            try:
                # Find next available slot for the teacher
                next_slot = await self._find_next_available_slot(
                    db_session_obj, teacher_id
                )

                if not next_slot:
                    scheduling_results["requires_manual_scheduling"] = True
                    scheduling_results["error"] = (
                        "No available slots found for teacher in next 2 weeks"
                    )
                    logging.warning(
                        f"No available slots found for teacher {teacher_id}"
                    )
                    task_context.update_node(self.node_name, **scheduling_results)
                    return task_context

                # Create demo lesson record
                demo_lesson = await self._create_demo_lesson(
                    db_session_obj, student_id, teacher_id, next_slot
                )

                if demo_lesson:
                    scheduling_results["success"] = True
                    scheduling_results["demo_lesson_id"] = demo_lesson.id
                    scheduling_results["scheduled_at"] = (
                        demo_lesson.scheduled_at.isoformat()
                    )

                    # Commit the lesson creation
                    db_session_obj.commit()

                    logging.info(
                        f"Successfully scheduled demo lesson {demo_lesson.id} for {demo_lesson.scheduled_at}"
                    )
                else:
                    scheduling_results["error"] = "Failed to create demo lesson record"
                    logging.error("Failed to create demo lesson record")

            except Exception as e:
                db_session_obj.rollback()
                raise e
            finally:
                db_session_obj.close()

            # Store scheduling results in task context
            task_context.update_node(self.node_name, **scheduling_results)

            return task_context

        except Exception as e:
            logging.error(f"Error in {self.node_name}: {str(e)}")
            task_context.update_node(
                self.node_name,
                success=False,
                error=str(e),
                requires_manual_scheduling=True,
            )
            # Don't stop workflow - demo lesson scheduling failure shouldn't block enrollment
            return task_context

    async def _find_next_available_slot(
        self, db_session_obj: Session, teacher_id: int
    ) -> Optional[datetime]:
        """
        Find the next available slot for the teacher.

        Simple algorithm:
        1. Get teacher's availability schedule
        2. Look for next available slot in the next 2 weeks
        3. Check against existing lessons to avoid conflicts
        """
        try:
            # Get teacher's availability
            teacher_availability = (
                db_session_obj.query(TeacherAvailability)
                .filter(
                    TeacherAvailability.teacher_id == teacher_id,
                    TeacherAvailability.is_active == True,
                    TeacherAvailability.is_recurring == True,
                )
                .all()
            )

            if not teacher_availability:
                logging.warning(
                    f"No availability schedule found for teacher {teacher_id}"
                )
                return None

            # Look for slots in the next 2 weeks
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_date = start_date + timedelta(days=14)

            # Generate potential slots based on teacher availability
            potential_slots = []
            current_date = start_date

            while current_date <= end_date:
                day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
                # Convert to our format (0=Sunday, 6=Saturday)
                our_day_format = (day_of_week + 1) % 7

                # Check if teacher is available on this day
                day_availability = [
                    av
                    for av in teacher_availability
                    if av.day_of_week == our_day_format
                ]

                for availability in day_availability:
                    # Generate hourly slots within availability window
                    slot_time = datetime.combine(
                        current_date.date(), availability.start_time
                    )
                    end_time = datetime.combine(
                        current_date.date(), availability.end_time
                    )

                    while slot_time + timedelta(minutes=30) <= end_time:
                        # Skip past slots
                        if slot_time > datetime.now():
                            potential_slots.append(slot_time)
                        slot_time += timedelta(hours=1)  # Check hourly slots

                current_date += timedelta(days=1)

            # Sort slots by date
            potential_slots.sort()

            # Check each slot for conflicts
            for slot in potential_slots:
                if await self._is_slot_available(db_session_obj, teacher_id, slot):
                    return slot

            return None

        except Exception as e:
            logging.error(f"Error finding next available slot: {str(e)}")
            return None

    async def _is_slot_available(
        self, db_session_obj: Session, teacher_id: int, slot_time: datetime
    ) -> bool:
        """Check if a specific time slot is available (no existing lessons)."""
        try:
            # Check for existing lessons at this time
            slot_end_time = slot_time + timedelta(minutes=30)

            existing_lesson = (
                db_session_obj.query(Lesson)
                .filter(
                    Lesson.teacher_id == teacher_id,
                    Lesson.scheduled_at >= slot_time,
                    Lesson.scheduled_at < slot_end_time,
                    Lesson.status.in_(
                        ["scheduled", "completed"]
                    ),  # Don't count cancelled lessons
                )
                .first()
            )

            return existing_lesson is None

        except Exception as e:
            logging.error(f"Error checking slot availability: {str(e)}")
            return False

    async def _create_demo_lesson(
        self,
        db_session_obj: Session,
        student_id: int,
        teacher_id: int,
        scheduled_at: datetime,
    ) -> Optional[Lesson]:
        """Create a demo lesson record."""
        try:
            # Get student and teacher for validation
            student = (
                db_session_obj.query(Student).filter(Student.id == student_id).first()
            )
            teacher = (
                db_session_obj.query(Teacher).filter(Teacher.id == teacher_id).first()
            )

            if not student or not teacher:
                logging.error(f"Student {student_id} or teacher {teacher_id} not found")
                return None

            # Create demo lesson
            demo_lesson = Lesson(
                student_id=student_id,
                teacher_id=teacher_id,
                scheduled_at=scheduled_at,
                duration_minutes=30,
                lesson_type="demo",
                status="scheduled",
                payment_status="pending",  # Demo lessons might be free or paid
                attendance_marked=False,
                teacher_notes="Demo lesson - initial assessment and introduction",
                student_progress_notes=None,
            )

            db_session_obj.add(demo_lesson)
            db_session_obj.flush()  # Get the ID without committing

            logging.info(
                f"Created demo lesson {demo_lesson.id} for student {student_id} with teacher {teacher_id}"
            )
            return demo_lesson

        except Exception as e:
            logging.error(f"Error creating demo lesson: {str(e)}")
            return None

    async def _get_preferred_time_slots(
        self, preferred_schedule: Optional[str]
    ) -> list[int]:
        """
        Parse preferred schedule and return preferred hours.

        This is a simple implementation - could be enhanced with more sophisticated parsing.
        """
        if not preferred_schedule:
            return list(range(9, 18))  # Default: 9 AM to 6 PM

        # Simple parsing for common preferences
        preferred_schedule_lower = preferred_schedule.lower()

        if "morning" in preferred_schedule_lower:
            return list(range(9, 12))  # 9 AM to 12 PM
        elif "afternoon" in preferred_schedule_lower:
            return list(range(12, 17))  # 12 PM to 5 PM
        elif "evening" in preferred_schedule_lower:
            return list(range(17, 20))  # 5 PM to 8 PM
        elif "weekend" in preferred_schedule_lower:
            return list(range(9, 18))  # Full day on weekends
        else:
            return list(range(9, 18))  # Default: 9 AM to 6 PM
