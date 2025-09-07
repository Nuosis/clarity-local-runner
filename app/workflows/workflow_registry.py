from enum import Enum

from workflows.enrollment_workflow import EnrollmentWorkflow
from workflows.payment_workflow import PaymentWorkflow
from workflows.subscription_payment_workflow import SubscriptionPaymentWorkflow


class WorkflowRegistry(Enum):
    ENROLLMENT = EnrollmentWorkflow
    PAYMENT = PaymentWorkflow
    SUBSCRIPTION_PAYMENT = SubscriptionPaymentWorkflow
