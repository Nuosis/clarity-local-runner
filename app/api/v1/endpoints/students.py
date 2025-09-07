"""
Student management endpoints for Cedar Heights Music Academy API.
"""

from typing import List, Optional
from uuid import UUID

from auth.dependencies import get_current_user, require_admin_or_teacher
from auth.models import UserContext
from core.exceptions import NotFoundError, ValidationError
from database.session import db_session
from fastapi import APIRouter, Depends, Query, status
from models.student import Student
from schemas.common import APIResponse, PaginationMetadata
from schemas.student_schemas import (
    Instrument,
    SkillLevel,
    StudentCreate,
    StudentListItem,
    StudentListResponse,
    StudentResponse,
    StudentUpdate,
)
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=APIResponse[StudentListResponse])
async def list_students(
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
) -> APIResponse[StudentListResponse]:
    """
    List students with filtering and pagination.

    Requires ADMIN or TEACHER permissions.
    """
    query = db.query(Student)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Student.first_name.ilike(search_term)
            | Student.last_name.ilike(search_term)
            | Student.email.ilike(search_term)
        )

    if instrument:
        query = query.filter(Student.instrument == instrument)

    if is_active is not None:
        query = query.filter(Student.is_active == is_active)

    # Get total count
    total = query.count()

    # Apply pagination
    skip = (page - 1) * limit
    students = query.offset(skip).limit(limit).all()

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

    student_list_items = [StudentListItem.from_orm(student) for student in students]

    return APIResponse(
        success=True,
        data=StudentListResponse(students=student_list_items, pagination=pagination),
        message=f"Retrieved {len(students)} students",
    )


@router.post(
    "/",
    response_model=APIResponse[StudentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_student(
    student_data: StudentCreate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[StudentResponse]:
    """
    Create a new student.

    Requires ADMIN or TEACHER permissions.
    """
    # Check if email already exists
    if student_data.email:
        existing_student = (
            db.query(Student).filter(Student.email == student_data.email).first()
        )
        if existing_student:
            raise ValidationError("Student with this email already exists")

    # Create new student
    student = Student(**student_data.dict())
    db.add(student)
    db.commit()
    db.refresh(student)

    return APIResponse(
        success=True,
        data=StudentResponse.from_orm(student),
        message="Student created successfully",
    )


@router.get("/{student_id}", response_model=APIResponse[StudentResponse])
async def get_student(
    student_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[StudentResponse]:
    """
    Get a specific student by ID.

    Requires ADMIN or TEACHER permissions.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    return APIResponse(
        success=True,
        data=StudentResponse.from_orm(student),
        message="Student retrieved successfully",
    )


@router.put("/{student_id}", response_model=APIResponse[StudentResponse])
async def update_student(
    student_id: UUID,
    student_data: StudentUpdate,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[StudentResponse]:
    """
    Update a student's information.

    Requires ADMIN or TEACHER permissions.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    # Check if email is being changed and if it conflicts
    if student_data.email and student_data.email != student.email:
        existing_student = (
            db.query(Student)
            .filter(Student.email == student_data.email, Student.id != student_id)
            .first()
        )
        if existing_student:
            raise ValidationError("Student with this email already exists")

    # Update student fields
    update_data = student_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)

    return APIResponse(
        success=True,
        data=StudentResponse.from_orm(student),
        message="Student updated successfully",
    )


@router.delete("/{student_id}", response_model=APIResponse[dict])
async def delete_student(
    student_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[dict]:
    """
    Delete a student (soft delete by setting is_active to False).

    Requires ADMIN or TEACHER permissions.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    # Soft delete by setting is_active to False
    student.is_active = False
    db.commit()

    return APIResponse(
        success=True,
        data={"id": str(student_id), "deleted": True},
        message="Student deleted successfully",
    )


@router.post("/{student_id}/activate", response_model=APIResponse[StudentResponse])
async def activate_student(
    student_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[StudentResponse]:
    """
    Reactivate a deactivated student.

    Requires ADMIN or TEACHER permissions.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    student.is_active = True
    db.commit()
    db.refresh(student)

    return APIResponse(
        success=True,
        data=StudentResponse.from_orm(student),
        message="Student activated successfully",
    )


@router.get("/{student_id}/lessons", response_model=APIResponse[List[dict]])
async def get_student_lessons(
    student_id: UUID,
    db: Session = Depends(db_session),
    current_user: UserContext = Depends(get_current_user),
    _: UserContext = Depends(require_admin_or_teacher()),
) -> APIResponse[List[dict]]:
    """
    Get all lessons for a specific student.

    Requires ADMIN or TEACHER permissions.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")

    # TODO: Implement lesson retrieval when lesson endpoints are created
    # For now, return empty list
    lessons = []

    return APIResponse(
        success=True,
        data=lessons,
        message=f"Retrieved {len(lessons)} lessons for student",
    )
