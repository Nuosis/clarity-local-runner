"""
Record Subscription Payment Node

This node handles recording subscription payment events from Stripe webhooks
into the local database, ensuring idempotency and proper error handling.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from core.nodes.base import Node
from core.task import TaskContext
from database.session import SessionLocal
from models.payment import Payment, Subscription
from models.student import Student
from schemas.subscription_payment_schema import SubscriptionPaymentEventSchema
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class RecordSubscriptionPaymentNode(Node):
    """
    Records subscription payment events in the database.

    This node processes both successful and failed payment events from Stripe,
    creating or updating payment records while ensuring idempotency through
    unique payment ID tracking.

    Key Features:
    - Idempotent payment recording (prevents duplicates)
    - Handles both successful and failed payments
    - Links payments to existing students via Stripe customer ID
    - Creates subscription records if they don't exist
    - Comprehensive error handling and logging
    - Database transaction management
    """

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Process subscription payment event and record in database.

        Args:
            task_context: Contains SubscriptionPaymentEventSchema in event field

        Returns:
            Updated TaskContext with payment recording results
        """
        try:
            logging.info(f"Starting {self.node_name} payment recording")

            # Extract payment event from context
            payment_event: SubscriptionPaymentEventSchema = task_context.event

            # Initialize results
            payment_results = {
                "success": False,
                "payment_recorded": False,
                "subscription_updated": False,
                "duplicate_detected": False,
                "student_found": False,
                "payment_id": None,
                "subscription_id": None,
                "error": None,
                "processing_details": {},
            }

            # Create database session
            db_session = SessionLocal()

            try:
                # Process the payment event
                result = await self._process_payment_event(db_session, payment_event)
                payment_results.update(result)

                # Commit transaction if successful
                if payment_results["success"]:
                    db_session.commit()
                    logging.info(
                        f"Payment recording completed successfully. "
                        f"Payment ID: {payment_results.get('payment_id')}, "
                        f"Event: {payment_event.event_type}"
                    )
                else:
                    db_session.rollback()
                    logging.error(
                        f"Payment recording failed: {payment_results.get('error')}"
                    )

            except Exception as e:
                db_session.rollback()
                error_msg = f"Database transaction failed: {str(e)}"
                logging.error(error_msg)
                payment_results.update({"success": False, "error": error_msg})

            finally:
                db_session.close()

            # Store results in task context
            task_context.update_node(self.node_name, **payment_results)

            return task_context

        except Exception as e:
            error_msg = f"Error in {self.node_name}: {str(e)}"
            logging.error(error_msg)
            task_context.update_node(
                self.node_name, success=False, error=error_msg, payment_recorded=False
            )
            return task_context

    async def _process_payment_event(
        self, db_session: Session, payment_event: SubscriptionPaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Process the payment event and record in database.

        Args:
            db_session: Database session
            payment_event: Validated payment event data

        Returns:
            Dictionary with processing results
        """
        try:
            # Check for duplicate payment using Stripe event ID
            existing_payment = self._check_duplicate_payment(
                db_session, payment_event.stripe_event_id
            )

            if existing_payment:
                logging.info(
                    f"Duplicate payment detected for event {payment_event.stripe_event_id}. "
                    f"Existing payment ID: {existing_payment.id}"
                )
                return {
                    "success": True,
                    "duplicate_detected": True,
                    "payment_id": existing_payment.id,
                    "payment_recorded": False,
                    "processing_details": {
                        "duplicate_payment_id": existing_payment.id,
                        "original_event_id": payment_event.stripe_event_id,
                    },
                }

            # Find student by Stripe customer ID
            student = self._find_student_by_customer_id(
                db_session, payment_event.customer_id
            )

            if not student:
                error_msg = f"Student not found for Stripe customer ID: {payment_event.customer_id}"
                logging.error(error_msg)
                return {"success": False, "error": error_msg, "student_found": False}

            logging.info(
                f"Found student {student.id} for customer {payment_event.customer_id}"
            )

            # Handle subscription record
            subscription_result = await self._handle_subscription_record(
                db_session, payment_event, student.id
            )

            # Create payment record
            payment = await self._create_payment_record(
                db_session, payment_event, student.id
            )

            return {
                "success": True,
                "payment_recorded": True,
                "student_found": True,
                "payment_id": payment.id,
                "subscription_id": subscription_result.get("subscription_id"),
                "subscription_updated": subscription_result.get("updated", False),
                "processing_details": {
                    "student_id": student.id,
                    "stripe_customer_id": payment_event.customer_id,
                    "payment_amount": float(payment_event.amount),
                    "payment_currency": payment_event.currency,
                    "event_type": payment_event.event_type,
                    "invoice_id": payment_event.invoice_id,
                },
            }

        except SQLAlchemyError as e:
            error_msg = f"Database error processing payment: {str(e)}"
            logging.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error processing payment: {str(e)}"
            logging.error(error_msg)
            return {"success": False, "error": error_msg}

    def _check_duplicate_payment(
        self, db_session: Session, stripe_event_id: str
    ) -> Optional[Payment]:
        """
        Check if payment already exists for this Stripe event.

        Args:
            db_session: Database session
            stripe_event_id: Stripe event ID to check

        Returns:
            Existing Payment record or None
        """
        try:
            # Check if payment exists with this event ID in metadata
            existing_payment = (
                db_session.query(Payment)
                .filter(
                    Payment.payment_metadata.op("->>")("stripe_event_id")
                    == stripe_event_id
                )
                .first()
            )

            return existing_payment

        except SQLAlchemyError as e:
            logging.error(f"Error checking for duplicate payment: {str(e)}")
            return None

    def _find_student_by_customer_id(
        self, db_session: Session, stripe_customer_id: str
    ) -> Optional[Student]:
        """
        Find student by Stripe customer ID.

        Args:
            db_session: Database session
            stripe_customer_id: Stripe customer ID

        Returns:
            Student record or None
        """
        try:
            # Look for student with matching Stripe customer ID in metadata
            student = (
                db_session.query(Student)
                .filter(
                    Student.student_metadata.op("->>")("stripe_customer_id")
                    == stripe_customer_id
                )
                .first()
            )

            return student

        except SQLAlchemyError as e:
            logging.error(f"Error finding student by customer ID: {str(e)}")
            return None

    async def _handle_subscription_record(
        self,
        db_session: Session,
        payment_event: SubscriptionPaymentEventSchema,
        student_id: int,
    ) -> Dict[str, Any]:
        """
        Handle subscription record creation or update.

        Args:
            db_session: Database session
            payment_event: Payment event data
            student_id: Student ID

        Returns:
            Dictionary with subscription handling results
        """
        try:
            if not payment_event.subscription_id:
                # No subscription ID in event, skip subscription handling
                return {"updated": False, "subscription_id": None}

            # Check if subscription already exists
            existing_subscription = (
                db_session.query(Subscription)
                .filter(
                    Subscription.stripe_subscription_id == payment_event.subscription_id
                )
                .first()
            )

            if existing_subscription:
                # Update existing subscription status if needed
                if payment_event.is_payment_failed():
                    existing_subscription.status = "past_due"
                elif payment_event.is_payment_successful():
                    existing_subscription.status = "active"

                # Update period dates
                existing_subscription.current_period_start = payment_event.period_start
                existing_subscription.current_period_end = payment_event.period_end

                logging.info(
                    f"Updated existing subscription {existing_subscription.id}"
                )
                return {"updated": True, "subscription_id": existing_subscription.id}
            else:
                # Create new subscription record
                new_subscription = Subscription(
                    student_id=student_id,
                    stripe_subscription_id=payment_event.subscription_id,
                    stripe_customer_id=payment_event.customer_id,
                    status="active"
                    if payment_event.is_payment_successful()
                    else "past_due",
                    current_period_start=payment_event.period_start,
                    current_period_end=payment_event.period_end,
                    amount=payment_event.amount,
                    currency=payment_event.currency,
                    subscription_metadata={
                        "created_from_webhook": True,
                        "initial_event_id": payment_event.stripe_event_id,
                        "invoice_id": payment_event.invoice_id,
                    },
                )

                db_session.add(new_subscription)
                db_session.flush()  # Get the ID

                logging.info(f"Created new subscription {new_subscription.id}")
                return {"updated": True, "subscription_id": new_subscription.id}

        except SQLAlchemyError as e:
            logging.error(f"Error handling subscription record: {str(e)}")
            return {"updated": False, "subscription_id": None, "error": str(e)}

    async def _create_payment_record(
        self,
        db_session: Session,
        payment_event: SubscriptionPaymentEventSchema,
        student_id: int,
    ) -> Payment:
        """
        Create payment record in database.

        Args:
            db_session: Database session
            payment_event: Payment event data
            student_id: Student ID

        Returns:
            Created Payment record
        """
        try:
            # Determine payment status based on event type
            if payment_event.is_payment_successful():
                payment_status = "succeeded"
                payment_date = payment_event.created_at
                failure_reason = None
            else:
                payment_status = "failed"
                payment_date = None
                failure_reason = (
                    f"Invoice payment failed for invoice {payment_event.invoice_id}"
                )

            # Create payment record
            payment = Payment(
                student_id=student_id,
                stripe_payment_intent_id=payment_event.payment_intent_id
                or f"invoice_{payment_event.invoice_id}",
                stripe_customer_id=payment_event.customer_id,
                amount=payment_event.amount,
                currency=payment_event.currency,
                status=payment_status,
                payment_method="card",  # Assume card for subscription payments
                payment_date=payment_date,
                failure_reason=failure_reason,
                billing_cycle="monthly",  # Default for subscriptions
                description=f"Subscription payment for invoice {payment_event.invoice_id}",
                payment_metadata={
                    "stripe_event_id": payment_event.stripe_event_id,
                    "stripe_invoice_id": payment_event.invoice_id,
                    "stripe_subscription_id": payment_event.subscription_id,
                    "invoice_number": payment_event.invoice_number,
                    "invoice_status": payment_event.invoice_status,
                    "hosted_invoice_url": payment_event.hosted_invoice_url,
                    "invoice_pdf_url": payment_event.invoice_pdf_url,
                    "period_start": payment_event.period_start.isoformat(),
                    "period_end": payment_event.period_end.isoformat(),
                    "processed_at": datetime.utcnow().isoformat(),
                    "event_type": payment_event.event_type,
                    "livemode": payment_event.livemode,
                },
            )

            db_session.add(payment)
            db_session.flush()  # Get the ID

            logging.info(
                f"Created payment record {payment.id} for student {student_id}. "
                f"Status: {payment_status}, Amount: {payment_event.amount} {payment_event.currency}"
            )

            return payment

        except SQLAlchemyError as e:
            error_msg = f"Error creating payment record: {str(e)}"
            logging.error(error_msg)
            raise e
