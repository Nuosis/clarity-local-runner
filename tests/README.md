# Cedar Heights Music Academy - API Test Suite

A quick and dirty API testing framework for the Cedar Heights Music Academy backend API.

## Overview

This test suite provides automated testing for the Cedar Heights Music Academy API endpoints, organized from most basic to most complex:

1. **Health Endpoints** - Basic server health checks
2. **Public Endpoints** - No authentication required
3. **Authentication Endpoints** - Login, token management
4. **Student Endpoints** - Student management (requires authentication)
5. **Teacher Endpoints** - Teacher management (requires authentication)
6. **Protected Endpoints** - Additional endpoints requiring authentication (lessons, payments)

## Quick Start

### Prerequisites

- Python 3.7+
- `requests` library (`pip install requests`)
- Cedar Heights API server running (default: http://localhost:8080)

### Running Tests

```bash
# Run all tests in order
cd tests
python run_api_tests.py

# Run individual test files
python test_01_health.py
python test_02_public.py
```

### Server Setup

Make sure the API server is running:

```bash
cd docker
docker-compose up api
```

## Test Structure

### Framework Components

- **`api_test_framework.py`** - Core testing framework with authentication support
- **`run_api_tests.py`** - Main test runner that executes tests in order
- **`test_01_health.py`** - Health endpoint tests (most basic)
- **`test_02_public.py`** - Public endpoint tests (no auth required)
- **`test_03_auth.py`** - Authentication endpoint tests
- **`test_04_students.py`** - Student management endpoint tests (requires auth)
- **`test_05_teachers.py`** - Teacher management endpoint tests (requires auth)

### Request Examples

The `requests/` directory contains example JSON payloads for different endpoints:

```
requests/
├── auth/
│   └── login.json
├── students/
│   ├── create_student.json
│   └── update_student.json
├── teachers/
│   ├── create_teacher.json
│   ├── update_teacher.json
│   └── update_availability.json
└── README.md
```

## Test Categories

### 1. Health Tests (`test_01_health.py`)

Tests basic server functionality:
- Basic health check (`/health`)
- Detailed health check (`/health/detailed`)
- Readiness probe (`/health/ready`)
- Liveness probe (`/health/live`)
- Root endpoint (`/`)
- Auth service health (`/auth/health`)

### 2. Public Tests (`test_02_public.py`)

Tests public endpoints that don't require authentication:
- Get public teachers (`/api/v1/public/teachers`)
- Get public timeslots (`/api/v1/public/timeslots`)
- Get public pricing (`/api/v1/public/pricing`)
- Filter and edge case testing

### 3. Authentication Tests (`test_03_auth.py`)

Tests authentication endpoints and flows:
- Auth health check (`/auth/health`)
- Login with valid/invalid credentials (`/auth/login`)
- Token verification (`/auth/verify-token`)
- User context retrieval (`/auth/me`)
- Token refresh (`/auth/refresh`)
- Logout (`/auth/logout`)

### 4. Student Tests (`test_04_students.py`)

Tests student management endpoints (requires authentication):
- List students with pagination and filtering (`/api/v1/students`)
- Create new students (`/api/v1/students`)
- Get student details (`/api/v1/students/{id}`)
- Update student information (`/api/v1/students/{id}`)
- Delete/deactivate students (`/api/v1/students/{id}`)
- Activate students (`/api/v1/students/{id}/activate`)
- Get student lessons (`/api/v1/students/{id}/lessons`)
- Validation and edge case testing

### 5. Teacher Tests (`test_05_teachers.py`)

Tests teacher management endpoints (requires authentication):
- List teachers with pagination and filtering (`/api/v1/teachers`)
- Create new teachers (`/api/v1/teachers`)
- Get teacher details (`/api/v1/teachers/{id}`)
- Update teacher information (`/api/v1/teachers/{id}`)
- Delete/deactivate teachers (`/api/v1/teachers/{id}`)
- Activate teachers (`/api/v1/teachers/{id}/activate`)
- Update teacher availability (`/api/v1/teachers/{id}/availability`)
- Get teacher students (`/api/v1/teachers/{id}/students`)
- Get teacher lessons (`/api/v1/teachers/{id}/lessons`)
- Validation and edge case testing

## Features

### Authentication Support

The framework automatically handles JWT authentication:

```python
framework = APITestFramework()
framework.authenticate("admin@cedarheights.com", "admin123")
# Subsequent requests will include the JWT token
```

### Response Validation

Built-in validators for common response patterns:

```python
framework.run_test(
    test_name="Get Teachers",
    method="GET",
    endpoint="/api/v1/teachers",
    validate_response=validate_list_response
)
```

### Comprehensive Reporting

Detailed test results with timing and error information:

```
📊 TEST SUMMARY
============================================================
Total Tests: 8
✅ Passed: 7
❌ Failed: 1
⏱️  Average Response Time: 45.2ms
Success Rate: 87.5%
```

## Configuration

### Base URL

Default API base URL is `http://localhost:8080`. To change:

```python
framework = APITestFramework(base_url="https://api.cedarheights.com")
```

### Timeouts

Default request timeout is 30 seconds. Modify in `api_test_framework.py`:

```python
response = getattr(self.session, method.lower())(url, timeout=30, **kwargs)
```

## Adding New Tests

### 1. Create Test File

Follow the naming convention: `test_XX_description.py`

```python
#!/usr/bin/env python3
"""
Description of test suite
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework, validate_api_response

def test_my_endpoints():
    framework = APITestFramework()
    
    # Authenticate if needed
    if not framework.authenticate("user@example.com", "password"):
        print("❌ Authentication failed")
        return framework
    
    # Run tests
    framework.run_test(
        test_name="My Test",
        method="GET",
        endpoint="/api/v1/my-endpoint",
        expected_status=200,
        validate_response=validate_api_response
    )
    
    return framework

if __name__ == "__main__":
    framework = test_my_endpoints()
    framework.print_summary()
    
    failed_tests = sum(1 for r in framework.results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)
```

### 2. Add to Test Runner

Update `run_api_tests.py` to include your new test file:

```python
test_files = [
    "test_01_health.py",
    "test_02_public.py",
    "test_03_my_new_tests.py",  # Add here
]
```

### 3. Create Request Examples

Add JSON examples to the `requests/` directory for complex payloads.

## Validation Functions

### Built-in Validators

- `validate_api_response(response_data)` - Standard API response format
- `validate_health_response(response_data)` - Health check responses
- `validate_list_response(response_data)` - Paginated list responses

### Custom Validators

Create custom validation functions:

```python
def validate_student_response(response_data):
    if not validate_api_response(response_data):
        return False
    
    data = response_data.get('data', {})
    required_fields = ['id', 'first_name', 'last_name', 'instrument']
    
    for field in required_fields:
        if field not in data:
            return False
    
    return True
```

## Troubleshooting

### Common Issues

1. **Server not running**
   ```
   ❌ Server health check failed: Connection refused
   ```
   Solution: Start the server with `cd docker && docker-compose up api`

2. **Authentication failed**
   ```
   ❌ Authentication failed: Invalid email or password
   ```
   Solution: Check credentials or ensure test users exist in the database

3. **Import errors**
   ```
   ModuleNotFoundError: No module named 'requests'
   ```
   Solution: Install required dependencies with `pip install requests`

### Debug Mode

For detailed request/response information, modify the framework to include debug output:

```python
# In api_test_framework.py, add debug prints
print(f"Request: {method.upper()} {url}")
print(f"Data: {data}")
print(f"Response: {response.status_code} - {response.text}")
```

## Extending the Framework

### Adding New HTTP Methods

The framework supports GET, POST, PUT, DELETE. To add others:

```python
# In make_request method
return getattr(self.session, method.lower())(url, **kwargs)
```

### Custom Headers

Add custom headers for specific tests:

```python
framework.session.headers.update({'X-Custom-Header': 'value'})
```

### Request Interceptors

Add request/response interceptors for logging or modification:

```python
# Before making request
print(f"Making request to {url}")

# After receiving response
print(f"Received {response.status_code} in {response_time_ms}ms")
```

## Contributing

When adding new tests:

1. Follow the existing naming conventions
2. Include comprehensive validation
3. Add appropriate error handling
4. Update this README with new test descriptions
5. Test your changes with the full test suite

## License

This test suite is part of the Cedar Heights Music Academy project.