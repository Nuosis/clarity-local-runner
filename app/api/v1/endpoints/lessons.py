"""
Lesson management endpoints for Cedar Heights Music Academy API.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Union
from uuid import UUID

from auth.dependencies import get_current_user, require_admin_or_teacher
from auth.models import UserContext
from core.exceptions import NotFoundError, ValidationError
from database.session import db_session
from fastapi import APIRouter, Depends, Query, status
from models.lesson import Lesson
from models.student import Student
from models.teacher import Teacher
from models.user import User
from schemas.common import APIResponse, PaginationMetadata
from schemas.lesson_schemas import (
    ConflictCheck,
    ConflictCheckResponse,
    LessonCancellation,
    LessonCreate,
    LessonListItem,
    LessonListResponse,
    LessonQueryParams,
    LessonResponse,
    LessonStatus,
    LessonType,
    LessonUpdate,
    PaymentStatus,
    ScheduleQueryParams,
    ScheduleResponse,
)
from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

router = APIRouter()


def check_lesson_conflicts(
    db: Session,
    teacher_id: int,
    scheduled_at: datetime,
    duration_minutes: int,
    exclude_lesson_id: Optional[Union[int, UUID]] = None,
) -> List[Lesson]:
    """
    Check for scheduling conflicts for a teacher at a specific time.
    Returns list of conflicting lessons.
    """
    lesson_end_time = scheduled_at + timedelta(minutes=duration_minutes)

    # Get all scheduled lessons for the teacher
    query = db.query(Lesson).filter(
        and_(
            Lesson.teacher_id == teacher_id,
            Lesson.status.in_(["scheduled", "confirmed"]),
        )
    )

    if exclude_lesson_id:
        query = query.filter(Lesson.id != exclude_lesson_id)

    existing_lessons = query.all()

    # Check for conflicts in Python (more reliable than complex SQL)
    conflicts = []
    for lesson in existing_lessons:
        existing_end = lesson.scheduled_at + timedelta(minutes=lesson.duration_minutes)

        # Check if times overlap
        if scheduled_at < existing_end and lesson_end_time > lesson.scheduled_at:
            conflicts.append(lesson)

    return conflicts


@router.get("/", response_model=APIResponse[LessonListResponse])
async def list_lessons(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    student_id: Optional[int] = Query(None, gt=0, description="Filter by student ID"),
    teacher_id: Optional[int] = Query(None, gt=0, description="Filter by teacher ID"),
    status: Optional[LessonStatus] = Query(None, description="Filter by status"),
    lesson_type: Optional[LessonType] = Query(
        None, description="Filter by lesson type"
    ),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    include_notes: bool = Query(False, description="Include lesson notes"),
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[LessonListResponse]:
    """
    List lessons with filtering and pagination.

    Requires ADMIN or TEACHER permissions.
    """
    query = db.query(Lesson).join(Student).join(Teacher).join(User)

    # Apply filters
    if student_id:
        query = query.filter(Lesson.student_id == student_id)

    if teacher_id:
        query = query.filter(Lesson.teacher_id == teacher_id)

    if status:
        query = query.filter(Lesson.status == status.value)

    if lesson_type:
        query = query.filter(Lesson.lesson_type == lesson_type.value)

    if date_from:
        query = query.filter(
            Lesson.scheduled_at >= datetime.combine(date_from, datetime.min.time())
        )

    if date_to:
        query = query.filter(
            Lesson.scheduled_at <= datetime.combine(date_to, datetime.max.time())
        )

    # Order by scheduled date (most recent first)
    query = query.order_by(Lesson.scheduled_at.desc())

    # Get total count
    total = query.count()

    # Apply pagination
    skip = (page - 1) * limit
    lessons = query.offset(skip).limit(limit).all()

    # Calculate pagination metadata
    pages = (total + limit - 1) // limit
    pagination = PaginationMetadata(
        page=page,
        limit=limit,
        total=total,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )

    # Convert to list items with proper field mapping
    lesson_list_items = []
    for lesson in lessons:
        lesson_item = LessonListItem(
            id=lesson.id,
            student_id=lesson.student_id,
            student_name=f"{lesson.student.user.first_name} {lesson.student.user.last_name}",
            teacher_id=lesson.teacher_id,
            teacher_name=f"{lesson.teacher.user.first_name} {lesson.teacher.user.last_name}",
            scheduled_at=lesson.scheduled_at,
            duration_minutes=lesson.duration_minutes,
            lesson_type=LessonType(lesson.lesson_type),
            status=LessonStatus(lesson.status),
            payment_status=PaymentStatus(lesson.payment_status),
            attendance_marked=lesson.attendance_marked,
            teacher_notes=lesson.teacher_notes if include_notes else None,
            student_progress_notes=lesson.student_progress_notes
            if include_notes
            else None,
            timeslot_id=lesson.timeslot_id,
            semester_id=lesson.semester_id,
            created_at=lesson.created_at,
        )
        lesson_list_items.append(lesson_item)

    return APIResponse(
        success=True,
        data=LessonListResponse(lessons=lesson_list_items, pagination=pagination),
        message=f"Retrieved {len(lessons)} lessons",
    )


@router.post(
    "/",
    response_model=APIResponse[LessonResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson(
    lesson_data: LessonCreate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[LessonResponse]:
    """
    Create a new lesson.

    Requires ADMIN or TEACHER permissions.
    """
    # Validate student exists
    student = db.query(Student).filter(Student.id == lesson_data.student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    # Validate teacher exists
    teacher = db.query(Teacher).filter(Teacher.id == lesson_data.teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")

    # Check for scheduling conflicts
    conflicts = check_lesson_conflicts(
        db,
        lesson_data.teacher_id,
        lesson_data.scheduled_at,
        lesson_data.duration_minutes,
    )

    if conflicts:
        raise ValidationError("Teacher has a scheduling conflict at this time")

    # Create new lesson
    lesson = Lesson(
        student_id=lesson_data.student_id,
        teacher_id=lesson_data.teacher_id,
        timeslot_id=lesson_data.timeslot_id,
        semester_id=lesson_data.semester_id,
        scheduled_at=lesson_data.scheduled_at,
        duration_minutes=lesson_data.duration_minutes,
        lesson_type=lesson_data.lesson_type.value,
        teacher_notes=lesson_data.teacher_notes,
        student_progress_notes=lesson_data.student_progress_notes,
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    # Load relationships for response
    lesson_with_relations = (
        db.query(Lesson)
        .join(Student)
        .join(Teacher)
        .filter(Lesson.id == lesson.id)
        .first()
    )

    return APIResponse(
        success=True,
        data=LessonResponse.from_orm(lesson_with_relations),
        message="Lesson created successfully",
    )


@router.get("/{lesson_id}", response_model=APIResponse[LessonResponse])
async def get_lesson(
    lesson_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[LessonResponse]:
    """
    Get a specific lesson by ID.

    Requires ADMIN or TEACHER permissions.
    """
    lesson = (
        db.query(Lesson)
        .join(Student)
        .join(Teacher)
        .filter(Lesson.id == lesson_id)
        .first()
    )
    if not lesson:
        raise NotFoundError("Lesson not found")

    return APIResponse(
        success=True,
        data=LessonResponse.from_orm(lesson),
        message="Lesson retrieved successfully",
    )


@router.put("/{lesson_id}", response_model=APIResponse[LessonResponse])
async def update_lesson(
    lesson_id: UUID,
    lesson_data: LessonUpdate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[LessonResponse]:
    """
    Update a lesson's information.

    Requires ADMIN or TEACHER permissions.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise NotFoundError("Lesson not found")

    # Check for scheduling conflicts if time is being changed
    if lesson_data.scheduled_at and lesson_data.scheduled_at != lesson.scheduled_at:
        duration = lesson_data.duration_minutes or lesson.duration_minutes

        conflicts = check_lesson_conflicts(
            db,
            lesson.teacher_id,
            lesson_data.scheduled_at,
            duration,
            exclude_lesson_id=lesson_id,
        )

        if conflicts:
            raise ValidationError("Teacher has a scheduling conflict at this time")

    # Update lesson fields
    update_data = lesson_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(lesson, field, value.value)
        elif field == "payment_status" and value:
            setattr(lesson, field, value.value)
        else:
            setattr(lesson, field, value)

    db.commit()
    db.refresh(lesson)

    # Load relationships for response
    lesson_with_relations = (
        db.query(Lesson)
        .join(Student)
        .join(Teacher)
        .filter(Lesson.id == lesson_id)
        .first()
    )

    return APIResponse(
        success=True,
        data=LessonResponse.from_orm(lesson_with_relations),
        message="Lesson updated successfully",
    )


@router.delete("/{lesson_id}", response_model=APIResponse[dict])
async def delete_lesson(
    lesson_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[dict]:
    """
    Delete a lesson (hard delete).

    Requires ADMIN or TEACHER permissions.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise NotFoundError("Lesson not found")

    # Only allow deletion of scheduled lessons
    if lesson.status not in ["scheduled"]:
        raise ValidationError("Can only delete scheduled lessons")

    db.delete(lesson)
    db.commit()

    return APIResponse(
        success=True,
        data={"id": str(lesson_id), "deleted": True},
        message="Lesson deleted successfully",
    )


@router.post("/{lesson_id}/cancel", response_model=APIResponse[LessonResponse])
async def cancel_lesson(
    lesson_id: UUID,
    cancellation_data: LessonCancellation,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[LessonResponse]:
    """
    Cancel a lesson with reason and notification options.

    Requires ADMIN or TEACHER permissions.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise NotFoundError("Lesson not found")

    if lesson.status != "scheduled":
        raise ValidationError("Can only cancel scheduled lessons")

    # Update lesson status
    lesson.status = "cancelled"
    lesson.teacher_notes = f"Cancelled: {cancellation_data.cancellation_reason}"

    db.commit()
    db.refresh(lesson)

    # TODO: Implement notification system if notify_parent is True
    # TODO: Implement makeup lesson creation if offer_makeup is True

    # Load relationships for response
    lesson_with_relations = (
        db.query(Lesson)
        .join(Student)
        .join(Teacher)
        .filter(Lesson.id == lesson_id)
        .first()
    )

    return APIResponse(
        success=True,
        data=LessonResponse.from_orm(lesson_with_relations),
        message="Lesson cancelled successfully",
    )


@router.post("/{lesson_id}/complete", response_model=APIResponse[LessonResponse])
async def complete_lesson(
    lesson_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[LessonResponse]:
    """
    Mark a lesson as completed.

    Requires ADMIN or TEACHER permissions.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise NotFoundError("Lesson not found")

    if lesson.status != "scheduled":
        raise ValidationError("Can only complete scheduled lessons")

    # Update lesson status
    lesson.status = "completed"
    lesson.attendance_marked = True

    db.commit()
    db.refresh(lesson)

    # Load relationships for response
    lesson_with_relations = (
        db.query(Lesson)
        .join(Student)
        .join(Teacher)
        .filter(Lesson.id == lesson_id)
        .first()
    )

    return APIResponse(
        success=True,
        data=LessonResponse.from_orm(lesson_with_relations),
        message="Lesson marked as completed",
    )


@router.post("/check-conflicts", response_model=APIResponse[ConflictCheckResponse])
async def check_scheduling_conflicts(
    conflict_check: ConflictCheck,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[ConflictCheckResponse]:
    """
    Check for scheduling conflicts before creating/updating a lesson.

    Requires ADMIN or TEACHER permissions.
    """
    conflicts = check_lesson_conflicts(
        db,
        conflict_check.teacher_id,
        conflict_check.scheduled_at,
        conflict_check.duration_minutes,
        exclude_lesson_id=conflict_check.exclude_lesson_id,
    )

    has_conflicts = len(conflicts) > 0

    # Format conflict information
    conflict_info = []
    for conflict in conflicts:
        conflict_info.append(
            {
                "lesson_id": conflict.id,
                "scheduled_at": conflict.scheduled_at.isoformat(),
                "duration_minutes": conflict.duration_minutes,
                "student_name": f"{conflict.student.user.first_name} {conflict.student.user.last_name}",
            }
        )

    # TODO: Implement suggested alternative times logic
    suggested_times = []

    return APIResponse(
        success=True,
        data=ConflictCheckResponse(
            has_conflicts=has_conflicts,
            conflicts=conflict_info,
            available=not has_conflicts,
            suggested_times=suggested_times,
        ),
        message="Conflict check completed",
    )


@router.get("/schedule/view", response_model=APIResponse[ScheduleResponse])
async def get_schedule_view(
    view: str = Query("week", description="Schedule view type"),
    schedule_date: Optional[date] = Query(None, description="Center date for view"),
    teacher_id: Optional[int] = Query(None, gt=0, description="Filter by teacher ID"),
    student_id: Optional[int] = Query(None, gt=0, description="Filter by student ID"),
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[ScheduleResponse]:
    """
    Get schedule view (day/week/month) with lessons.

    Requires ADMIN or TEACHER permissions.
    """
    # TODO: Implement comprehensive schedule view logic
    # For now, return a basic structure

    if not schedule_date:
        schedule_date = date.today()

    # Basic query for lessons
    query = db.query(Lesson).join(Student).join(Teacher)

    if teacher_id:
        query = query.filter(Lesson.teacher_id == teacher_id)

    if student_id:
        query = query.filter(Lesson.student_id == student_id)

    # Filter by date range based on view
    if view == "day":
        start_date = datetime.combine(schedule_date, datetime.min.time())
        end_date = datetime.combine(schedule_date, datetime.max.time())
    elif view == "week":
        # Simple week view - can be enhanced
        start_date = datetime.combine(schedule_date, datetime.min.time())
        end_date = datetime.combine(schedule_date, datetime.max.time())
    else:  # month
        start_date = datetime.combine(schedule_date.replace(day=1), datetime.min.time())
        end_date = datetime.combine(schedule_date, datetime.max.time())

    query = query.filter(
        Lesson.scheduled_at >= start_date, Lesson.scheduled_at <= end_date
    )

    lessons = query.order_by(Lesson.scheduled_at).all()

    # TODO: Format lessons into proper schedule structure
    schedule_data = ScheduleResponse(
        view=view,
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        schedule=[],  # TODO: Implement proper schedule formatting
        teachers=[],  # TODO: Implement teacher summary
    )

    return APIResponse(
        success=True,
        data=schedule_data,
        message=f"Retrieved {view} schedule view",
    )
