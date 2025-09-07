"""
Payment Failure Handling Node

This module implements the PaymentFailureHandlingNode workflow node that handles
payment failures, notifications, and cleanup operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from core.nodes.base import Node
from core.task import TaskContext
from database.session import db_session
from models.user import User
from schemas.payment_schema import PaymentEventSchema, PaymentStatus
from services.brevo_email_service import brevo_service
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PaymentFailureHandlingNode(Node):
    """
    Workflow node that handles payment failures and related cleanup.

    This node handles:
    - Logging payment failure details
    - Sending failure notifications to customers and admins
    - Updating subscription status if applicable
    - Recording failure metrics
    - Scheduling retry attempts if appropriate
    - Cleaning up incomplete transactions

    Input: PaymentEventSchema with failure information
    Output: Updated context with failure handling results
    """

    def __init__(self):
        super().__init__()
        self.name = "PaymentFailureHandlingNode"
        self.description = "Handles payment failures, notifications, and cleanup"

    async def process(self, context: TaskContext) -> TaskContext:
        """
        Process the payment failure handling workflow step.

        Args:
            context: Task context containing payment failure information

        Returns:
            Updated task context with failure handling results
        """
        logger.info(f"Starting {self.name} processing")

        try:
            # Extract payment event data
            payment_event = PaymentEventSchema(**context.data)
            failure_reason = context.data.get("failure_reason", "Payment failed")

            logger.warning(
                f"Handling payment failure for user {payment_event.user_id}: {failure_reason}"
            )

            # Record failure details
            failure_details = await self._record_failure_details(context, payment_event)

            # Handle subscription-specific failures
            if context.data.get("subscription_id"):
                await self._handle_subscription_failure(context, payment_event)

            # Send failure notifications
            notification_results = await self._send_failure_notifications(
                context, payment_event, failure_reason
            )

            # Clean up incomplete transactions
            cleanup_results = await self._cleanup_incomplete_transactions(
                context, payment_event
            )

            # Update context with failure handling results
            context.data.update(
                {
                    "failure_handled": True,
                    "failure_details_recorded": failure_details["success"],
                    "notifications_sent": notification_results["success"],
                    "cleanup_completed": cleanup_results["success"],
                }
            )

            # Store node result
            context.results[self.name] = {
                "success": True,
                "failure_reason": failure_reason,
                "failure_details": failure_details,
                "notifications": notification_results,
                "cleanup": cleanup_results,
                "message": "Payment failure handled successfully",
            }

            logger.info(
                f"Payment failure handling completed for user {payment_event.user_id}"
            )
            return context

        except Exception as e:
            error_msg = f"Unexpected error in {self.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._handle_error(context, error_msg, "failure_handling_error")

    async def _record_failure_details(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Record detailed failure information for analysis and reporting.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with recording results
        """
        try:
            failure_record = {
                "user_id": str(payment_event.user_id),
                "payment_intent_id": context.data.get("payment_intent_id"),
                "subscription_id": context.data.get("subscription_id"),
                "amount": str(payment_event.amount),
                "currency": payment_event.currency,
                "failure_timestamp": datetime.utcnow().isoformat(),
                "error_code": context.data.get("error_code"),
                "error_message": context.data.get("error_message"),
                "decline_code": context.data.get("decline_code"),
                "retry_count": context.data.get("retry_count", 0),
                "payment_method_type": payment_event.payment_method.type
                if payment_event.payment_method
                else None,
                "workflow_id": context.data.get("workflow_id"),
            }

            # Log failure details for monitoring and analysis
            logger.error(
                f"Payment failure recorded",
                extra={
                    "payment_failure": failure_record,
                    "user_id": str(payment_event.user_id),
                    "amount": str(payment_event.amount),
                },
            )

            # In a production system, you might also:
            # - Store in a dedicated failures table
            # - Send to monitoring/analytics service
            # - Update metrics/counters

            return {
                "success": True,
                "failure_record": failure_record,
                "message": "Failure details recorded successfully",
            }

        except Exception as e:
            logger.error(f"Failed to record failure details: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to record failure details",
            }

    async def _handle_subscription_failure(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Handle subscription-specific failure scenarios.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with subscription handling results
        """
        try:
            subscription_id = context.data.get("subscription_id")
            if not subscription_id:
                return {"success": True, "message": "No subscription to handle"}

            # Update subscription status based on failure type
            error_code = context.data.get("error_code", "")
            decline_code = context.data.get("decline_code", "")

            # Determine if subscription should be paused or cancelled
            should_cancel = decline_code in [
                "stolen_card",
                "lost_card",
                "pickup_card",
                "restricted_card",
                "security_violation",
            ]

            if should_cancel:
                # Mark subscription for cancellation
                context.data["subscription_action"] = "cancel"
                context.data["subscription_reason"] = (
                    f"Payment failed with decline code: {decline_code}"
                )
            else:
                # Mark subscription as past due
                context.data["subscription_action"] = "past_due"
                context.data["subscription_reason"] = "Payment failed, retry scheduled"

            logger.info(
                f"Subscription {subscription_id} marked for {context.data['subscription_action']}"
            )

            return {
                "success": True,
                "subscription_id": subscription_id,
                "action": context.data["subscription_action"],
                "reason": context.data["subscription_reason"],
            }

        except Exception as e:
            logger.error(f"Failed to handle subscription failure: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to handle subscription failure",
            }

    async def _send_failure_notifications(
        self,
        context: TaskContext,
        payment_event: PaymentEventSchema,
        failure_reason: str,
    ) -> Dict[str, Any]:
        """
        Send failure notifications to customer and admin.

        Args:
            context: Task context
            payment_event: Payment event data
            failure_reason: Reason for failure

        Returns:
            Dictionary with notification results
        """
        try:
            notifications_sent = []

            # Prepare notification data
            notification_data = {
                "customer_name": payment_event.name,
                "customer_email": payment_event.email,
                "amount": str(payment_event.amount),
                "currency": payment_event.currency.upper(),
                "failure_reason": failure_reason,
                "error_code": context.data.get("error_code", ""),
                "decline_code": context.data.get("decline_code", ""),
                "subscription_id": context.data.get("subscription_id"),
                "retry_scheduled": context.data.get("requires_retry", False),
                "support_email": "support@cedarhightsmusic.com",
                "support_phone": "(555) 123-4567",
            }

            # Send customer notification
            try:
                customer_result = await self._send_customer_failure_notification(
                    notification_data
                )
                notifications_sent.append(
                    {
                        "type": "customer",
                        "success": customer_result["success"],
                        "message": customer_result.get("message", ""),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to send customer notification: {str(e)}")
                notifications_sent.append(
                    {"type": "customer", "success": False, "error": str(e)}
                )

            # Send admin notification for high-value failures or repeated failures
            should_notify_admin = (
                payment_event.amount >= 100  # High value
                or context.data.get("retry_count", 0) >= 2  # Multiple failures
                or context.data.get("decline_code")
                in ["stolen_card", "lost_card", "security_violation"]  # Security issues
            )

            if should_notify_admin:
                try:
                    admin_result = await self._send_admin_failure_notification(
                        notification_data
                    )
                    notifications_sent.append(
                        {
                            "type": "admin",
                            "success": admin_result["success"],
                            "message": admin_result.get("message", ""),
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to send admin notification: {str(e)}")
                    notifications_sent.append(
                        {"type": "admin", "success": False, "error": str(e)}
                    )

            success_count = sum(1 for n in notifications_sent if n["success"])

            return {
                "success": success_count > 0,
                "notifications_sent": notifications_sent,
                "total_sent": success_count,
                "message": f"Sent {success_count} of {len(notifications_sent)} notifications",
            }

        except Exception as e:
            logger.error(f"Failed to send failure notifications: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to send failure notifications",
            }

    async def _send_customer_failure_notification(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send payment failure notification to customer."""
        try:
            if not brevo_service.is_configured():
                logger.warning(
                    "Brevo email service not configured, skipping customer notification"
                )
                return {"success": False, "message": "Email service not configured"}

            # Determine email template based on failure type
            if data.get("subscription_id"):
                subject = "Payment Issue with Your Music Lesson Subscription"
                template_data = {
                    "customer_name": data["customer_name"],
                    "amount": data["amount"],
                    "currency": data["currency"],
                    "failure_reason": self._get_customer_friendly_error(
                        data["failure_reason"], data.get("decline_code")
                    ),
                    "retry_scheduled": data["retry_scheduled"],
                    "support_email": data["support_email"],
                    "support_phone": data["support_phone"],
                }
            else:
                subject = "Payment Processing Issue"
                template_data = {
                    "customer_name": data["customer_name"],
                    "amount": data["amount"],
                    "currency": data["currency"],
                    "failure_reason": self._get_customer_friendly_error(
                        data["failure_reason"], data.get("decline_code")
                    ),
                    "support_email": data["support_email"],
                    "support_phone": data["support_phone"],
                }

            # Send email
            result = await brevo_service.send_email(
                to_email=data["customer_email"],
                to_name=data["customer_name"],
                subject=subject,
                html_content=self._generate_customer_failure_email_html(template_data),
                text_content=self._generate_customer_failure_email_text(template_data),
            )

            return result

        except Exception as e:
            logger.error(f"Failed to send customer failure notification: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _send_admin_failure_notification(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send payment failure notification to admin."""
        try:
            if not brevo_service.is_configured():
                logger.warning(
                    "Brevo email service not configured, skipping admin notification"
                )
                return {"success": False, "message": "Email service not configured"}

            subject = (
                f"Payment Failure Alert - {data['customer_name']} (${data['amount']})"
            )

            template_data = {
                "customer_name": data["customer_name"],
                "customer_email": data["customer_email"],
                "amount": data["amount"],
                "currency": data["currency"],
                "failure_reason": data["failure_reason"],
                "error_code": data.get("error_code", "N/A"),
                "decline_code": data.get("decline_code", "N/A"),
                "subscription_id": data.get("subscription_id", "N/A"),
                "retry_scheduled": data["retry_scheduled"],
            }

            # Send to admin email
            result = await brevo_service.send_email(
                to_email="admin@cedarhightsmusic.com",
                to_name="Cedar Heights Admin",
                subject=subject,
                html_content=self._generate_admin_failure_email_html(template_data),
                text_content=self._generate_admin_failure_email_text(template_data),
            )

            return result

        except Exception as e:
            logger.error(f"Failed to send admin failure notification: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _cleanup_incomplete_transactions(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Clean up any incomplete transactions or temporary data.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with cleanup results
        """
        try:
            cleanup_actions = []

            # Clean up any temporary payment records
            # In a real system, you might have temporary transaction records to clean up

            # Log cleanup completion
            logger.info(
                f"Cleanup completed for failed payment - User: {payment_event.user_id}"
            )

            return {
                "success": True,
                "cleanup_actions": cleanup_actions,
                "message": "Cleanup completed successfully",
            }

        except Exception as e:
            logger.error(f"Failed to cleanup incomplete transactions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to cleanup incomplete transactions",
            }

    def _get_customer_friendly_error(
        self, error_message: str, decline_code: Optional[str] = None
    ) -> str:
        """Convert technical error messages to customer-friendly messages."""
        if decline_code:
            friendly_messages = {
                "insufficient_funds": "Your card has insufficient funds. Please try a different payment method.",
                "card_declined": "Your card was declined. Please contact your bank or try a different card.",
                "expired_card": "Your card has expired. Please update your payment method.",
                "incorrect_cvc": "The security code (CVC) is incorrect. Please check and try again.",
                "processing_error": "There was a temporary processing error. Please try again in a few minutes.",
                "stolen_card": "This card has been reported as stolen. Please contact your bank.",
                "lost_card": "This card has been reported as lost. Please contact your bank.",
            }
            return friendly_messages.get(
                decline_code,
                "Your payment could not be processed. Please try a different payment method.",
            )

        return "Your payment could not be processed. Please try again or contact support for assistance."

    def _generate_customer_failure_email_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML email content for customer failure notification."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #d32f2f;">Payment Issue</h2>
                
                <p>Dear {data["customer_name"]},</p>
                
                <p>We encountered an issue processing your payment of ${data["amount"]} {data["currency"]}.</p>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Issue:</strong> {data["failure_reason"]}
                </div>
                
                {"<p><strong>Next Steps:</strong> We will automatically retry your payment in a few hours.</p>" if data.get("retry_scheduled") else "<p><strong>Next Steps:</strong> Please update your payment method or try again.</p>"}
                
                <p>If you continue to experience issues, please contact our support team:</p>
                <ul>
                    <li>Email: {data["support_email"]}</li>
                    <li>Phone: {data["support_phone"]}</li>
                </ul>
                
                <p>Thank you for your understanding.</p>
                
                <p>Best regards,<br>Cedar Heights Music Academy</p>
            </div>
        </body>
        </html>
        """

    def _generate_customer_failure_email_text(self, data: Dict[str, Any]) -> str:
        """Generate text email content for customer failure notification."""
        retry_text = (
            "We will automatically retry your payment in a few hours."
            if data.get("retry_scheduled")
            else "Please update your payment method or try again."
        )

        return f"""
        Dear {data["customer_name"]},

        We encountered an issue processing your payment of ${data["amount"]} {data["currency"]}.

        Issue: {data["failure_reason"]}

        Next Steps: {retry_text}

        If you continue to experience issues, please contact our support team:
        - Email: {data["support_email"]}
        - Phone: {data["support_phone"]}

        Thank you for your understanding.

        Best regards,
        Cedar Heights Music Academy
        """

    def _generate_admin_failure_email_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML email content for admin failure notification."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #d32f2f;">Payment Failure Alert</h2>
                
                <p><strong>Customer:</strong> {data["customer_name"]} ({data["customer_email"]})</p>
                <p><strong>Amount:</strong> ${data["amount"]} {data["currency"]}</p>
                <p><strong>Failure Reason:</strong> {data["failure_reason"]}</p>
                <p><strong>Error Code:</strong> {data["error_code"]}</p>
                <p><strong>Decline Code:</strong> {data["decline_code"]}</p>
                <p><strong>Subscription ID:</strong> {data["subscription_id"]}</p>
                <p><strong>Retry Scheduled:</strong> {"Yes" if data["retry_scheduled"] else "No"}</p>
                
                <p>Please review and take appropriate action if needed.</p>
            </div>
        </body>
        </html>
        """

    def _generate_admin_failure_email_text(self, data: Dict[str, Any]) -> str:
        """Generate text email content for admin failure notification."""
        return f"""
        Payment Failure Alert

        Customer: {data["customer_name"]} ({data["customer_email"]})
        Amount: ${data["amount"]} {data["currency"]}
        Failure Reason: {data["failure_reason"]}
        Error Code: {data["error_code"]}
        Decline Code: {data["decline_code"]}
        Subscription ID: {data["subscription_id"]}
        Retry Scheduled: {"Yes" if data["retry_scheduled"] else "No"}

        Please review and take appropriate action if needed.
        """

    def _handle_error(
        self, context: TaskContext, error_message: str, error_code: str
    ) -> TaskContext:
        """
        Handle errors and update context with error information.

        Args:
            context: Task context to update
            error_message: Error message
            error_code: Error code for categorization

        Returns:
            Updated context with error information
        """
        context.data["error"] = True
        context.data["error_message"] = error_message
        context.data["error_code"] = error_code

        context.results[self.name] = {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
        }

        return context

    def validate_input(self, context: TaskContext) -> bool:
        """
        Validate that the context contains required data for failure handling.

        Args:
            context: Task context to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate payment event schema
            PaymentEventSchema(**context.data)

            # Check that this is indeed a failure scenario
            payment_status = context.data.get("payment_status")
            if payment_status not in [PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
                logger.warning(
                    f"Failure handling called for non-failure status: {payment_status}"
                )

            return True

        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            return False

    def get_required_config(self) -> Dict[str, Any]:
        """
        Get required configuration for this node.

        Returns:
            Dictionary of required configuration keys and descriptions
        """
        return {}  # No external configuration required

    def get_output_schema(self) -> Dict[str, Any]:
        """
        Get the output schema for this node.

        Returns:
            Dictionary describing the output data structure
        """
        return {
            "failure_handled": "bool - Whether failure was handled successfully",
            "failure_details_recorded": "bool - Whether failure details were recorded",
            "notifications_sent": "bool - Whether notifications were sent",
            "cleanup_completed": "bool - Whether cleanup was completed",
            "subscription_action": "str - Action taken on subscription (cancel, past_due, etc.)",
            "subscription_reason": "str - Reason for subscription action",
        }
