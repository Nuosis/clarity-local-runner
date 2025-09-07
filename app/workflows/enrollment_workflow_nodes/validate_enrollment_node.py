"""
Validate enrollment data and business rules node.
"""

import logging
from datetime import date
from typing import Any, Dict

from core.nodes.base import Node
from core.task import TaskContext
from schemas.enrollment_schema import EnrollmentEventSchema


class ValidateEnrollmentNode(Node):
    """Validate enrollment data and business rules."""

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Validate enrollment data and business rules.

        Validates:
        - Student age (5+ years)
        - Parent information completeness
        - Instrument availability
        - Payment information
        - Data format and constraints

        Args:
            task_context: The task context containing enrollment event data

        Returns:
            Updated task context with validation results
        """
        try:
            logging.info(f"Starting {self.node_name} validation")

            # Get enrollment event data
            enrollment_event: EnrollmentEventSchema = task_context.event

            # Initialize validation results
            validation_results = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "validated_data": {},
            }

            # Validate student age (already done in schema, but double-check)
            student_age = self._calculate_age(enrollment_event.student_date_of_birth)
            if student_age < 5:
                validation_results["errors"].append(
                    "Student must be at least 5 years old"
                )
                validation_results["is_valid"] = False
            else:
                validation_results["validated_data"]["student_age"] = student_age
                logging.info(f"Student age validation passed: {student_age} years old")

            # Validate parent information completeness
            parent_validation = self._validate_parent_info(enrollment_event)
            if not parent_validation["is_valid"]:
                validation_results["errors"].extend(parent_validation["errors"])
                validation_results["is_valid"] = False
            else:
                validation_results["validated_data"]["parent_info"] = parent_validation[
                    "data"
                ]
                logging.info("Parent information validation passed")

            # Validate instrument availability
            instrument_validation = self._validate_instrument(
                enrollment_event.instrument
            )
            if not instrument_validation["is_valid"]:
                validation_results["errors"].extend(instrument_validation["errors"])
                validation_results["is_valid"] = False
            else:
                validation_results["validated_data"]["instrument"] = (
                    instrument_validation["data"]
                )
                logging.info(
                    f"Instrument validation passed: {enrollment_event.instrument}"
                )

            # Validate lesson rate
            rate_validation = self._validate_lesson_rate(enrollment_event.lesson_rate)
            if not rate_validation["is_valid"]:
                validation_results["errors"].extend(rate_validation["errors"])
                validation_results["is_valid"] = False
            else:
                validation_results["validated_data"]["lesson_rate"] = rate_validation[
                    "data"
                ]
                logging.info(
                    f"Lesson rate validation passed: ${enrollment_event.lesson_rate}"
                )

            # Validate payment information if provided
            if enrollment_event.payment_method_id:
                payment_validation = self._validate_payment_info(enrollment_event)
                if not payment_validation["is_valid"]:
                    validation_results["warnings"].extend(
                        payment_validation["warnings"]
                    )
                else:
                    validation_results["validated_data"]["payment_info"] = (
                        payment_validation["data"]
                    )
                    logging.info("Payment information validation passed")

            # Store validation results in task context
            task_context.update_node(self.node_name, **validation_results)

            # Log validation summary
            if validation_results["is_valid"]:
                logging.info(
                    f"{self.node_name} completed successfully - all validations passed"
                )
            else:
                logging.error(
                    f"{self.node_name} failed - validation errors: {validation_results['errors']}"
                )
                # Stop workflow if validation fails
                task_context.stop_workflow()

            return task_context

        except Exception as e:
            logging.error(f"Error in {self.node_name}: {str(e)}")
            task_context.update_node(
                self.node_name,
                is_valid=False,
                error=str(e),
                errors=[f"Validation failed: {str(e)}"],
            )
            task_context.stop_workflow()
            return task_context

    def _calculate_age(self, birth_date: date) -> int:
        """Calculate age from birth date."""
        today = date.today()
        return (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )

    def _validate_parent_info(
        self, enrollment_event: EnrollmentEventSchema
    ) -> Dict[str, Any]:
        """Validate parent information completeness."""
        errors = []

        # Check required parent fields
        if (
            not enrollment_event.parent_first_name
            or len(enrollment_event.parent_first_name.strip()) < 2
        ):
            errors.append("Parent first name must be at least 2 characters")

        if (
            not enrollment_event.parent_last_name
            or len(enrollment_event.parent_last_name.strip()) < 2
        ):
            errors.append("Parent last name must be at least 2 characters")

        if (
            not enrollment_event.parent_email
            or "@" not in enrollment_event.parent_email
        ):
            errors.append("Valid parent email is required")

        # Validate phone if provided
        if enrollment_event.parent_phone:
            # Basic phone validation - remove non-digits and check length
            phone_digits = "".join(filter(str.isdigit, enrollment_event.parent_phone))
            if len(phone_digits) < 10:
                errors.append("Parent phone number must contain at least 10 digits")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "data": {
                "parent_first_name": enrollment_event.parent_first_name.strip(),
                "parent_last_name": enrollment_event.parent_last_name.strip(),
                "parent_email": enrollment_event.parent_email.lower().strip(),
                "parent_phone": enrollment_event.parent_phone,
            },
        }

    def _validate_instrument(self, instrument: str) -> Dict[str, Any]:
        """Validate instrument availability."""
        allowed_instruments = ["piano", "guitar", "bass"]

        if instrument.lower() not in allowed_instruments:
            return {
                "is_valid": False,
                "errors": [
                    f"Instrument '{instrument}' is not available. Available instruments: {', '.join(allowed_instruments)}"
                ],
                "data": None,
            }

        return {"is_valid": True, "errors": [], "data": instrument.lower()}

    def _validate_lesson_rate(self, lesson_rate) -> Dict[str, Any]:
        """Validate lesson rate is within acceptable range."""
        min_rate = 30
        max_rate = 200

        if lesson_rate < min_rate or lesson_rate > max_rate:
            return {
                "is_valid": False,
                "errors": [f"Lesson rate must be between ${min_rate} and ${max_rate}"],
                "data": None,
            }

        return {"is_valid": True, "errors": [], "data": float(lesson_rate)}

    def _validate_payment_info(
        self, enrollment_event: EnrollmentEventSchema
    ) -> Dict[str, Any]:
        """Validate payment information if provided."""
        warnings = []

        # Basic validation for payment method ID format
        if enrollment_event.payment_method_id:
            if not enrollment_event.payment_method_id.startswith("pm_"):
                warnings.append("Payment method ID format may be invalid")

        # Validate billing address if provided
        billing_address_valid = True
        if enrollment_event.billing_address:
            required_fields = ["line1", "city", "postal_code", "country"]
            for field in required_fields:
                if (
                    field not in enrollment_event.billing_address
                    or not enrollment_event.billing_address[field]
                ):
                    warnings.append(f"Billing address missing required field: {field}")
                    billing_address_valid = False

        return {
            "is_valid": True,  # Payment info is optional, so warnings don't fail validation
            "warnings": warnings,
            "data": {
                "payment_method_id": enrollment_event.payment_method_id,
                "billing_address": enrollment_event.billing_address,
                "billing_address_valid": billing_address_valid,
            },
        }
