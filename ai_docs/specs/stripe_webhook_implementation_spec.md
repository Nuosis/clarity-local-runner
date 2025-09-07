# Stripe Webhook Implementation Specification - Simplified

## Executive Summary

This specification outlines a simplified Stripe webhook implementation focused solely on subscription payment events. All other Stripe operations (customer creation, subscription management, refunds, etc.) will be handled via direct API calls from the admin frontend.

## Scope

### **In Scope - Webhook Events Only:**
- `invoice.payment_succeeded` - Subscription payment completed successfully
- `invoice.payment_failed` - Subscription payment failed

### **Out of Scope - Handled by Admin Frontend:**
- Customer creation/updates/deletion
- Subscription creation/updates/cancellation
- Payment intent processing (one-time payments)
- Refund processing
- Dispute handling
- Payment method management

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Stripe API    │    │  Cedar Heights   │    │   Database      │
│                 │    │     Backend      │    │                 │
│ • Invoice       │───►│ • Webhook        │◄──►│ • Users         │
│   Events Only   │    │   Endpoint       │    │ • Subscriptions │
│                 │    │ • PaymentWorkflow│    │ • Payments      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Celery Worker   │
                       │                  │
                       │ • Payment Proc.  │
                       │ • Notifications  │
                       │ • Accounting     │
                       └──────────────────┘
```

## Core Components

### 1. Stripe Webhook Handler (Existing)
**Location**: `app/api/v1/endpoints/stripe_webhooks.py`
**Purpose**: Secure webhook endpoint for subscription payment events only

**Supported Events**:
- `invoice.payment_succeeded`
- `invoice.payment_failed`

### 2. Event Processing (Simplified)
**Location**: `app/services/stripe_webhook_service.py` (existing)
**Purpose**: Process subscription payment webhooks

**Responsibilities**:
- HMAC signature verification
- Event validation for invoice events only
- Route to existing PaymentWorkflow
- Idempotency handling

### 3. New SubscriptionPaymentWorkflow
**Location**: `app/workflows/subscription_payment_workflow.py`
**Purpose**: Handle subscription payment processing from webhooks

**Workflow Nodes**:
1. `RecordSubscriptionPaymentNode` - Record payment in DB with unique paymentId (prevents duplicates)
2. `SubscriptionPaymentRouterNode` - Route based on payment success/failure
3. `GenerateReceiptNode` - Generate and send receipt for successful payments
4. `GenerateInvoiceNode` - Generate and send invoice for successful payments
5. `UpdateAccountingNode` - Create accounting entries (reused from existing)
6. `PaymentFailureHandlingNode` - Handle failed payments (reused from existing)

## Implementation Plan

### Phase 1: Webhook Infrastructure (Week 1)
**Sprint 1.1: Core Setup (3 days)**
- [ ] Task 1.1.1: Update webhook endpoint to filter for invoice events only (2h)
- [ ] Task 1.1.2: Enhance signature verification for invoice events (2h)
- [ ] Task 1.1.3: Add invoice event validation schemas (3h)
- [ ] Task 1.1.4: Implement idempotency for invoice events (3h)
- [ ] Task 1.1.5: Unit tests for invoice webhook processing (4h)

**Sprint 1.2: New Workflow Creation (2 days)**
- [ ] Task 1.2.1: Create SubscriptionPaymentWorkflow (4h)
- [ ] Task 1.2.2: Create RecordSubscriptionPaymentNode (6h)
- [ ] Task 1.2.3: Create SubscriptionPaymentRouterNode (4h)
- [ ] Task 1.2.4: Map invoice events to new workflow (2h)
- [ ] Task 1.2.5: Register webhook endpoint in API router (1h)

### Phase 2: Testing & Deployment (Week 2)
**Sprint 2.1: Testing (3 days)**
- [ ] Task 2.1.1: End-to-end testing with Stripe test webhooks (6h)
- [ ] Task 2.1.2: Error scenario testing (failed payments, invalid signatures) (4h)
- [ ] Task 2.1.3: Performance testing (webhook processing time) (2h)
- [ ] Task 2.1.4: Security testing (signature validation, replay attacks) (3h)

**Sprint 2.2: Deployment (2 days)**
- [ ] Task 2.2.1: Production webhook endpoint configuration (2h)
- [ ] Task 2.2.2: Monitoring and alerting setup (3h)
- [ ] Task 2.2.3: Documentation and runbooks (3h)
- [ ] Task 2.2.4: Production deployment and testing (4h)

## Data Models

### Enhanced StripeEvent Model (Simplified)
```python
class StripeEvent(Base):
    id: UUID
    stripe_event_id: str      # Stripe's event ID
    event_type: str           # 'invoice.payment_succeeded' or 'invoice.payment_failed'
    processed: bool
    processed_at: datetime
    webhook_received_at: datetime
    invoice_data: JSON        # Stripe invoice data
    subscription_id: str      # Stripe subscription ID
    customer_id: str          # Stripe customer ID
    workflow_id: UUID         # Associated workflow execution
    idempotency_key: str      # For duplicate detection
```

## Webhook Event Handling

### Supported Events Detail

#### `invoice.payment_succeeded`
**Trigger**: When a subscription payment is successfully processed
**Workflow**: SubscriptionPaymentWorkflow
**Actions**:
- Record payment in database with unique paymentId (prevents duplicates)
- Generate and send receipt to customer
- Generate and send invoice to customer
- Create accounting entries
- Update subscription status

#### `invoice.payment_failed`
**Trigger**: When a subscription payment fails
**Workflow**: SubscriptionPaymentWorkflow → PaymentFailureHandlingNode
**Actions**:
- Record failed payment attempt with unique paymentId
- Update subscription status to past_due
- Send failure notifications
- Schedule retry if appropriate

### Event Processing Flow (Simplified)
```
Stripe Invoice Event → Webhook Endpoint → Signature Verification →
Event Validation → SubscriptionPaymentWorkflow → Database Update → Receipt/Invoice Generation
```

## Security Requirements

### Webhook Security
- **HMAC Signature Verification**: All webhooks verified using Stripe's signature
- **Event Type Filtering**: Only process invoice.payment_* events
- **Timestamp Validation**: Reject webhooks older than 5 minutes
- **Idempotency**: Prevent duplicate processing using event IDs

### Data Protection
- **Minimal Data Storage**: Only store necessary invoice and subscription data
- **Secure Logging**: Sanitize logs to prevent sensitive data exposure
- **Access Controls**: Webhook endpoint accessible only to Stripe

## Testing Strategy

### Unit Tests
- Webhook signature verification
- Invoice event validation
- Workflow routing for invoice events
- Idempotency handling

### Integration Tests
- Complete webhook to workflow processing
- Database updates for successful/failed payments
- Notification sending

### End-to-End Tests
- Stripe test webhook processing
- Payment success and failure scenarios
- Error handling and recovery

## Monitoring & Observability

### Key Metrics
- **Webhook Processing Success Rate**: Target >99%
- **Processing Time**: Target <5 seconds
- **Failed Payment Rate**: Monitor subscription payment failures
- **Duplicate Event Rate**: Monitor idempotency effectiveness

### Alerting
- **Critical**: Webhook processing failure rate >5%
- **Warning**: Webhook processing time >10 seconds
- **Info**: High volume of failed subscription payments

## Success Criteria

### Functional Requirements
- [ ] Process `invoice.payment_succeeded` events successfully
- [ ] Process `invoice.payment_failed` events successfully
- [ ] Maintain existing PaymentWorkflow functionality
- [ ] Prevent duplicate event processing
- [ ] Secure webhook signature verification

### Non-Functional Requirements
- [ ] 99% webhook processing success rate
- [ ] <5 second webhook processing time
- [ ] Zero security vulnerabilities
- [ ] Complete test coverage (>90% unit, >80% integration)

### Business Requirements
- [ ] Automated subscription payment processing
- [ ] Timely failure notifications for failed payments
- [ ] Accurate accounting records for all payments
- [ ] Reliable subscription status updates

## Implementation Estimate

**Total Effort**: 2 weeks (80 hours)
- **Week 1**: Core webhook infrastructure and workflow integration
- **Week 2**: Testing, monitoring, and deployment

**Team Size**: 1 developer
**Risk Level**: Low (leveraging existing infrastructure)

## Dependencies

### External Dependencies
- **Stripe API**: Webhook delivery and invoice data
- **Existing PaymentWorkflow**: Subscription payment processing
- **Database**: PostgreSQL for event and payment storage
- **Message Queue**: Celery/Redis for async processing

### Internal Dependencies
- **Event System**: Existing event processing infrastructure
- **Workflow Engine**: GenAI Launchpad workflow framework
- **Notification System**: Email notifications for payment events

## Conclusion

This simplified approach focuses solely on subscription payment webhooks while leveraging the existing robust PaymentWorkflow infrastructure. By limiting scope to only invoice events and handling all other operations via admin frontend API calls, we achieve:

1. **Reduced Complexity**: Minimal new code required
2. **Lower Risk**: Leverages proven existing workflows
3. **Faster Implementation**: 2-week timeline vs 8-week comprehensive approach
4. **Maintainability**: Simpler system with fewer moving parts
5. **Flexibility**: Admin frontend can handle complex operations with full control

The implementation provides automated subscription payment processing while maintaining the ability to handle all other Stripe operations through direct API calls from the admin interface.