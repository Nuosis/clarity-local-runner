"""
Public API endpoints for frontend integration.
These endpoints do not require authentication and provide public information.
"""

from datetime import datetime
from typing import List, Optional

from database.session import db_session
from fastapi import APIRouter, Depends, Query
from models.academic import AcademicYear, Semester
from models.system import PricingConfig, SystemSetting
from models.teacher import Teacher, TeacherAvailability
from pydantic import BaseModel
from schemas.common import APIResponse
from schemas.student_schemas import Instrument
from schemas.teacher_schemas import TeacherProfile
from sqlalchemy.orm import Session

router = APIRouter()


class PublicTimeslot(BaseModel):
    """Public timeslot information for enrollment."""

    id: int
    teacher_id: int
    teacher_name: str
    day_of_week: int
    day_name: str
    start_time: str
    end_time: str
    duration_minutes: int
    is_available: bool
    instrument: Optional[str] = None


class PublicPricing(BaseModel):
    """Public pricing information."""

    instrument: str
    rate_per_lesson: float
    currency: str
    billing_frequency: str
    lesson_duration: int
    effective_date: str


class PublicSemester(BaseModel):
    """Current semester information."""

    id: int
    name: str
    start_date: str
    end_date: str


class PublicPricingResponse(BaseModel):
    """Response model for public pricing."""

    pricing: List[PublicPricing]
    current_semester: Optional[PublicSemester] = None


@router.get("/teachers", response_model=APIResponse[List[TeacherProfile]])
async def get_public_teachers(
    db: Session = Depends(db_session),
    instrument: Optional[str] = Query(None, description="Filter by instrument"),
):
    """
    Get teacher information for public website.

    Returns basic teacher information without sensitive data.
    """
    try:
        query = (
            db.query(Teacher).join(Teacher.user).filter(Teacher.is_available == True)
        )

        if instrument:
            # Filter teachers who teach the specified instrument
            query = query.filter(Teacher.instruments.contains([instrument]))

        teachers = query.all()

        # Convert to public response format
        public_teachers = []
        for teacher in teachers:
            # Convert string instruments to Instrument enum values
            instruments = []
            if teacher.instruments:
                for instrument_str in teacher.instruments:
                    try:
                        instruments.append(Instrument(instrument_str))
                    except ValueError:
                        # Skip invalid instrument values
                        continue

            public_teacher = TeacherProfile(
                id=teacher.id,
                first_name=teacher.user.first_name,
                last_name=teacher.user.last_name,
                instruments=instruments,
                bio=teacher.bio,
                photo_url=teacher.photo_url,
                is_available=teacher.is_available,
            )
            public_teachers.append(public_teacher)

        return APIResponse(
            success=True,
            data=public_teachers,
            message="Public teachers retrieved successfully",
        )

    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to retrieve public teachers: {str(e)}",
        )


@router.get("/timeslots", response_model=APIResponse[List[PublicTimeslot]])
async def get_public_timeslots(
    db: Session = Depends(db_session),
    teacher_id: Optional[int] = Query(None, description="Filter by teacher"),
    instrument: Optional[str] = Query(None, description="Filter by instrument"),
    weekday: Optional[int] = Query(None, description="Filter by day of week (0-6)"),
    active: Optional[bool] = Query(True, description="Filter by active status"),
):
    """
    Get available timeslots for enrollment.

    Returns available timeslots that can be used for lesson scheduling.
    """
    try:
        # Query available timeslots with teacher information
        query = db.query(TeacherAvailability).join(Teacher).join(Teacher.user)

        if active is not None:
            query = query.filter(TeacherAvailability.is_active == active)

        if teacher_id:
            query = query.filter(TeacherAvailability.teacher_id == teacher_id)

        if weekday is not None:
            query = query.filter(TeacherAvailability.day_of_week == weekday)

        if instrument:
            query = query.filter(Teacher.instruments.contains([instrument]))

        # Only show available teachers
        query = query.filter(Teacher.is_available == True)

        timeslots = query.all()

        # Convert to public response format
        public_timeslots = []
        day_names = [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ]

        for slot in timeslots:
            # Calculate duration in minutes
            start_time = slot.start_time
            end_time = slot.end_time
            duration_minutes = int(
                (
                    datetime.combine(datetime.today(), end_time)
                    - datetime.combine(datetime.today(), start_time)
                ).total_seconds()
                / 60
            )

            public_slot = PublicTimeslot(
                id=slot.id,
                teacher_id=slot.teacher_id,
                teacher_name=f"{slot.teacher.user.first_name} {slot.teacher.user.last_name}",
                day_of_week=slot.day_of_week,
                day_name=day_names[slot.day_of_week],
                start_time=str(slot.start_time),
                end_time=str(slot.end_time),
                duration_minutes=duration_minutes,
                is_available=True,
                instrument=slot.teacher.instruments[0]
                if slot.teacher.instruments
                else None,
            )
            public_timeslots.append(public_slot)

        return APIResponse(
            success=True,
            data=public_timeslots,
            message="Public timeslots retrieved successfully",
        )

    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to retrieve public timeslots: {str(e)}",
        )


@router.get("/pricing", response_model=APIResponse[PublicPricingResponse])
async def get_public_pricing(db: Session = Depends(db_session)):
    """
    Get current pricing information.

    Returns active pricing configuration for public display.
    """
    try:
        # Get active pricing configurations
        pricing_configs = (
            db.query(PricingConfig).filter(PricingConfig.is_active == True).all()
        )

        # Get current semester
        current_semester = (
            db.query(Semester).filter(Semester.is_current == True).first()
        )

        # Convert to public response format
        public_pricing = []
        for config in pricing_configs:
            pricing = PublicPricing(
                instrument=config.instrument,
                rate_per_lesson=float(config.rate_per_lesson),
                currency=config.currency,
                billing_frequency=config.billing_frequency,
                lesson_duration=config.lesson_duration,
                effective_date=str(config.effective_date),
            )
            public_pricing.append(pricing)

        # Convert current semester if exists
        semester_info = None
        if current_semester:
            semester_info = PublicSemester(
                id=current_semester.id,
                name=current_semester.name,
                start_date=str(current_semester.start_date),
                end_date=str(current_semester.end_date),
            )

        response_data = PublicPricingResponse(
            pricing=public_pricing, current_semester=semester_info
        )

        return APIResponse(
            success=True,
            data=response_data,
            message="Public pricing retrieved successfully",
        )

    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to retrieve public pricing: {str(e)}",
        )
