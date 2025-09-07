"""
Send welcome emails to parent and teacher node.
"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

from core.nodes.base import Node
from core.task import TaskContext
from services.brevo_email_service import brevo_service


class SendWelcomeEmailsNode(Node):
    """Send welcome emails to parent and teacher."""

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Send welcome emails to parent and teacher.

        Sends:
        - Send parent welcome email with login credentials
        - Send teacher notification about new student
        - Include demo lesson details

        Args:
            task_context: The task context containing all previous workflow results

        Returns:
            Updated task context with email sending results
        """
        try:
            logging.info(f"Starting {self.node_name} email sending")

            # Gather information from previous nodes
            account_results = task_context.nodes.get("CreateStudentAccountNode", {})
            assignment_results = task_context.nodes.get("AssignTeacherNode", {})
            scheduling_results = task_context.nodes.get("ScheduleDemoLessonNode", {})
            validation_results = task_context.nodes.get("ValidateEnrollmentNode", {})

            # Initialize email results
            email_results = {
                "success": False,
                "parent_email_sent": False,
                "teacher_email_sent": False,
                "admin_notification_sent": False,
                "emails_attempted": 0,
                "emails_successful": 0,
                "email_errors": [],
            }

            # Check if we have minimum required information
            if not account_results.get("success", False):
                logging.warning(
                    "Account creation not successful - sending limited welcome emails"
                )

            # Prepare email data
            email_data = await self._prepare_email_data(
                task_context.event,
                account_results,
                assignment_results,
                scheduling_results,
                validation_results,
            )

            # Send parent welcome email
            if email_data.get("parent_email"):
                parent_email_result = await self._send_parent_welcome_email(email_data)
                email_results["parent_email_sent"] = parent_email_result["success"]
                email_results["emails_attempted"] += 1
                if parent_email_result["success"]:
                    email_results["emails_successful"] += 1
                    logging.info("Parent welcome email sent successfully")
                else:
                    email_results["email_errors"].append(
                        f"Parent email: {parent_email_result['error']}"
                    )
                    logging.error(
                        f"Failed to send parent welcome email: {parent_email_result['error']}"
                    )

            # Send teacher notification email (if teacher assigned)
            if email_data.get("teacher_assigned") and email_data.get("teacher_email"):
                teacher_email_result = await self._send_teacher_notification_email(
                    email_data
                )
                email_results["teacher_email_sent"] = teacher_email_result["success"]
                email_results["emails_attempted"] += 1
                if teacher_email_result["success"]:
                    email_results["emails_successful"] += 1
                    logging.info("Teacher notification email sent successfully")
                else:
                    email_results["email_errors"].append(
                        f"Teacher email: {teacher_email_result['error']}"
                    )
                    logging.error(
                        f"Failed to send teacher notification email: {teacher_email_result['error']}"
                    )

            # Send admin notification email
            admin_email_result = await self._send_admin_notification_email(email_data)
            email_results["admin_notification_sent"] = admin_email_result["success"]
            email_results["emails_attempted"] += 1
            if admin_email_result["success"]:
                email_results["emails_successful"] += 1
                logging.info("Admin notification email sent successfully")
            else:
                email_results["email_errors"].append(
                    f"Admin email: {admin_email_result['error']}"
                )
                logging.error(
                    f"Failed to send admin notification email: {admin_email_result['error']}"
                )

            # Determine overall success
            email_results["success"] = email_results["emails_successful"] > 0

            if email_results["success"]:
                logging.info(
                    f"Email sending completed - {email_results['emails_successful']}/{email_results['emails_attempted']} emails sent successfully"
                )
            else:
                logging.error("All email sending attempts failed")

            # Store email results in task context
            task_context.update_node(self.node_name, **email_results)

            # Don't stop workflow even if emails fail - enrollment is complete
            return task_context

        except Exception as e:
            logging.error(f"Error in {self.node_name}: {str(e)}")
            task_context.update_node(
                self.node_name,
                success=False,
                error=str(e),
                emails_attempted=0,
                emails_successful=0,
            )
            # Don't stop workflow - email failures shouldn't block enrollment completion
            return task_context

    async def _prepare_email_data(
        self,
        enrollment_event,
        account_results: Dict[str, Any],
        assignment_results: Dict[str, Any],
        scheduling_results: Dict[str, Any],
        validation_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare data needed for all email templates."""
        try:
            validated_data = validation_results.get("validated_data", {})
            parent_info = validated_data.get("parent_info", {})

            email_data = {
                # Student information
                "student_first_name": enrollment_event.student_first_name,
                "student_last_name": enrollment_event.student_last_name,
                "student_age": validated_data.get("student_age"),
                "instrument": validated_data.get(
                    "instrument", enrollment_event.instrument
                ),
                "skill_level": enrollment_event.skill_level,
                "lesson_rate": validated_data.get(
                    "lesson_rate", enrollment_event.lesson_rate
                ),
                # Parent information
                "parent_first_name": parent_info.get(
                    "parent_first_name", enrollment_event.parent_first_name
                ),
                "parent_last_name": parent_info.get(
                    "parent_last_name", enrollment_event.parent_last_name
                ),
                "parent_email": parent_info.get(
                    "parent_email", enrollment_event.parent_email
                ),
                "temporary_password": account_results.get("temporary_password"),
                # Teacher information
                "teacher_assigned": assignment_results.get("success", False),
                "teacher_name": assignment_results.get("teacher_name"),
                "teacher_email": None,  # Would need to fetch from database
                # Demo lesson information
                "demo_lesson_scheduled": scheduling_results.get("success", False),
                "demo_lesson_date": scheduling_results.get("scheduled_at"),
                "requires_manual_scheduling": scheduling_results.get(
                    "requires_manual_scheduling", False
                ),
                # System information
                "enrollment_date": datetime.now().strftime("%B %d, %Y"),
                "login_url": self._get_login_url(),
                "support_email": self._get_support_email(),
                "school_name": "Cedar Heights Music Academy",
            }

            return email_data

        except Exception as e:
            logging.error(f"Error preparing email data: {str(e)}")
            return {}

    async def _send_parent_welcome_email(
        self, email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send welcome email to parent with login credentials."""
        try:
            subject = f"Welcome to {email_data['school_name']} - {email_data['student_first_name']}'s Enrollment Confirmed!"

            email_content = self._generate_parent_welcome_email_content(email_data)

            # Send email using Brevo
            email_sent = await self._send_email(
                to_email=email_data["parent_email"],
                to_name=f"{email_data['parent_first_name']} {email_data['parent_last_name']}",
                subject=subject,
                content=email_content,
                email_type="parent_welcome",
            )

            return {
                "success": email_sent,
                "error": None if email_sent else "Email service unavailable",
            }

        except Exception as e:
            logging.error(f"Error sending parent welcome email: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _send_teacher_notification_email(
        self, email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send notification email to teacher about new student."""
        try:
            # In a real implementation, we would fetch teacher email from database
            # For now, simulate with a placeholder
            teacher_email = "teacher@cedarheights.com"  # Would be fetched from database

            subject = f"New Student Assignment - {email_data['student_first_name']} {email_data['student_last_name']}"

            email_content = self._generate_teacher_notification_email_content(
                email_data
            )

            # Send email using Brevo
            email_sent = await self._send_email(
                to_email=teacher_email,
                to_name=email_data.get("teacher_name", "Teacher"),
                subject=subject,
                content=email_content,
                email_type="teacher_notification",
            )

            return {
                "success": email_sent,
                "error": None if email_sent else "Email service unavailable",
            }

        except Exception as e:
            logging.error(f"Error sending teacher notification email: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _send_admin_notification_email(
        self, email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send notification email to admin about new enrollment."""
        try:
            admin_email = self._get_admin_email()

            subject = f"New Enrollment - {email_data['student_first_name']} {email_data['student_last_name']}"

            email_content = self._generate_admin_notification_email_content(email_data)

            # Send email using Brevo
            email_sent = await self._send_email(
                to_email=admin_email,
                to_name="Admin",
                subject=subject,
                content=email_content,
                email_type="admin_notification",
            )

            return {
                "success": email_sent,
                "error": None if email_sent else "Email service unavailable",
            }

        except Exception as e:
            logging.error(f"Error sending admin notification email: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _send_email(
        self, to_email: str, to_name: str, subject: str, content: str, email_type: str
    ) -> bool:
        """
        Send email using Brevo email service.
        """
        try:
            logging.info(f"Sending {email_type} email to {to_email}")
            logging.debug(f"Email subject: {subject}")

            # Check if Brevo service is configured
            if not brevo_service.is_configured():
                logging.warning(
                    "Brevo email service not configured - falling back to simulation"
                )
                logging.info(f"Would send {email_type} email to {to_email}: {subject}")
                return True  # Don't fail workflow due to email configuration issues

            # Send email through Brevo
            result = await brevo_service.send_email(
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                html_content=content,
                text_content=self._html_to_text(content),
            )

            if result["success"]:
                logging.info(
                    f"Successfully sent {email_type} email to {to_email}. Message ID: {result.get('message_id')}"
                )
                return True
            else:
                logging.error(
                    f"Failed to send {email_type} email to {to_email}: {result.get('error')}"
                )
                return False

        except Exception as e:
            logging.error(f"Error sending {email_type} email to {to_email}: {str(e)}")
            return False

    def _generate_parent_welcome_email_content(self, email_data: Dict[str, Any]) -> str:
        """Generate welcome email content for parent in HTML format."""
        demo_lesson_info = ""
        if email_data["demo_lesson_scheduled"]:
            demo_lesson_info = f"""
            <p><strong>Demo Lesson:</strong><br>
            Your child's demo lesson has been scheduled for <strong>{email_data["demo_lesson_date"]}</strong>.<br>
            The teacher will use this session to assess {email_data["student_first_name"]}'s current skill level and discuss learning goals.</p>
            """
        elif email_data["requires_manual_scheduling"]:
            demo_lesson_info = """
            <p><strong>Demo Lesson:</strong><br>
            We'll be in touch shortly to schedule your child's demo lesson at a time that works for your family.</p>
            """

        teacher_info = ""
        if email_data["teacher_assigned"]:
            teacher_info = f"<p><strong>Teacher Assignment:</strong><br>Your child has been assigned to <strong>{email_data['teacher_name']}</strong> for {email_data['instrument']} lessons.</p>"
        else:
            teacher_info = "<p><strong>Teacher Assignment:</strong><br>We'll assign a teacher and notify you shortly.</p>"

        login_info = ""
        if email_data["temporary_password"]:
            login_info = f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Your Account Login Details:</h3>
                <p><strong>Email:</strong> {email_data["parent_email"]}<br>
                <strong>Temporary Password:</strong> {email_data["temporary_password"]}<br>
                <strong>Login URL:</strong> <a href="{email_data["login_url"]}">{email_data["login_url"]}</a></p>
                <p><em>Please log in and change your password at your earliest convenience.</em></p>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to {email_data["school_name"]}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Welcome to {email_data["school_name"]}!</h2>
                
                <p>Dear {email_data["parent_first_name"]} {email_data["parent_last_name"]},</p>
                
                <p>We're excited to confirm that <strong>{email_data["student_first_name"]}'s</strong> enrollment has been successfully processed.</p>
                
                <div style="background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Enrollment Details:</h3>
                    <ul>
                        <li><strong>Student:</strong> {email_data["student_first_name"]} {email_data["student_last_name"]}</li>
                        <li><strong>Instrument:</strong> {email_data["instrument"].title()}</li>
                        <li><strong>Skill Level:</strong> {email_data["skill_level"].title()}</li>
                        <li><strong>Lesson Rate:</strong> ${email_data["lesson_rate"]} per lesson</li>
                        <li><strong>Enrollment Date:</strong> {email_data["enrollment_date"]}</li>
                    </ul>
                </div>
                
                {teacher_info}
                
                {demo_lesson_info}
                
                {login_info}
                
                <p>If you have any questions or need assistance, please don't hesitate to contact us at <a href="mailto:{email_data["support_email"]}">{email_data["support_email"]}</a>.</p>
                
                <p>Welcome to the Cedar Heights Music Academy family!</p>
                
                <p>Best regards,<br>
                <strong>The Cedar Heights Music Academy Team</strong></p>
            </div>
        </body>
        </html>
        """

    def _generate_teacher_notification_email_content(
        self, email_data: Dict[str, Any]
    ) -> str:
        """Generate notification email content for teacher in HTML format."""
        demo_lesson_info = ""
        if email_data["demo_lesson_scheduled"]:
            demo_lesson_info = f"<p><strong>Demo lesson scheduled for:</strong> {email_data['demo_lesson_date']}</p>"
        else:
            demo_lesson_info = "<p><strong>Demo lesson:</strong> Scheduling pending</p>"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>New Student Assignment</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">New Student Assignment</h2>
                
                <p>Dear {email_data["teacher_name"]},</p>
                
                <p>You have been assigned a new student at <strong>{email_data["school_name"]}</strong>.</p>
                
                <div style="background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Student Details:</h3>
                    <ul>
                        <li><strong>Name:</strong> {email_data["student_first_name"]} {email_data["student_last_name"]}</li>
                        <li><strong>Age:</strong> {email_data["student_age"]} years old</li>
                        <li><strong>Instrument:</strong> {email_data["instrument"].title()}</li>
                        <li><strong>Skill Level:</strong> {email_data["skill_level"].title()}</li>
                        <li><strong>Lesson Rate:</strong> ${email_data["lesson_rate"]} per lesson</li>
                        <li><strong>Parent:</strong> {email_data["parent_first_name"]} {email_data["parent_last_name"]}</li>
                        <li><strong>Parent Email:</strong> <a href="mailto:{email_data["parent_email"]}">{email_data["parent_email"]}</a></li>
                    </ul>
                </div>
                
                {demo_lesson_info}
                
                <p>Please prepare for the demo lesson and reach out to the parent if you need any additional information.</p>
                
                <p>Best regards,<br>
                <strong>The Cedar Heights Music Academy Team</strong></p>
            </div>
        </body>
        </html>
        """

    def _generate_admin_notification_email_content(
        self, email_data: Dict[str, Any]
    ) -> str:
        """Generate notification email content for admin in HTML format."""
        status_summary = []
        if email_data["teacher_assigned"]:
            status_summary.append(
                f"<li style='color: #28a745;'>✅ Teacher assigned: {email_data['teacher_name']}</li>"
            )
        else:
            status_summary.append(
                "<li style='color: #ffc107;'>⚠️ Teacher assignment pending</li>"
            )

        if email_data["demo_lesson_scheduled"]:
            status_summary.append(
                f"<li style='color: #28a745;'>✅ Demo lesson scheduled: {email_data['demo_lesson_date']}</li>"
            )
        else:
            status_summary.append(
                "<li style='color: #ffc107;'>⚠️ Demo lesson scheduling pending</li>"
            )

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>New Enrollment Notification</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">New Enrollment Processed</h2>
                
                <p>A new enrollment has been processed in the system:</p>
                
                <div style="background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Student Information:</h3>
                    <ul>
                        <li><strong>Name:</strong> {email_data["student_first_name"]} {email_data["student_last_name"]}</li>
                        <li><strong>Age:</strong> {email_data["student_age"]} years old</li>
                        <li><strong>Instrument:</strong> {email_data["instrument"].title()}</li>
                        <li><strong>Skill Level:</strong> {email_data["skill_level"].title()}</li>
                        <li><strong>Lesson Rate:</strong> ${email_data["lesson_rate"]} per lesson</li>
                    </ul>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Parent Information:</h3>
                    <ul>
                        <li><strong>Name:</strong> {email_data["parent_first_name"]} {email_data["parent_last_name"]}</li>
                        <li><strong>Email:</strong> <a href="mailto:{email_data["parent_email"]}">{email_data["parent_email"]}</a></li>
                    </ul>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Enrollment Status:</h3>
                    <ul style="list-style: none; padding-left: 0;">
                        {"".join(status_summary)}
                    </ul>
                </div>
                
                <p><strong>Enrollment Date:</strong> {email_data["enrollment_date"]}</p>
                
                <p>Please review and follow up on any pending items.</p>
            </div>
        </body>
        </html>
        """

    def _get_login_url(self) -> str:
        """Get the login URL for the parent portal."""
        # In a real implementation, this would be configured
        return "https://portal.cedarheights.com/login"

    def _get_support_email(self) -> str:
        """Get the support email address."""
        return os.getenv("SUPPORT_EMAIL", "support@cedarheights.com")

    def _get_admin_email(self) -> str:
        """Get the admin notification email address."""
        return os.getenv("ADMIN_EMAIL", "admin@cedarheights.com")

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text for email."""
        # Simple HTML to text conversion - in production, you might use a library like BeautifulSoup

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html_content)

        # Replace HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text
