"""
Brevo (formerly Sendinblue) email service integration.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


class BrevoEmailService:
    """Service for sending emails through Brevo API."""

    def __init__(self):
        """Initialize Brevo email service with API key."""
        self.api_key = os.getenv("BREVO_API_KEY")
        if not self.api_key:
            logging.warning("BREVO_API_KEY not found in environment variables")
            self.client = None
        else:
            # Configure API key authorization
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key["api-key"] = self.api_key

            # Create API instance
            self.client = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )

    async def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
        template_id: Optional[int] = None,
        template_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email through Brevo.

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
            sender_email: Sender email (defaults to configured sender)
            sender_name: Sender name (defaults to configured sender)
            template_id: Brevo template ID (optional)
            template_params: Template parameters (optional)

        Returns:
            Dict containing success status and message ID or error details
        """
        try:
            if not self.client:
                return {
                    "success": False,
                    "error": "Brevo client not initialized - check API key configuration",
                }

            # Set default sender if not provided
            if not sender_email:
                sender_email = os.getenv(
                    "BREVO_SENDER_EMAIL", "noreply@cedarheights.com"
                )
            if not sender_name:
                sender_name = os.getenv(
                    "BREVO_SENDER_NAME", "Cedar Heights Music Academy"
                )

            # Create sender object
            sender = sib_api_v3_sdk.SendSmtpEmailSender(
                name=sender_name, email=sender_email
            )

            # Create recipient object
            to = [sib_api_v3_sdk.SendSmtpEmailTo(email=to_email, name=to_name)]

            # Create email object
            if template_id:
                # Use template-based email
                send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                    to=to,
                    template_id=template_id,
                    params=template_params or {},
                    sender=sender,
                )
            else:
                # Use content-based email
                send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                    to=to,
                    html_content=html_content,
                    text_content=text_content,
                    subject=subject,
                    sender=sender,
                )

            # Send the email
            api_response = self.client.send_transac_email(send_smtp_email)

            logging.info(
                f"Email sent successfully to {to_email}. Message ID: {api_response.message_id}"
            )

            return {
                "success": True,
                "message_id": api_response.message_id,
                "recipient": to_email,
            }

        except ApiException as e:
            error_msg = f"Brevo API error: {e.status} - {e.reason}"
            logging.error(f"Failed to send email to {to_email}: {error_msg}")
            return {"success": False, "error": error_msg, "status_code": e.status}
        except Exception as e:
            error_msg = f"Unexpected error sending email: {str(e)}"
            logging.error(f"Failed to send email to {to_email}: {error_msg}")
            return {"success": False, "error": error_msg}

    async def send_bulk_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple emails in bulk.

        Args:
            emails: List of email dictionaries with required fields

        Returns:
            Dict containing overall success status and individual results
        """
        results = []
        successful_sends = 0

        for email_data in emails:
            result = await self.send_email(**email_data)
            results.append(result)
            if result["success"]:
                successful_sends += 1

        return {
            "success": successful_sends > 0,
            "total_emails": len(emails),
            "successful_sends": successful_sends,
            "failed_sends": len(emails) - successful_sends,
            "results": results,
        }

    def is_configured(self) -> bool:
        """Check if the Brevo service is properly configured."""
        return self.client is not None and self.api_key is not None

    def get_account_info(self) -> Dict[str, Any]:
        """Get Brevo account information for debugging."""
        try:
            if not self.client:
                return {"error": "Client not initialized"}

            # This would require the account API, but for now return basic info
            return {
                "configured": True,
                "api_key_present": bool(self.api_key),
                "sender_email": os.getenv("BREVO_SENDER_EMAIL", "Not configured"),
                "sender_name": os.getenv("BREVO_SENDER_NAME", "Not configured"),
            }
        except Exception as e:
            return {"error": str(e)}


# Global instance
brevo_service = BrevoEmailService()
