"""
Cedar Heights Music Academy - Database Models

This module contains all SQLAlchemy models for the music school management system.
Models are organized by domain for better maintainability.
"""

from .academic import AcademicYear, MakeupWeek, SchoolHours, Semester
from .base import Base
from .communication import EmailTracking, Message, Notification
from .lesson import Lesson, MakeupLessonTracking, Timeslot
from .payment import BillingRecord, Payment, Subscription
from .student import Student
from .system import AuditLog, PricingConfig, SystemSetting
from .teacher import Teacher, TeacherAvailability
from .user import User

__all__ = [
    "Base",
    "User",
    "AcademicYear",
    "Semester",
    "MakeupWeek",
    "SchoolHours",
    "Teacher",
    "TeacherAvailability",
    "Student",
    "Timeslot",
    "Lesson",
    "MakeupLessonTracking",
    "Payment",
    "Subscription",
    "BillingRecord",
    "Message",
    "EmailTracking",
    "Notification",
    "SystemSetting",
    "PricingConfig",
    "AuditLog",
]
