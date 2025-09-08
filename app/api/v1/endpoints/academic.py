"""
Academic calendar management endpoints.
"""

from datetime import date
from typing import List, Optional

from auth.dependencies import get_current_user, require_admin
from database.session import db_session
from fastapi import APIRouter, Depends, Query
from models.academic import AcademicYear, MakeupWeek, Semester
from models.user import User
from pydantic import BaseModel
from schemas.common import APIResponse
from sqlalchemy.orm import Session

router = APIRouter()


class MakeupWeekResponse(BaseModel):
    """Makeup week information."""

    id: int
    name: str
    start_date: str
    end_date: str
    is_active: bool

    class Config:
        from_attributes = True


class AcademicYearResponse(BaseModel):
    """Academic year information."""

    id: int
    name: str
    start_date: str
    end_date: str
    is_current: bool
    created_at: str

    class Config:
        from_attributes = True


class SemesterResponse(BaseModel):
    """Semester information."""

    id: int
    academic_year_id: int
    name: str
    start_date: str
    end_date: str
    is_current: bool
    makeup_weeks: List[MakeupWeekResponse] = []
    created_at: str

    class Config:
        from_attributes = True


class AcademicYearCreate(BaseModel):
    """Schema for creating academic years."""

    name: str
    start_date: date
    end_date: date
    is_current: bool = False


class SemesterCreate(BaseModel):
    """Schema for creating semesters."""

    academic_year_id: int
    name: str
    start_date: date
    end_date: date
    is_current: bool = False


@router.get("/years", response_model=APIResponse[List[AcademicYearResponse]])
async def get_academic_years(
    db: Session = Depends(db_session), current_user: User = Depends(get_current_user)
):
    """
    List academic years.

    Access: ADMIN (all), TEACHER (read-only), PARENT (read-only)
    """
    try:
        academic_years = (
            db.query(AcademicYear).order_by(AcademicYear.start_date.desc()).all()
        )

        # Convert to response format
        years_data = []
        for year in academic_years:
            year_data = AcademicYearResponse(
                id=year.id,
                name=year.name,
                start_date=str(year.start_date),
                end_date=str(year.end_date),
                is_current=year.is_current,
                created_at=str(year.created_at),
            )
            years_data.append(year_data)

        return APIResponse(
            success=True,
            data=years_data,
            message="Academic years retrieved successfully",
        )

    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to retrieve academic years: {str(e)}",
        )


@router.post("/years", response_model=APIResponse[AcademicYearResponse])
async def create_academic_year(
    year_data: AcademicYearCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
):
    """
    Create a new academic year.

    Access: ADMIN only
    """
    try:
        # Check if there's already a current academic year and we're setting this as current
        if year_data.is_current:
            # Set all other academic years to not current
            db.query(AcademicYear).update({"is_current": False})

        # Create new academic year
        academic_year = AcademicYear(
            name=year_data.name,
            start_date=year_data.start_date,
            end_date=year_data.end_date,
            is_current=year_data.is_current,
        )

        db.add(academic_year)
        db.commit()
        db.refresh(academic_year)

        # Convert to response format
        year_response = AcademicYearResponse(
            id=academic_year.id,
            name=academic_year.name,
            start_date=str(academic_year.start_date),
            end_date=str(academic_year.end_date),
            is_current=academic_year.is_current,
            created_at=str(academic_year.created_at),
        )

        return APIResponse(
            success=True,
            data=year_response,
            message="Academic year created successfully",
        )

    except Exception as e:
        db.rollback()
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to create academic year: {str(e)}",
        )


@router.get("/semesters", response_model=APIResponse[List[SemesterResponse]])
async def get_semesters(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    academic_year_id: Optional[int] = Query(
        None, description="Filter by academic year"
    ),
    is_current: Optional[bool] = Query(None, description="Filter by current semester"),
):
    """
    List semesters.

    Access: ADMIN (all), TEACHER (read-only), PARENT (read-only)
    """
    try:
        query = db.query(Semester)

        if academic_year_id:
            query = query.filter(Semester.academic_year_id == academic_year_id)

        if is_current is not None:
            query = query.filter(Semester.is_current == is_current)

        semesters = query.order_by(Semester.start_date.desc()).all()

        # Convert to response format
        semesters_data = []
        for semester in semesters:
            # Get makeup weeks for this semester
            makeup_weeks = []
            for week in semester.makeup_weeks:
                makeup_week = MakeupWeekResponse(
                    id=week.id,
                    name=week.name,
                    start_date=str(week.start_date),
                    end_date=str(week.end_date),
                    is_active=week.is_active,
                )
                makeup_weeks.append(makeup_week)

            semester_data = SemesterResponse(
                id=semester.id,
                academic_year_id=semester.academic_year_id,
                name=semester.name,
                start_date=str(semester.start_date),
                end_date=str(semester.end_date),
                is_current=semester.is_current,
                makeup_weeks=makeup_weeks,
                created_at=str(semester.created_at),
            )
            semesters_data.append(semester_data)

        return APIResponse(
            success=True,
            data=semesters_data,
            message="Semesters retrieved successfully",
        )

    except Exception as e:
        return APIResponse(
            success=False, data=None, message=f"Failed to retrieve semesters: {str(e)}"
        )


@router.post("/semesters", response_model=APIResponse[SemesterResponse])
async def create_semester(
    semester_data: SemesterCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
):
    """
    Create a new semester.

    Access: ADMIN only
    """
    try:
        # Verify the academic year exists
        academic_year = (
            db.query(AcademicYear)
            .filter(AcademicYear.id == semester_data.academic_year_id)
            .first()
        )

        if not academic_year:
            return APIResponse(
                success=False,
                data=None,
                message="Academic year not found",
            )

        # Check if there's already a current semester and we're setting this as current
        if semester_data.is_current:
            # Set all other semesters to not current
            db.query(Semester).update({"is_current": False})

        # Create new semester
        semester = Semester(
            academic_year_id=semester_data.academic_year_id,
            name=semester_data.name,
            start_date=semester_data.start_date,
            end_date=semester_data.end_date,
            is_current=semester_data.is_current,
        )

        db.add(semester)
        db.commit()
        db.refresh(semester)

        # Convert to response format
        semester_response = SemesterResponse(
            id=semester.id,
            academic_year_id=semester.academic_year_id,
            name=semester.name,
            start_date=str(semester.start_date),
            end_date=str(semester.end_date),
            is_current=semester.is_current,
            makeup_weeks=[],  # New semester won't have makeup weeks initially
            created_at=str(semester.created_at),
        )

        return APIResponse(
            success=True,
            data=semester_response,
            message="Semester created successfully",
        )

    except Exception as e:
        db.rollback()
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to create semester: {str(e)}",
        )
