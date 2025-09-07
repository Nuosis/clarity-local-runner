from enum import Enum

from workflows.enrollment_workflow import EnrollmentWorkflow
from workflows.payment_workflow import PaymentWorkflow


class WorkflowRegistry(Enum):
    ENROLLMENT = EnrollmentWorkflow
    PAYMENT = PaymentWorkflow
