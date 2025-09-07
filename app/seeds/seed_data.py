"""
Seed data creation for development environment.
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from database.session import SessionLocal
from models import *
from sqlalchemy.orm import Session


def create_seed_data():
    """Create comprehensive seed data for development."""
    db = SessionLocal()
    try:
        # Clear existing data first
        clear_all_data(db)

        # Create academic year and semester
        academic_year = AcademicYear(
            name="2024-2025",
            start_date=date(2024, 9, 1),
            end_date=date(2025, 8, 31),
            is_current=True,
        )
        db.add(academic_year)
        db.flush()

        fall_semester = Semester(
            academic_year_id=academic_year.id,
            name="Fall 2024",
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 20),
            is_current=True,
        )
        db.add(fall_semester)
        db.flush()

        # Create makeup week
        makeup_week = MakeupWeek(
            semester_id=fall_semester.id,
            name="Fall 2024 Makeup Week",
            start_date=date(2024, 12, 15),  # Sunday
            end_date=date(2024, 12, 21),  # Saturday
            is_active=True,
        )
        db.add(makeup_week)

        # Create school hours
        school_hours_data = [
            (1, time(9, 0), time(20, 0)),  # Monday
            (2, time(9, 0), time(20, 0)),  # Tuesday
            (3, time(9, 0), time(20, 0)),  # Wednesday
            (4, time(9, 0), time(20, 0)),  # Thursday
            (5, time(9, 0), time(20, 0)),  # Friday
            (6, time(9, 0), time(18, 0)),  # Saturday
        ]

        for day, start, end in school_hours_data:
            school_hour = SchoolHours(
                day_of_week=day, start_time=start, end_time=end, is_active=True
            )
            db.add(school_hour)

        # Create admin user
        admin_user = User(
            supabase_user_id=uuid4(),
            email="admin@cedarheights.academy",
            first_name="Admin",
            last_name="User",
            phone="902-555-0001",
            role="admin",
            is_active=True,
            user_metadata={"created_by": "seed_data"},
        )
        db.add(admin_user)
        db.flush()

        # Create teacher users and profiles
        teachers_data = [
            {
                "email": "sarah.piano@cedarheights.academy",
                "first_name": "Sarah",
                "last_name": "Johnson",
                "phone": "902-555-0101",
                "instruments": ["piano"],
                "hourly_rate": Decimal("75.00"),
                "bio": "Experienced piano instructor with 15 years of teaching experience.",
            },
            {
                "email": "mike.guitar@cedarheights.academy",
                "first_name": "Mike",
                "last_name": "Thompson",
                "phone": "902-555-0102",
                "instruments": ["guitar"],
                "hourly_rate": Decimal("70.00"),
                "bio": "Professional guitarist and music educator specializing in rock and classical styles.",
            },
            {
                "email": "emma.bass@cedarheights.academy",
                "first_name": "Emma",
                "last_name": "Wilson",
                "phone": "902-555-0103",
                "instruments": ["bass"],
                "hourly_rate": Decimal("80.00"),
                "bio": "Professional bass player with jazz and rock experience.",
            },
        ]

        teachers = []
        for teacher_data in teachers_data:
            # Create user
            teacher_user = User(
                supabase_user_id=uuid4(),
                email=teacher_data["email"],
                first_name=teacher_data["first_name"],
                last_name=teacher_data["last_name"],
                phone=teacher_data["phone"],
                role="teacher",
                is_active=True,
                user_metadata={"created_by": "seed_data"},
            )
            db.add(teacher_user)
            db.flush()

            # Create teacher profile
            teacher = Teacher(
                user_id=teacher_user.id,
                instruments=teacher_data["instruments"],
                hourly_rate=teacher_data["hourly_rate"],
                max_students=30,
                is_available=True,
                bio=teacher_data["bio"],
            )
            db.add(teacher)
            teachers.append(teacher)

        db.flush()

        # Create teacher availability
        for teacher in teachers:
            # Monday to Friday availability
            for day in range(1, 6):  # Monday to Friday
                for hour in range(15, 20):  # 3 PM to 7 PM
                    availability = TeacherAvailability(
                        teacher_id=teacher.id,
                        day_of_week=day,
                        start_time=time(hour, 0),
                        end_time=time(hour, 30),
                        is_recurring=True,
                        is_active=True,
                    )
                    db.add(availability)

        # Create parent users and students
        parents_students_data = [
            {
                "parent": {
                    "email": "john.smith@email.com",
                    "first_name": "John",
                    "last_name": "Smith",
                    "phone": "902-555-0201",
                },
                "students": [
                    {
                        "first_name": "Emma",
                        "last_name": "Smith",
                        "date_of_birth": date(2015, 3, 15),
                        "instrument": "piano",
                        "lesson_rate": Decimal("125.00"),
                    }
                ],
            },
            {
                "parent": {
                    "email": "mary.jones@email.com",
                    "first_name": "Mary",
                    "last_name": "Jones",
                    "phone": "902-555-0202",
                },
                "students": [
                    {
                        "first_name": "Alex",
                        "last_name": "Jones",
                        "date_of_birth": date(2012, 8, 22),
                        "instrument": "guitar",
                        "lesson_rate": Decimal("125.00"),
                    },
                    {
                        "first_name": "Sophie",
                        "last_name": "Jones",
                        "date_of_birth": date(2014, 11, 5),
                        "instrument": "bass",
                        "lesson_rate": Decimal("125.00"),
                    },
                ],
            },
        ]

        for family_data in parents_students_data:
            # Create parent user
            parent_user = User(
                supabase_user_id=uuid4(),
                email=family_data["parent"]["email"],
                first_name=family_data["parent"]["first_name"],
                last_name=family_data["parent"]["last_name"],
                phone=family_data["parent"]["phone"],
                role="parent",
                is_active=True,
                user_metadata={"created_by": "seed_data"},
            )
            db.add(parent_user)
            db.flush()

            # Create students
            for student_data in family_data["students"]:
                # Assign teacher based on instrument
                teacher = next(
                    (
                        t
                        for t in teachers
                        if student_data["instrument"] in t.instruments
                    ),
                    None,
                )

                student = Student(
                    first_name=student_data["first_name"],
                    last_name=student_data["last_name"],
                    date_of_birth=student_data["date_of_birth"],
                    parent_id=parent_user.id,
                    teacher_id=teacher.id if teacher else None,
                    instrument=student_data["instrument"],
                    skill_level="beginner",
                    lesson_rate=student_data["lesson_rate"],
                    enrollment_date=date.today(),
                    is_active=True,
                    notes="Enrolled through seed data",
                )
                db.add(student)

        # Create system settings
        system_settings_data = [
            (
                "school_name",
                "Cedar Heights Music Academy",
                "string",
                "Name of the music school",
                True,
                "general",
            ),
            (
                "default_lesson_duration",
                "30",
                "number",
                "Default lesson duration in minutes",
                True,
                "lessons",
            ),
            (
                "max_makeup_lessons_per_semester",
                "1",
                "number",
                "Maximum makeup lessons allowed per student per semester",
                False,
                "lessons",
            ),
            (
                "enrollment_auto_confirm",
                "false",
                "boolean",
                "Automatically confirm enrollments without manual review",
                False,
                "enrollment",
            ),
            (
                "payment_retry_attempts",
                "3",
                "number",
                "Number of automatic payment retry attempts",
                False,
                "payments",
            ),
            (
                "contact_email",
                "info@cedarheights.academy",
                "string",
                "Main contact email",
                True,
                "contact",
            ),
            (
                "contact_phone",
                "+1-902-555-0123",
                "string",
                "Main contact phone",
                True,
                "contact",
            ),
            (
                "timezone",
                "America/Halifax",
                "string",
                "School timezone",
                False,
                "general",
            ),
        ]

        for key, value, type_, desc, public, category in system_settings_data:
            setting = SystemSetting(
                setting_key=key,
                setting_value=value,
                setting_type=type_,
                description=desc,
                is_public=public,
                category=category,
            )
            db.add(setting)

        # Create pricing configuration
        pricing_data = [
            ("piano", "all", 30, Decimal("125.00")),
            ("guitar", "all", 30, Decimal("125.00")),
            ("bass", "all", 30, Decimal("125.00")),
        ]

        for instrument, skill, duration, rate in pricing_data:
            pricing = PricingConfig(
                instrument=instrument,
                skill_level=skill,
                lesson_duration=duration,
                rate_per_lesson=rate,
                currency="CAD",
                billing_frequency="monthly",
                is_active=True,
                effective_date=date.today(),
            )
            db.add(pricing)

        db.commit()
        print("✅ Seed data created successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating seed data: {e}")
        raise
    finally:
        db.close()


def clear_all_data(db: Optional[Session] = None):
    """Clear all data from the database."""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        # Delete in reverse dependency order
        db.query(AuditLog).delete()
        db.query(PricingConfig).delete()
        db.query(SystemSetting).delete()
        db.query(Notification).delete()
        db.query(EmailTracking).delete()
        db.query(Message).delete()
        db.query(BillingRecord).delete()
        db.query(Subscription).delete()
        db.query(Payment).delete()
        db.query(MakeupLessonTracking).delete()
        db.query(Lesson).delete()
        db.query(Timeslot).delete()
        db.query(Student).delete()
        db.query(TeacherAvailability).delete()
        db.query(Teacher).delete()
        db.query(User).delete()
        db.query(SchoolHours).delete()
        db.query(MakeupWeek).delete()
        db.query(Semester).delete()
        db.query(AcademicYear).delete()

        if should_close:
            db.commit()
            print("✅ All data cleared successfully!")

    except Exception as e:
        if should_close:
            db.rollback()
        print(f"❌ Error clearing data: {e}")
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    create_seed_data()
