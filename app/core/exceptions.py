"""
Custom exceptions for Cedar Heights Music Academy API.
"""

from typing import Any, Dict, List, Optional


class CedarHeightsException(Exception):
    """Base exception for Cedar Heights Music Academy."""

    def __init__(
        self,
        message: str,
        error_code: str = "GENERAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(CedarHeightsException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field_errors: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ):
        super().__init__(
            message=message, error_code="VALIDATION_ERROR", status_code=422, **kwargs
        )
        self.field_errors = field_errors or []


class AuthenticationError(CedarHeightsException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            **kwargs,
        )


class AuthorizationError(CedarHeightsException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(
            message=message, error_code="AUTHORIZATION_ERROR", status_code=403, **kwargs
        )


class NotFoundError(CedarHeightsException):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(
            message=message, error_code="NOT_FOUND", status_code=404, **kwargs
        )


class ConflictError(CedarHeightsException):
    """Raised when there's a resource conflict."""

    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(
            message=message, error_code="CONFLICT", status_code=409, **kwargs
        )


class BusinessRuleError(CedarHeightsException):
    """Raised when business rules are violated."""

    def __init__(self, message: str = "Business rule violation", **kwargs):
        super().__init__(
            message=message, error_code="BUSINESS_RULE_ERROR", status_code=422, **kwargs
        )


class ExternalServiceError(CedarHeightsException):
    """Raised when external service calls fail."""

    def __init__(
        self,
        message: str = "External service error",
        service: str = "unknown",
        **kwargs,
    ):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            **kwargs,
        )
        self.service = service


class RateLimitError(CedarHeightsException):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(
            message=message, error_code="RATE_LIMIT_EXCEEDED", status_code=429, **kwargs
        )


class DatabaseError(CedarHeightsException):
    """Raised when database operations fail."""

    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(
            message=message, error_code="DATABASE_ERROR", status_code=500, **kwargs
        )


class WorkflowError(CedarHeightsException):
    """Raised when workflow execution fails."""

    def __init__(
        self,
        message: str = "Workflow execution failed",
        workflow_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message, error_code="WORKFLOW_ERROR", status_code=500, **kwargs
        )
        self.workflow_id = workflow_id


class PaymentError(CedarHeightsException):
    """Raised when payment processing fails."""

    def __init__(
        self,
        message: str = "Payment processing failed",
        payment_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message, error_code="PAYMENT_ERROR", status_code=402, **kwargs
        )
        self.payment_id = payment_id


class SchedulingError(CedarHeightsException):
    """Raised when lesson scheduling fails."""

    def __init__(self, message: str = "Scheduling conflict", **kwargs):
        super().__init__(
            message=message, error_code="SCHEDULING_ERROR", status_code=409, **kwargs
        )
