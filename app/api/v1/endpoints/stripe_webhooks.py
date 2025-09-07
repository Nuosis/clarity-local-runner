import json
import logging
from http import HTTPStatus
from typing import Dict

from database.event import Event
from database.repository import GenericRepository
from database.session import db_session
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from schemas.stripe_webhook_schema import StripeWebhookEventSchema
from services.stripe_webhook_service import stripe_webhook_service
from sqlalchemy.orm import Session
from starlette.responses import Response
from worker.config import celery_app

logger = logging.getLogger(__name__)

"""
Stripe Webhook Endpoint Module

This module provides a dedicated endpoint for Stripe webhook events that leverages
the existing event infrastructure. It implements a hybrid approach:

1. Stripe-specific validation and security (signature verification)
2. Idempotency handling for duplicate events
3. Delegation to existing event processing pipeline
4. Leverages existing workflow routing and Celery processing

The endpoint follows the "validate-and-delegate" pattern where:
- Stripe webhooks are validated and secured at this endpoint
- After validation, events are processed through the existing event system
- This maintains DRY principles while providing Stripe-specific security
"""

router = APIRouter()


@router.post("/stripe", dependencies=[])
async def handle_stripe_webhook(
    request: Request,
    session: Session = Depends(db_session),
    stripe_signature: str = Header(None, alias="stripe-signature"),
) -> Response:
    """
    Handles incoming Stripe webhook events with signature verification.

    This endpoint provides Stripe-specific security and validation, then delegates
    to the existing event processing system. It implements:

    1. Stripe webhook signature verification
    2. Event structure validation using StripeWebhookEventSchema
    3. Idempotency handling for duplicate events
    4. Integration with existing event storage and workflow processing

    Args:
        request: FastAPI request object containing the raw webhook payload
        session: Database session injected by FastAPI dependency
        stripe_signature: Stripe-Signature header for webhook verification

    Returns:
        Response: 202 Accepted response with task ID for successful processing
                 400 Bad Request for validation failures
                 409 Conflict for duplicate events

    Raises:
        HTTPException: For signature verification failures or validation errors
    """
    try:
        # Get raw payload for signature verification
        raw_payload = await request.body()

        # Verify Stripe webhook signature
        if stripe_signature:
            stripe_webhook_service.verify_signature(
                payload=raw_payload, signature_header=stripe_signature
            )
            logger.info("Stripe webhook signature verified successfully")
        else:
            logger.warning("No Stripe signature header provided")
            if not stripe_webhook_service.webhook_secret:
                logger.info(
                    "Webhook signature verification skipped - no secret configured"
                )
            else:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Missing Stripe-Signature header",
                )

        # Parse and validate the webhook event
        try:
            webhook_data = json.loads(raw_payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook payload: {e}")
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail="Invalid JSON payload"
            )

        # Validate using Stripe webhook schema
        try:
            stripe_event = StripeWebhookEventSchema(**webhook_data)
            logger.info(
                f"Stripe webhook event validated: {stripe_event.type} (ID: {stripe_event.id})"
            )
        except Exception as e:
            logger.error(f"Stripe webhook validation failed: {e}")
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Invalid Stripe webhook event structure: {str(e)}",
            )

        # Generate idempotency key and check for duplicates
        idempotency_key = stripe_webhook_service.generate_idempotency_key(webhook_data)

        if stripe_webhook_service.is_duplicate_event(stripe_event.id, idempotency_key):
            logger.info(f"Duplicate Stripe webhook event ignored: {stripe_event.id}")
            return Response(
                content=json.dumps(
                    {
                        "message": "Duplicate event ignored",
                        "event_id": stripe_event.id,
                        "idempotency_key": idempotency_key,
                    }
                ),
                status_code=HTTPStatus.CONFLICT,
                headers={"Content-Type": "application/json"},
            )

        # Extract metadata for logging and monitoring
        event_metadata = stripe_webhook_service.extract_event_metadata(webhook_data)
        logger.info(f"Processing Stripe webhook: {event_metadata}")

        # Store event in database using existing Event model
        repository = GenericRepository(
            session=session,
            model=Event,
        )

        # Enhance event data with idempotency key for better tracking
        enhanced_webhook_data = webhook_data.copy()
        enhanced_webhook_data["idempotency_key"] = idempotency_key

        # Create event with Stripe-specific workflow type
        event = Event(
            data=enhanced_webhook_data,
            workflow_type=get_stripe_workflow_type(stripe_event),
        )
        repository.create(obj=event)

        # Queue processing task using existing Celery infrastructure
        task_id = celery_app.send_task(
            "process_incoming_event",
            args=[str(event.id)],
        )

        logger.info(
            f"Stripe webhook queued for processing: task_id={task_id}, event_id={event.id}"
        )

        # Return acceptance response
        return Response(
            content=json.dumps(
                {
                    "message": f"Stripe webhook accepted and queued for processing",
                    "task_id": str(task_id),
                    "event_id": str(event.id),
                    "stripe_event_id": stripe_event.id,
                    "stripe_event_type": stripe_event.type,
                }
            ),
            status_code=HTTPStatus.ACCEPTED,
            headers={"Content-Type": "application/json"},
        )

    except HTTPException:
        # Re-raise HTTP exceptions (signature verification, validation errors)
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing Stripe webhook: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook",
        )


def get_stripe_workflow_type(stripe_event: StripeWebhookEventSchema) -> str:
    """
    Determine the appropriate workflow type for a Stripe webhook event.

    This function routes Stripe events to the appropriate workflow based on
    the event type. For Phase 1, we only handle invoice events and route
    them to the new SUBSCRIPTION_PAYMENT workflow.

    Args:
        stripe_event: Validated Stripe webhook event

    Returns:
        str: Workflow type name for routing to appropriate workflow
    """
    # Phase 1: Only handle invoice events
    if stripe_event.is_invoice_event():
        return "SUBSCRIPTION_PAYMENT"

    # For non-invoice events, route to existing PAYMENT workflow
    if stripe_event.is_payment_event():
        return "PAYMENT"

    # For unknown event types, log and route to a default workflow
    logger.warning(
        f"Unknown Stripe event type: {stripe_event.type}, routing to PAYMENT workflow"
    )
    return "PAYMENT"


@router.get("/stripe/health")
def stripe_webhook_health() -> Dict[str, str]:
    """
    Health check endpoint for Stripe webhook integration.

    Returns:
        Dict: Health status and configuration information
    """
    webhook_secret_configured = bool(stripe_webhook_service.webhook_secret)

    return {
        "status": "healthy",
        "webhook_secret_configured": str(webhook_secret_configured),
        "service": "stripe_webhooks",
    }
