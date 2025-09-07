"""
Student Enrollment Workflow

This workflow orchestrates the complete student enrollment process from initial
validation through account creation, teacher assignment, demo lesson scheduling,
and welcome email notifications.
"""

from core.schema import NodeConfig, WorkflowSchema
from core.workflow import Workflow
from schemas.enrollment_schema import EnrollmentEventSchema

from workflows.enrollment_workflow_nodes.assign_teacher_node import AssignTeacherNode
from workflows.enrollment_workflow_nodes.create_student_account_node import (
    CreateStudentAccountNode,
)
from workflows.enrollment_workflow_nodes.schedule_demo_lesson_node import (
    ScheduleDemoLessonNode,
)
from workflows.enrollment_workflow_nodes.send_welcome_emails_node import (
    SendWelcomeEmailsNode,
)
from workflows.enrollment_workflow_nodes.validate_enrollment_node import (
    ValidateEnrollmentNode,
)


class EnrollmentWorkflow(Workflow):
    """
    Student Enrollment Workflow

    Orchestrates the complete student enrollment process through the following stages:

    1. ValidateEnrollmentNode - Validates enrollment data and business rules
    2. CreateStudentAccountNode - Creates parent user account and student record
    3. AssignTeacherNode - Assigns appropriate teacher based on capacity
    4. ScheduleDemoLessonNode - Schedules initial demo lesson
    5. SendWelcomeEmailsNode - Sends welcome emails to parent, teacher, and admin

    The workflow is designed to be resilient - if any step fails, subsequent steps
    can still execute with appropriate fallbacks. Email failures, for example,
    won't prevent the enrollment from completing.

    Usage:
        workflow = EnrollmentWorkflow()
        result = await workflow.run_async(enrollment_data)

        # Or for synchronous execution:
        result = workflow.run(enrollment_data)
    """

    workflow_schema = WorkflowSchema(
        description="Complete student enrollment workflow with validation, account creation, teacher assignment, lesson scheduling, and notifications",
        event_schema=EnrollmentEventSchema,
        start=ValidateEnrollmentNode,
        nodes=[
            NodeConfig(
                node=ValidateEnrollmentNode,
                connections=[CreateStudentAccountNode],
                description="Validates enrollment data including student age, parent info, instrument availability, and payment information",
            ),
            NodeConfig(
                node=CreateStudentAccountNode,
                connections=[AssignTeacherNode],
                description="Creates parent user account in Supabase and student record in database with proper error handling",
            ),
            NodeConfig(
                node=AssignTeacherNode,
                connections=[ScheduleDemoLessonNode],
                description="Assigns teacher using capacity-based algorithm (teacher with lowest student count)",
            ),
            NodeConfig(
                node=ScheduleDemoLessonNode,
                connections=[SendWelcomeEmailsNode],
                description="Schedules demo lesson by finding next available teacher slot and creating lesson record",
            ),
            NodeConfig(
                node=SendWelcomeEmailsNode,
                connections=[],
                description="Sends welcome emails to parent (with login credentials), teacher notification, and admin notification using Brevo email service",
            ),
        ],
    )
