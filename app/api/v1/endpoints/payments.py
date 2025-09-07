"""
Payment management endpoints with comprehensive CRUD operations.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from auth.dependencies import get_current_user, require_admin_or_teacher
from auth.models import UserContext, UserRole
from core.exceptions import (
    DatabaseError,
    NotFoundError,
    ValidationError,
)
from database.session import db_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.payment import BillingRecord, Payment, Subscription
from models.student import Student
from models.user import User
from schemas.common import APIResponse, PaginationMetadata
from schemas.payment_schemas import (
    BillingQueryParams,
    BillingRecordCreate,
    BillingRecordListResponse,
    BillingRecordResponse,
    LessonInfo,
    PaymentCreate,
    PaymentListResponse,
    PaymentQueryParams,
    PaymentResponse,
    PaymentStatus,
    PaymentSummary,
    PaymentUpdate,
    PaymentWorkflowRequest,
    PaymentWorkflowResponse,
    PaymentWorkflowStatus,
    StudentInfo,
    SubscriptionCancellation,
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionQueryParams,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from sqlalchemy import and_, desc, func, or_, text
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


# Payment CRUD Operations
@router.post(
    "/",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new payment",
    description="Create a new payment record with validation and processing",
)
async def create_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse:
    """Create a new payment with comprehensive validation."""
    logger.info(f"Creating payment for student {payment_data.student_id}")

    try:
        # Validate student exists
        student = (
            db.query(Student).filter(Student.id == payment_data.student_id).first()
        )
        if not student:
            raise NotFoundError(f"Student with ID {payment_data.student_id} not found")

        # Get parent user info
        parent = db.query(User).filter(User.id == student.parent_id).first()
        if not parent:
            raise NotFoundError(
                f"Parent user not found for student {payment_data.student_id}"
            )

        # Validate lesson exists if provided
        lesson = None
        if payment_data.lesson_id:
            from models.lesson import Lesson

            lesson = (
                db.query(Lesson).filter(Lesson.id == payment_data.lesson_id).first()
            )
            if not lesson:
                raise NotFoundError(
                    f"Lesson with ID {payment_data.lesson_id} not found"
                )

            # Ensure lesson belongs to the student
            if lesson.student_id != payment_data.student_id:
                raise ValidationError("Lesson does not belong to the specified student")

        # Create payment record
        payment = Payment(
            student_id=payment_data.student_id,
            lesson_id=payment_data.lesson_id,
            stripe_payment_intent_id=payment_data.stripe_payment_intent_id
            or f"pi_test_{datetime.utcnow().timestamp()}",
            amount=payment_data.amount,
            currency=payment_data.currency.value,
            payment_method=payment_data.payment_method.value,
            billing_cycle=payment_data.billing_cycle.value
            if payment_data.billing_cycle
            else "monthly",
            description=payment_data.description,
            status=PaymentStatus.PENDING.value,
            payment_date=payment_data.payment_date,
        )

        db.add(payment)
        db.flush()  # Get the ID without committing

        # Build response data
        response_data = {
            "id": payment.id,
            "student": {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
            },
            "lesson": None,
            "stripe_payment_intent_id": payment.stripe_payment_intent_id,
            "stripe_customer_id": payment.stripe_customer_id,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "billing_cycle": payment.billing_cycle,
            "description": payment.description,
            "status": payment.status,
            "payment_date": payment.payment_date.isoformat()
            if payment.payment_date
            else None,
            "failure_reason": payment.failure_reason,
            "metadata": payment.payment_metadata,
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat(),
        }

        # Add lesson info if exists
        if payment_data.lesson_id and lesson:
            # Get teacher info
            from models.teacher import Teacher

            teacher = (
                db.query(Teacher)
                .options(joinedload(Teacher.user))
                .filter(Teacher.id == lesson.teacher_id)
                .first()
            )
            if teacher:
                response_data["lesson"] = {
                    "id": lesson.id,
                    "scheduled_at": lesson.scheduled_at.isoformat(),
                    "teacher_name": f"{teacher.user.first_name} {teacher.user.last_name}",
                }

        logger.info(f"Payment {payment.id} created successfully")
        return APIResponse(
            success=True,
            message="Payment created successfully",
            data=response_data,
        )

    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create payment: {str(e)}"
        )


@router.get(
    "/",
    response_model=APIResponse,
    summary="List payments with filtering",
    description="Retrieve paginated list of payments with optional filtering",
)
async def list_payments(
    params: PaymentQueryParams = Depends(),
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
) -> APIResponse:
    """List payments with pagination and filtering."""
    logger.info(f"Listing payments with params: {params}")

    try:
        # Build base query
        query = db.query(Payment).join(Student)

        # Apply filters
        if params.student_id:
            query = query.filter(Payment.student_id == params.student_id)

        if params.status:
            query = query.filter(Payment.status == params.status.value)

        if params.date_from:
            query = query.filter(Payment.payment_date >= params.date_from)

        if params.date_to:
            query = query.filter(Payment.payment_date <= params.date_to)

        # Apply role-based filtering
        if current_user.role == UserRole.PARENT:
            # Parents can only see their own student's payments
            student_ids = [
                s.id
                for s in db.query(Student.id)
                .filter(Student.parent_id == current_user.user_id)
                .all()
            ]
            query = query.filter(Payment.student_id.in_(student_ids))

        # Get total count
        total_count = query.count()

        # Apply pagination and ordering
        payments = (
            query.order_by(desc(Payment.created_at))
            .offset((params.page - 1) * params.limit)
            .limit(params.limit)
            .all()
        )

        # Build response items
        payment_items = []
        for payment in payments:
            # Get student info
            student = db.query(Student).filter(Student.id == payment.student_id).first()
            payment_items.append(
                {
                    "id": payment.id,
                    "student_id": payment.student_id,
                    "student_name": f"{student.first_name} {student.last_name}"
                    if student
                    else "Unknown",
                    "lesson_id": payment.lesson_id,
                    "stripe_payment_intent_id": payment.stripe_payment_intent_id,
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                    "status": payment.status,
                    "payment_method": payment.payment_method,
                    "payment_date": payment.payment_date.isoformat()
                    if payment.payment_date
                    else None,
                    "billing_cycle": payment.billing_cycle,
                    "description": payment.description,
                    "created_at": payment.created_at.isoformat(),
                }
            )

        # Calculate summary statistics
        summary_query = query.with_entities(
            func.sum(Payment.amount).label("total_amount"),
            func.count(Payment.id)
            .filter(Payment.status == "succeeded")
            .label("successful_payments"),
            func.count(Payment.id)
            .filter(Payment.status == "failed")
            .label("failed_payments"),
            func.count(Payment.id)
            .filter(Payment.status == "pending")
            .label("pending_payments"),
            func.sum(Payment.amount)
            .filter(Payment.status == "refunded")
            .label("refunded_amount"),
        ).first()

        summary = {
            "total_amount": float(
                getattr(summary_query, "total_amount", None) or Decimal("0.00")
            ),
            "successful_payments": getattr(summary_query, "successful_payments", None)
            or 0,
            "failed_payments": getattr(summary_query, "failed_payments", None) or 0,
            "pending_payments": getattr(summary_query, "pending_payments", None) or 0,
            "refunded_amount": float(
                getattr(summary_query, "refunded_amount", None) or Decimal("0.00")
            ),
        }

        response_data = {
            "payments": payment_items,
            "summary": summary,
            "pagination": {
                "page": params.page,
                "limit": params.limit,
                "total": total_count,
                "pages": (total_count + params.limit - 1) // params.limit,
                "has_next": params.page * params.limit < total_count,
                "has_prev": params.page > 1,
            },
        }

        logger.info(f"Retrieved {len(payment_items)} payments")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(payment_items)} payments",
            data=response_data,
        )

    except Exception as e:
        logger.error(f"Error listing payments: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve payments: {str(e)}"
        )


@router.get(
    "/{payment_id}",
    response_model=APIResponse,
    summary="Get payment details",
    description="Retrieve detailed information about a specific payment",
)
async def get_payment(
    payment_id: int,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
) -> APIResponse:
    """Get detailed payment information."""
    logger.info(f"Retrieving payment {payment_id}")

    try:
        # Get payment
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=404, detail=f"Payment with ID {payment_id} not found"
            )

        # Get student info
        student = db.query(Student).filter(Student.id == payment.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found for payment")

        # Check role-based access
        if current_user.role == UserRole.PARENT:
            if student.parent_id != current_user.user_id:
                raise HTTPException(
                    status_code=403, detail="Access denied to this payment"
                )

        # Build response data
        response_data = {
            "id": payment.id,
            "student": {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
            },
            "lesson": None,
            "stripe_payment_intent_id": payment.stripe_payment_intent_id,
            "stripe_customer_id": payment.stripe_customer_id,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "billing_cycle": payment.billing_cycle,
            "description": payment.description,
            "status": payment.status,
            "payment_date": payment.payment_date.isoformat()
            if payment.payment_date
            else None,
            "failure_reason": payment.failure_reason,
            "metadata": payment.payment_metadata,
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat(),
        }

        # Add lesson info if exists
        if payment.lesson_id:
            from models.lesson import Lesson
            from models.teacher import Teacher

            lesson = db.query(Lesson).filter(Lesson.id == payment.lesson_id).first()
            if lesson:
                teacher = (
                    db.query(Teacher)
                    .options(joinedload(Teacher.user))
                    .filter(Teacher.id == lesson.teacher_id)
                    .first()
                )
                if teacher:
                    response_data["lesson"] = {
                        "id": lesson.id,
                        "scheduled_at": lesson.scheduled_at.isoformat(),
                        "teacher_name": f"{teacher.user.first_name} {teacher.user.last_name}",
                    }

        logger.info(f"Payment {payment_id} retrieved successfully")
        return APIResponse(
            success=True,
            message="Payment retrieved successfully",
            data=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving payment {payment_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve payment: {str(e)}"
        )


@router.patch(
    "/{payment_id}",
    response_model=APIResponse,
    summary="Update payment",
    description="Update payment status and related information",
)
async def update_payment(
    payment_id: int,
    payment_update: PaymentUpdate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse:
    """Update payment information."""
    logger.info(f"Updating payment {payment_id}")

    try:
        # Get existing payment
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=404, detail=f"Payment with ID {payment_id} not found"
            )

        # Update fields
        update_data = payment_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status" and value:
                setattr(payment, field, value.value)
            elif field == "metadata":
                payment.payment_metadata = value
            else:
                setattr(payment, field, value)

        db.flush()

        # Get student info for response
        student = db.query(Student).filter(Student.id == payment.student_id).first()

        # Build response data
        response_data = {
            "id": payment.id,
            "student": {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
            }
            if student
            else None,
            "lesson": None,
            "stripe_payment_intent_id": payment.stripe_payment_intent_id,
            "stripe_customer_id": payment.stripe_customer_id,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "billing_cycle": payment.billing_cycle,
            "description": payment.description,
            "status": payment.status,
            "payment_date": payment.payment_date.isoformat()
            if payment.payment_date
            else None,
            "failure_reason": payment.failure_reason,
            "metadata": payment.payment_metadata,
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat(),
        }

        logger.info(f"Payment {payment_id} updated successfully")
        return APIResponse(
            success=True,
            message="Payment updated successfully",
            data=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment {payment_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update payment: {str(e)}"
        )


@router.delete(
    "/{payment_id}",
    response_model=APIResponse,
    summary="Delete payment",
    description="Soft delete a payment record (admin only)",
)
async def delete_payment(
    payment_id: int,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse:
    """Soft delete a payment record."""
    logger.info(f"Deleting payment {payment_id}")

    try:
        # Only admins can delete payments
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403, detail="Only administrators can delete payments"
            )

        # Get payment
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=404, detail=f"Payment with ID {payment_id} not found"
            )

        # Check if payment can be deleted (only pending/failed payments)
        if payment.status in ["succeeded", "refunded"]:
            raise HTTPException(
                status_code=400, detail="Cannot delete processed payments"
            )

        # Soft delete by updating status
        payment.status = "cancelled"

        logger.info(f"Payment {payment_id} deleted successfully")
        return APIResponse(
            success=True,
            message="Payment deleted successfully",
            data={"deleted_payment_id": payment_id},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payment {payment_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete payment: {str(e)}"
        )


# Subscription Management
@router.post(
    "/subscriptions",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create subscription",
    description="Create a new subscription for recurring payments",
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse:
    """Create a new subscription."""
    logger.info(f"Creating subscription for student {subscription_data.student_id}")

    try:
        # Validate student exists
        student = (
            db.query(Student).filter(Student.id == subscription_data.student_id).first()
        )
        if not student:
            raise HTTPException(
                status_code=404,
                detail=f"Student with ID {subscription_data.student_id} not found",
            )

        # Create subscription
        subscription = Subscription(
            student_id=subscription_data.student_id,
            stripe_subscription_id=f"sub_test_{datetime.utcnow().timestamp()}",
            stripe_customer_id=subscription_data.stripe_customer_id,
            billing_cycle=subscription_data.billing_cycle.value,
            amount=subscription_data.amount,
            currency=subscription_data.currency.value,
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow().replace(
                month=datetime.utcnow().month + 1
            ),
        )

        db.add(subscription)
        db.flush()

        response_data = {
            "id": subscription.id,
            "student_id": subscription.student_id,
            "student_name": f"{student.first_name} {student.last_name}",
            "stripe_subscription_id": subscription.stripe_subscription_id,
            "stripe_customer_id": subscription.stripe_customer_id,
            "billing_cycle": subscription.billing_cycle,
            "amount": float(subscription.amount),
            "currency": subscription.currency,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat()
            if subscription.current_period_start
            else None,
            "current_period_end": subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None,
            "created_at": subscription.created_at.isoformat(),
            "updated_at": subscription.updated_at.isoformat(),
        }

        logger.info(f"Subscription {subscription.id} created successfully")
        return APIResponse(
            success=True,
            message="Subscription created successfully",
            data=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create subscription: {str(e)}"
        )


@router.get(
    "/subscriptions",
    response_model=APIResponse,
    summary="List subscriptions",
    description="Retrieve paginated list of subscriptions",
)
async def list_subscriptions(
    params: SubscriptionQueryParams = Depends(),
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
) -> APIResponse:
    """List subscriptions with pagination and filtering."""
    logger.info(f"Listing subscriptions with params: {params}")

    try:
        # Build base query
        query = db.query(Subscription).join(Student)

        # Apply filters
        if params.student_id:
            query = query.filter(Subscription.student_id == params.student_id)

        if params.status:
            query = query.filter(Subscription.status == params.status.value)

        # Apply role-based filtering
        if current_user.role == UserRole.PARENT:
            student_ids = [
                s.id
                for s in db.query(Student.id)
                .filter(Student.parent_id == current_user.user_id)
                .all()
            ]
            query = query.filter(Subscription.student_id.in_(student_ids))

        # Get total count
        total_count = query.count()

        # Apply pagination and ordering
        subscriptions = (
            query.order_by(desc(Subscription.created_at))
            .offset((params.page - 1) * params.limit)
            .limit(params.limit)
            .all()
        )

        # Build response items
        subscription_items = []
        for subscription in subscriptions:
            student = (
                db.query(Student).filter(Student.id == subscription.student_id).first()
            )
            subscription_items.append(
                {
                    "id": subscription.id,
                    "student_id": subscription.student_id,
                    "student_name": f"{student.first_name} {student.last_name}"
                    if student
                    else "Unknown",
                    "stripe_subscription_id": subscription.stripe_subscription_id,
                    "stripe_customer_id": subscription.stripe_customer_id,
                    "billing_cycle": subscription.billing_cycle,
                    "amount": float(subscription.amount),
                    "currency": subscription.currency,
                    "status": subscription.status,
                    "current_period_start": subscription.current_period_start.isoformat()
                    if subscription.current_period_start
                    else None,
                    "current_period_end": subscription.current_period_end.isoformat()
                    if subscription.current_period_end
                    else None,
                    "created_at": subscription.created_at.isoformat(),
                    "updated_at": subscription.updated_at.isoformat(),
                }
            )

        response_data = {
            "subscriptions": subscription_items,
            "pagination": {
                "page": params.page,
                "limit": params.limit,
                "total": total_count,
                "pages": (total_count + params.limit - 1) // params.limit,
                "has_next": params.page * params.limit < total_count,
                "has_prev": params.page > 1,
            },
        }

        logger.info(f"Retrieved {len(subscription_items)} subscriptions")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(subscription_items)} subscriptions",
            data=response_data,
        )

    except Exception as e:
        logger.error(f"Error listing subscriptions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve subscriptions: {str(e)}"
        )


# Workflow endpoints (simplified implementation)
@router.post(
    "/workflows/process",
    response_model=APIResponse,
    summary="Process payment workflow",
    description="Execute payment processing workflow",
)
async def process_payment_workflow(
    workflow_request: PaymentWorkflowRequest,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse:
    """Process payment through workflow system."""
    logger.info(
        f"Processing payment workflow for student {workflow_request.student_id}"
    )

    try:
        # Mock workflow processing for now
        workflow_id = f"wf_{datetime.utcnow().timestamp()}"

        response_data = {
            "workflow_id": workflow_id,
            "status": "completed",
            "execution_time": 0.5,
            "results": {
                "payment_created": True,
                "amount_processed": float(workflow_request.amount),
                "student_id": workflow_request.student_id,
            },
        }

        logger.info(f"Payment workflow {workflow_id} completed successfully")
        return APIResponse(
            success=True,
            message="Payment workflow processed successfully",
            data=response_data,
        )

    except Exception as e:
        logger.error(f"Error processing payment workflow: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process payment workflow: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_id}/status",
    response_model=APIResponse,
    summary="Get workflow status",
    description="Check the status of a payment workflow",
)
async def get_workflow_status(
    workflow_id: str,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse:
    """Get payment workflow status."""
    logger.info(f"Retrieving workflow status for {workflow_id}")

    try:
        # Mock workflow status for now
        response_data = {
            "workflow_id": workflow_id,
            "status": "completed",
            "progress": 100,
            "current_node": "payment_processed",
            "nodes_executed": [
                "validate_payment",
                "process_payment",
                "send_confirmation",
            ],
            "execution_time": 1.2,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Workflow status retrieved for {workflow_id}")
        return APIResponse(
            success=True,
            message="Workflow status retrieved successfully",
            data=response_data,
        )

    except Exception as e:
        logger.error(f"Error retrieving workflow status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve workflow status: {str(e)}"
        )
