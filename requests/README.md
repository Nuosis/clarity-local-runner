# API Test Requests

This directory contains example JSON payloads for testing the Cedar Heights Music Academy API endpoints.

## Structure

- `auth/` - Authentication related requests
- `public/` - Public endpoints (no auth required)
- `health/` - Health check endpoints
- `students/` - Student management endpoints
- `teachers/` - Teacher management endpoints
- `lessons/` - Lesson management endpoints
- `payments/` - Payment endpoints

## Usage

These JSON files are used by the API test suite to simulate real API calls and verify responses.

## Authentication

Most endpoints require JWT authentication. Use the auth endpoints to obtain tokens for testing protected endpoints.