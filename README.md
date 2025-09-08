# Cedar Heights Music Academy - Backend API System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat&logo=python)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat&logo=docker)](https://docker.com)
[![Supabase](https://img.shields.io/badge/Supabase-Backend-3ECF8E.svg?style=flat&logo=supabase)](https://supabase.com)
[![Stripe](https://img.shields.io/badge/Stripe-Payments-008CDD.svg?style=flat&logo=stripe)](https://stripe.com)

A comprehensive, workflow-driven backend system for music academy management, built with FastAPI and powered by the GenAI Launchpad workflow orchestration framework. This system automates complex business processes including student enrollment, lesson scheduling, payment processing, and communication workflows.

## 🎯 Project Overview

Cedar Heights Music Academy Backend is a production-ready API system designed for solo-operated music schools that need to scale efficiently. The system combines traditional REST APIs for quick operations with sophisticated workflow orchestration for complex business processes.

### Key Features

- **🔄 Workflow-Driven Architecture**: Complex business processes automated through DAG-based workflows
- **⚡ High Performance**: <200ms response times for quick operations, <2s for workflow completion
- **🔐 Enterprise Security**: JWT authentication, role-based access control, and comprehensive audit logging
- **💳 Payment Processing**: Full Stripe integration with subscription management and automated billing
- **📧 Communication Automation**: Automated email workflows for enrollment, scheduling, and payments
- **📊 Comprehensive Management**: Complete student, teacher, and lesson lifecycle management
- **🐳 Docker Ready**: Production-ready containerization with Docker Compose orchestration

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                           │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API Calls
┌─────────────────────▼───────────────────────────────────────┐
│                FastAPI Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Quick APIs    │  │  Workflow APIs  │  │  Public APIs │ │
│  │   (<200ms)      │  │   (<2s)         │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              GenAI Launchpad Framework                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Workflow Engine                          │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ Enrollment  │ │  Payment    │ │    Scheduling       │ │ │
│  │  │ Workflows   │ │ Workflows   │ │    Workflows        │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Data Layer                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │    Supabase     │  │     Redis       │  │   External   │ │
│  │   PostgreSQL    │  │    Caching      │  │   Services   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Core Business Workflows

### 1. Student Enrollment Workflow
Automated end-to-end student onboarding process:
- **Validation**: Student age, instrument availability, teacher capacity
- **Account Creation**: Supabase user accounts for student and parent
- **Payment Setup**: Stripe customer and subscription creation
- **Teacher Assignment**: AI-powered matching based on availability and preferences
- **Demo Scheduling**: Automatic first lesson scheduling
- **Welcome Communications**: Automated email notifications to all parties

### 2. Payment Processing Workflow
Comprehensive payment handling with error recovery:
- **Stripe Integration**: Payment intent creation and confirmation
- **Subscription Management**: Automated recurring billing
- **Failure Handling**: Intelligent retry logic and parent notifications
- **Accounting Updates**: Automatic financial record reconciliation
- **Receipt Generation**: Automated receipt delivery

### 3. Lesson Scheduling Workflow
Intelligent lesson scheduling with conflict resolution:
- **Availability Checking**: Real-time teacher and student availability
- **Conflict Detection**: Automatic scheduling conflict identification
- **Alternative Suggestions**: AI-powered alternative time recommendations
- **Confirmation Workflows**: Automated booking confirmations

## 🛠️ Technology Stack

### Core Framework
- **FastAPI 0.104.1**: Modern async web framework with automatic OpenAPI documentation
- **Python 3.11+**: Latest Python features with enhanced performance
- **Pydantic 2.5.0**: Type-safe data validation and serialization
- **SQLAlchemy 2.0.23**: Async ORM with advanced relationship handling
- **Alembic 1.13.0**: Database migration management

### Infrastructure & Services
- **Supabase**: Backend-as-a-Service with PostgreSQL and authentication
- **Stripe 7.8.0**: Payment processing and subscription management
- **Redis 5.0.1**: Caching and task queue management
- **Celery 5.3.4**: Background task processing
- **Docker**: Containerization with multi-service orchestration

### AI & Workflow
- **GenAI Launchpad**: Custom workflow orchestration framework
- **Multi-Provider AI**: OpenAI, Anthropic, Azure OpenAI support
- **Event-Driven Architecture**: Redis Streams for workflow coordination

## 📁 Project Structure

```
cedar-heights-BE/
├── app/                          # Main application code
│   ├── main.py                   # FastAPI application entry point
│   ├── core/                     # Core framework components
│   │   ├── workflow.py           # Workflow orchestration engine
│   │   ├── task.py               # TaskContext state management
│   │   ├── schema.py             # Pydantic schema definitions
│   │   └── nodes/                # Workflow node implementations
│   ├── workflows/                # Business workflow definitions
│   │   ├── enrollment_workflow.py
│   │   ├── payment_workflow.py
│   │   └── workflow_nodes/       # Specialized workflow nodes
│   ├── api/                      # FastAPI endpoints
│   │   └── v1/endpoints/         # API endpoint implementations
│   ├── models/                   # Database models
│   ├── schemas/                  # Request/response schemas
│   ├── services/                 # Business logic services
│   └── auth/                     # Authentication & authorization
├── docker/                       # Docker configuration
│   ├── docker-compose.yml        # Multi-service orchestration
│   ├── Dockerfile.api            # API service container
│   └── volumes/                  # Persistent data volumes
├── ai_docs/                      # Comprehensive documentation
│   ├── context/core_docs/        # Architecture & requirements
│   └── guides/                   # Development guides
└── playground/                   # Development utilities
```

## 🔧 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd cedar-heights-BE
```

### 2. Environment Setup
```bash
# Copy environment template
cp docker/.env.example docker/.env

# Configure required environment variables
# - Supabase credentials
# - Stripe API keys
# - Email service credentials
# - AI provider API keys (optional)
```

### 3. Start the System
```bash
# Start all services
cd docker
docker-compose up -d

# View logs
docker-compose logs -f api
```

### 4. Verify Installation
```bash
# Check API health
curl http://localhost:8080/health

# Access API documentation
open http://localhost:8080/docs
```

## 📚 API Documentation

### Core Endpoints

#### Authentication & Users
- `POST /auth/login` - User authentication
- `GET /auth/me` - Current user profile
- `POST /auth/refresh` - Token refresh

#### Student Management
- `GET /api/v1/students` - List students with filtering
- `POST /api/v1/students` - Create new student
- `GET /api/v1/students/{id}` - Get student details
- `PUT /api/v1/students/{id}` - Update student information
- `DELETE /api/v1/students/{id}` - Soft delete student

#### Teacher Management
- `GET /api/v1/teachers` - List teachers with availability
- `POST /api/v1/teachers` - Create teacher profile
- `PUT /api/v1/teachers/{id}/availability` - Update availability

#### Lesson Scheduling
- `GET /api/v1/lessons` - List lessons with filtering
- `POST /api/v1/lessons` - Schedule new lesson
- `POST /api/v1/lessons/check-conflicts` - Check scheduling conflicts
- `GET /api/v1/lessons/schedule/view` - Calendar view

#### Payment Processing
- `GET /api/v1/payments` - Payment history
- `POST /api/v1/payments/process` - Process payment
- `POST /api/v1/stripe/webhooks` - Stripe webhook handler

#### Public APIs (No Authentication)
- `GET /api/v1/public/teachers` - Public teacher information
- `GET /api/v1/public/timeslots` - Available lesson slots
- `GET /api/v1/public/pricing` - Current pricing information

### Interactive Documentation
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## 🔐 Security Features

### Authentication & Authorization
- **JWT Token Authentication**: Supabase-powered secure authentication
- **Role-Based Access Control**: Admin, Teacher, and Parent roles
- **Row Level Security**: Database-level access control
- **API Rate Limiting**: Protection against abuse

### Data Protection
- **Input Validation**: Comprehensive Pydantic validation
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **CORS Configuration**: Secure cross-origin resource sharing
- **Security Headers**: Comprehensive security header implementation

## 🔄 Workflow System

### Workflow Architecture
The system uses a sophisticated workflow orchestration engine based on Directed Acyclic Graphs (DAGs) for complex business processes:

```python
class EnrollmentWorkflow(Workflow):
    workflow_schema = WorkflowSchema(
        description="Complete student enrollment process",
        event_schema=EnrollmentEventSchema,
        start=ValidateEnrollmentNode,
        nodes=[
            NodeConfig(node=ValidateEnrollmentNode, connections=[CreateStudentAccountNode]),
            NodeConfig(node=CreateStudentAccountNode, connections=[SetupPaymentMethodNode]),
            NodeConfig(node=SetupPaymentMethodNode, connections=[AssignTeacherNode]),
            NodeConfig(node=AssignTeacherNode, connections=[ScheduleDemoLessonNode]),
            NodeConfig(node=ScheduleDemoLessonNode, connections=[SendWelcomeEmailsNode])
        ]
    )
```

### Key Workflow Features
- **Type Safety**: End-to-end Pydantic validation
- **Error Handling**: Comprehensive error recovery and retry logic
- **State Management**: Persistent workflow state with Redis
- **Monitoring**: Complete workflow execution tracking
- **Scalability**: Horizontal scaling through stateless design

## 📊 Performance Metrics

### Response Time Targets
- **Quick APIs**: <200ms (95th percentile)
- **Workflow APIs**: <2s (95th percentile)
- **Background Workflows**: <30s completion

### System Capabilities
- **Concurrent Users**: 100+ simultaneous users
- **Student Capacity**: 500+ students supported
- **Lesson Processing**: 1000+ lessons/day
- **Payment Processing**: 99%+ success rate

## 🧪 Testing

### Test Coverage
- **Unit Tests**: >80% code coverage
- **Integration Tests**: Complete workflow testing
- **API Tests**: Comprehensive endpoint validation
- **Performance Tests**: Load and stress testing

### Running Tests
```bash
# Run all tests
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=app

# Run specific test suite
docker-compose exec api pytest tests/test_workflows/
```

## 📈 Monitoring & Observability

### Logging
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Log Levels**: DEBUG, INFO, WARN, ERROR with appropriate filtering
- **Performance Monitoring**: Request/response time tracking
- **Error Tracking**: Comprehensive error logging and alerting

### Health Checks
- **API Health**: `/health` endpoint with dependency checks
- **Database Health**: Connection and query performance monitoring
- **External Service Health**: Stripe, Supabase, email service monitoring

## 🚀 Deployment

### Production Deployment
```bash
# Production environment setup
cp docker/.env.example docker/.env.production

# Deploy with production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Database migrations
docker-compose exec api alembic upgrade head
```

### Environment Configuration
- **Development**: Local development with hot reload
- **Staging**: Pre-production testing environment
- **Production**: Optimized production deployment

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Set up local development environment
4. Make changes with comprehensive tests
5. Submit pull request with detailed description

### Code Standards
- **Type Hints**: All functions must include type annotations
- **Documentation**: Comprehensive docstrings for all public APIs
- **Testing**: New features require corresponding tests
- **Linting**: Code must pass flake8 and black formatting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- **Architecture Guide**: [ai_docs/context/core_docs/add.md](ai_docs/context/core_docs/add.md)
- **API Specification**: [ai_docs/context/core_docs/api_endpoints_specification.md](ai_docs/context/core_docs/api_endpoints_specification.md)
- **Development Guide**: [ai_docs/guides/AI_ASSISTED_DEVELOPMENT_GUIDE.md](ai_docs/guides/AI_ASSISTED_DEVELOPMENT_GUIDE.md)

### Getting Help
- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and community support
- **Email**: support@cedarheights.academy for direct support

## 🎵 About Cedar Heights Music Academy

Cedar Heights Music Academy is a modern music education platform designed to provide exceptional music instruction while leveraging technology to enhance the learning experience. Our backend system represents the culmination of modern software engineering practices applied to the unique challenges of music education management.

---

**Built with ❤️ for music education**
