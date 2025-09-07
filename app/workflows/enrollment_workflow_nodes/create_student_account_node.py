"""
Create student and parent accounts in Supabase node.
"""

import logging
import os
import secrets
import string
from datetime import date
from typing import Any, Dict

from core.nodes.base import Node
from core.task import TaskContext
from database.session import db_session
from models.student import Student
from models.user import User
from sqlalchemy.orm import Session
from supabase import create_client


class CreateStudentAccountNode(Node):
    """Create student and parent accounts in Supabase."""

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Create student and parent accounts in Supabase.

        Creates:
        - Parent user account with temporary password
        - Student record with parent relationship
        - Welcome credentials for login

        Args:
            task_context: The task context containing validated enrollment data

        Returns:
            Updated task context with account creation results
        """
        account_results = {
            "success": False,
            "parent_user_id": None,
            "student_id": None,
            "temporary_password": None,
            "accounts_created": [],
        }

        try:
            logging.info(f"Starting {self.node_name} account creation")

            # Check if validation passed
            validation_results = task_context.nodes.get("ValidateEnrollmentNode", {})
            if not validation_results.get("is_valid", False):
                logging.error("Cannot create accounts - validation failed")
                task_context.update_node(
                    self.node_name,
                    success=False,
                    error="Validation failed - cannot create accounts",
                )
                task_context.stop_workflow()
                return task_context

            # Get validated data
            validated_data = validation_results.get("validated_data", {})
            parent_info = validated_data.get("parent_info", {})
            enrollment_event = task_context.event

            # Generate temporary password for parent
            temp_password = self._generate_temporary_password()
            account_results["temporary_password"] = temp_password

            # Get database session
            db_session_gen = db_session()
            db_session_obj = next(db_session_gen)

            try:
                # Create parent user account in Supabase
                parent_account = await self._create_parent_supabase_account(
                    parent_info, temp_password
                )

                if not parent_account["success"]:
                    raise Exception(
                        f"Failed to create parent Supabase account: {parent_account['error']}"
                    )

                account_results["accounts_created"].append("parent_supabase")
                logging.info(
                    f"Parent Supabase account created: {parent_account['user_id']}"
                )

                # Create parent user record in database
                parent_user = await self._create_parent_user_record(
                    db_session_obj, parent_info, parent_account["user_id"]
                )

                account_results["parent_user_id"] = parent_user.id
                account_results["accounts_created"].append("parent_user_record")
                logging.info(f"Parent user record created: {parent_user.id}")

                # Create student record
                student = await self._create_student_record(
                    db_session_obj, enrollment_event, validated_data, parent_user.id
                )

                account_results["student_id"] = student.id
                account_results["accounts_created"].append("student_record")
                logging.info(f"Student record created: {student.id}")

                # Commit all database changes
                db_session_obj.commit()
                account_results["success"] = True

                logging.info(
                    f"{self.node_name} completed successfully - accounts created"
                )

            except Exception as e:
                # Rollback database changes
                db_session_obj.rollback()

                # Attempt to cleanup Supabase account if it was created
                if "parent_supabase" in account_results["accounts_created"]:
                    await self._cleanup_supabase_account(parent_account.get("user_id"))

                raise e

            finally:
                db_session_obj.close()

            # Store account creation results in task context
            task_context.update_node(self.node_name, **account_results)

            return task_context

        except Exception as e:
            logging.error(f"Error in {self.node_name}: {str(e)}")
            task_context.update_node(
                self.node_name,
                success=False,
                error=str(e),
                accounts_created=account_results.get("accounts_created", []),
            )
            task_context.stop_workflow()
            return task_context

    def _generate_temporary_password(self) -> str:
        """Generate a secure temporary password."""
        # Generate 12-character password with letters, digits, and symbols
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(secrets.choice(alphabet) for _ in range(12))

        # Ensure password has at least one of each type
        if not any(c.islower() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_lowercase)
        if not any(c.isupper() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_uppercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + secrets.choice(string.digits)

        return password

    async def _create_parent_supabase_account(
        self, parent_info: Dict[str, Any], password: str
    ) -> Dict[str, Any]:
        """Create parent account in Supabase Auth."""
        try:
            # Initialize Supabase client
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv(
                "SERVICE_ROLE_KEY"
            )  # Use service role key for admin operations

            if not supabase_url or not supabase_key:
                raise Exception("Supabase configuration missing")

            supabase = create_client(supabase_url, supabase_key)

            # Create user in Supabase
            auth_response = supabase.auth.admin.create_user(
                {
                    "email": parent_info["parent_email"],
                    "password": password,
                    "user_metadata": {
                        "first_name": parent_info["parent_first_name"],
                        "last_name": parent_info["parent_last_name"],
                        "role": "PARENT",
                        "phone": parent_info.get("parent_phone"),
                    },
                }
            )

            if hasattr(auth_response, "user") and auth_response.user:
                return {
                    "success": True,
                    "error": None,
                    "user_id": auth_response.user.id,
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create user in Supabase",
                    "user_id": None,
                }

        except Exception as e:
            logging.error(f"Error creating Supabase account: {str(e)}")
            return {"success": False, "error": str(e), "user_id": None}

    async def _create_parent_user_record(
        self,
        db_session_obj: Session,
        parent_info: Dict[str, Any],
        supabase_user_id: str,
    ) -> User:
        """Create parent user record in database."""
        try:
            # Check if user already exists
            existing_user = (
                db_session_obj.query(User)
                .filter(User.email == parent_info["parent_email"])
                .first()
            )

            if existing_user:
                raise Exception(
                    f"User with email {parent_info['parent_email']} already exists"
                )

            # Create new user record
            parent_user = User(
                supabase_user_id=supabase_user_id,
                email=parent_info["parent_email"],
                first_name=parent_info["parent_first_name"],
                last_name=parent_info["parent_last_name"],
                phone=parent_info.get("parent_phone"),
                role="PARENT",
                is_active=True,
            )

            db_session_obj.add(parent_user)
            db_session_obj.flush()  # Get the ID without committing

            return parent_user

        except Exception as e:
            logging.error(f"Error creating parent user record: {str(e)}")
            raise e

    async def _create_student_record(
        self,
        db_session_obj: Session,
        enrollment_event,
        validated_data: Dict[str, Any],
        parent_user_id: int,
    ) -> Student:
        """Create student record in database."""
        try:
            # Check if student already exists
            existing_student = (
                db_session_obj.query(Student)
                .filter(
                    Student.first_name == enrollment_event.student_first_name,
                    Student.last_name == enrollment_event.student_last_name,
                    Student.parent_id == parent_user_id,
                )
                .first()
            )

            if existing_student:
                raise Exception(
                    f"Student {enrollment_event.student_first_name} {enrollment_event.student_last_name} already exists for this parent"
                )

            # Create new student record
            student = Student(
                email=enrollment_event.student_email,
                first_name=enrollment_event.student_first_name,
                last_name=enrollment_event.student_last_name,
                date_of_birth=enrollment_event.student_date_of_birth,
                parent_id=parent_user_id,
                instrument=validated_data["instrument"],
                skill_level=enrollment_event.skill_level,
                lesson_rate=validated_data["lesson_rate"],
                enrollment_date=date.today(),
                is_active=True,
                notes=enrollment_event.notes,
            )

            db_session_obj.add(student)
            db_session_obj.flush()  # Get the ID without committing

            return student

        except Exception as e:
            logging.error(f"Error creating student record: {str(e)}")
            raise e

    async def _cleanup_supabase_account(self, user_id: str) -> None:
        """Cleanup Supabase account if account creation fails."""
        try:
            if user_id:
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SERVICE_ROLE_KEY")

                if supabase_url and supabase_key:
                    supabase = create_client(supabase_url, supabase_key)
                    supabase.auth.admin.delete_user(user_id)
                    logging.info(f"Cleaned up Supabase account: {user_id}")
        except Exception as e:
            logging.error(f"Error cleaning up Supabase account {user_id}: {str(e)}")
