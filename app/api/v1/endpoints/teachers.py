"""
Teacher management endpoints for Cedar Heights Music Academy API.
"""

from typing import List, Optional
from uuid import UUID

from auth.dependencies import get_current_user, require_admin_or_teacher
from auth.models import UserContext
from core.exceptions import NotFoundError, ValidationError
from database.session import db_session
from fastapi import APIRouter, Depends, Query, status
from models.teacher import Teacher
from models.user import User
from schemas.common import APIResponse, PaginationMetadata
from schemas.teacher_schemas import (
    AvailabilitySlotUpdate,
    Instrument,
    TeacherCreate,
    TeacherListItem,
    TeacherListResponse,
    TeacherResponse,
    TeacherUpdate,
)
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=APIResponse[TeacherListResponse])
async def list_teachers(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, min_length=1, max_length=100, description="Search by name"
    ),
    instrument: Optional[Instrument] = Query(None, description="Filter by instrument"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[TeacherListResponse]:
    """
    List teachers with filtering and pagination.

    Requires ADMIN or TEACHER permissions.
    """
    query = db.query(Teacher)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.join(User).filter(
            User.first_name.ilike(search_term)
            | User.last_name.ilike(search_term)
            | User.email.ilike(search_term)
        )

    if instrument:
        # Filter by teachers who teach this instrument
        query = query.filter(Teacher.instruments.contains([instrument]))

    if is_active is not None:
        query = query.filter(Teacher.is_available == is_active)

    # Get total count
    total = query.count()

    # Apply pagination
    skip = (page - 1) * limit
    teachers = query.offset(skip).limit(limit).all()

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

    teacher_list_items = [TeacherListItem.from_orm(teacher) for teacher in teachers]

    return APIResponse(
        success=True,
        data=TeacherListResponse(teachers=teacher_list_items, pagination=pagination),
        message=f"Retrieved {len(teachers)} teachers",
    )


@router.post(
    "/",
    response_model=APIResponse[TeacherResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_teacher(
    teacher_data: TeacherCreate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[TeacherResponse]:
    """
    Create a new teacher.

    Requires ADMIN or TEACHER permissions.
    """
    # Check if user_id exists and is valid
    user = db.query(User).filter(User.id == teacher_data.user_id).first()
    if not user:
        raise ValidationError("User not found")

    # Check if user already has a teacher profile
    existing_teacher = (
        db.query(Teacher).filter(Teacher.user_id == teacher_data.user_id).first()
    )
    if existing_teacher:
        raise ValidationError("User already has a teacher profile")

    # Create new teacher
    teacher = Teacher(**teacher_data.dict())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    return APIResponse(
        success=True,
        data=TeacherResponse.from_orm(teacher),
        message="Teacher created successfully",
    )


@router.get("/{teacher_id}", response_model=APIResponse[TeacherResponse])
async def get_teacher(
    teacher_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[TeacherResponse]:
    """
    Get a specific teacher by ID.

    Requires ADMIN or TEACHER permissions.
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")

    return APIResponse(
        success=True,
        data=TeacherResponse.from_orm(teacher),
        message="Teacher retrieved successfully",
    )


@router.put("/{teacher_id}", response_model=APIResponse[TeacherResponse])
async def update_teacher(
    teacher_id: UUID,
    teacher_data: TeacherUpdate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[TeacherResponse]:
    """
    Update a teacher's information.

    Requires ADMIN or TEACHER permissions.
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")

    # Note: Email updates should be handled through user management endpoints
    # Teachers don't directly update email - that's handled at the User level

    # Update teacher fields
    update_data = teacher_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(teacher, field, value)

    db.commit()
    db.refresh(teacher)

    return APIResponse(
        success=True,
        data=TeacherResponse.from_orm(teacher),
        message="Teacher updated successfully",
    )


@router.delete("/{teacher_id}", response_model=APIResponse[dict])
async def delete_teacher(
    teacher_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[dict]:
    """
    Delete a teacher (soft delete by setting is_active to False).

    Requires ADMIN or TEACHER permissions.
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")

    # Soft delete by setting is_available to False
    teacher.is_available = False
    db.commit()

    return APIResponse(
        success=True,
        data={"id": str(teacher_id), "deleted": True},
        message="Teacher deleted successfully",
    )


@router.post("/{teacher_id}/activate", response_model=APIResponse[TeacherResponse])
async def activate_teacher(
    teacher_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[TeacherResponse]:
    """
    Reactivate a deactivated teacher.

    Requires ADMIN or TEACHER permissions.
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")

    teacher.is_available = True
    db.commit()
    db.refresh(teacher)

    return APIResponse(
        success=True,
        data=TeacherResponse.from_orm(teacher),
        message="Teacher activated successfully",
    )


@router.put("/{teacher_id}/availability", response_model=APIResponse[TeacherResponse])
async def update_teacher_availability(
    teacher_id: UUID,
    availability_data: AvailabilitySlotUpdate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[TeacherResponse]:
    """
    Update a teacher's availability schedule.

    Requires ADMIN or TEACHER permissions.
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")

    # TODO: Implement availability slot management when TeacherAvailability model is integrated
    # For now, just return the teacher
    db.refresh(teacher)

    return APIResponse(
        success=True,
        data=TeacherResponse.from_orm(teacher),
        message="Teacher availability updated successfully",
    )


@router.get("/{teacher_id}/students", response_model=APIResponse[List[dict]])
async def get_teacher_students(
    teacher_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[List[dict]]:
    """
    Get all students assigned to a specific teacher.

    Requires ADMIN or TEACHER permissions.
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")

    # TODO: Implement student retrieval when student-teacher relationships are established
    # For now, return empty list
    students = []

    return APIResponse(
        success=True,
        data=students,
        message=f"Retrieved {len(students)} students for teacher",
    )


@router.get("/{teacher_id}/lessons", response_model=APIResponse[List[dict]])
async def get_teacher_lessons(
    teacher_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[List[dict]]:
    """
    Get all lessons for a specific teacher.

    Requires ADMIN or TEACHER permissions.
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")

    # TODO: Implement lesson retrieval when lesson endpoints are created
    # For now, return empty list
    lessons = []

    return APIResponse(
        success=True,
        data=lessons,
        message=f"Retrieved {len(lessons)} lessons for teacher",
    )
