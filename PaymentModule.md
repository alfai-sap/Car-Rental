# Payment Module Specification

> Module Version: 1.0 (MVP)
>
> Payment Gateway: PayMongo
>
> Purpose: Handle secure online payments without storing customer financial credentials.

---

# Overview

The Car Rental Management System delegates all payment processing to **PayMongo**.

The application **never stores or processes sensitive payment credentials** such as credit card numbers, CVV, online banking passwords, or GCash PINs.

Instead, the system creates a payment request through the PayMongo API and redirects the customer to PayMongo's secure checkout page.

After payment, PayMongo notifies the backend through a secure webhook, allowing the system to update the booking and payment status.

---

# Development Environment (Sandbox)

The development environment uses PayMongo's **Test API Keys**.

Features available during development include:

- Simulate successful payments
- Simulate failed payments
- Simulate cancelled payments
- Simulate expired payments
- Test PayMongo Checkout
- Test Webhook Integration
- Test Booking-to-Payment workflow
- Test Payment History

No real money is transferred during sandbox testing.

---

# Production Environment (Live)

When the project is deployed, the business owner must:

1. Create a PayMongo Business Account.
2. Complete PayMongo's verification process.
3. Connect a receiving bank account.
4. Obtain Live API Keys.

The application will then communicate with PayMongo's Live API, allowing customers to make real payments that are deposited into the owner's registered bank account.

No changes to the application workflow are required other than updating the API credentials.

---

# Environment Configuration

The application should support separate environments.

Development

```env
PAYMONGO_PUBLIC_KEY=pk_test_xxxxxxxxx
PAYMONGO_SECRET_KEY=sk_test_xxxxxxxxx
PAYMONGO_WEBHOOK_SECRET=whsec_test_xxxxxxxxx
```

Production

```env
PAYMONGO_PUBLIC_KEY=pk_live_xxxxxxxxx
PAYMONGO_SECRET_KEY=sk_live_xxxxxxxxx
PAYMONGO_WEBHOOK_SECRET=whsec_live_xxxxxxxxx
```

The application should automatically determine which environment to use based on its deployment configuration.

---

# Payment Workflow

```text
Customer

↓

Car Rental System

↓

PayMongo Checkout

↓

Customer Completes Payment

↓

PayMongo Processes Transaction

↓

PayMongo Sends Webhook

↓

Backend Verifies Webhook

↓

Update Payment Status

↓

Update Booking Status
```

The workflow remains identical in both Sandbox and Live environments.

---


# Payment Flow

```text
Customer

↓

Books Vehicle

↓

Booking Request Submitted

↓

Admin Reviews Booking

↓

Approved?

├── No
│     ↓
│  Booking Rejected
│
└── Yes
      ↓
Generate Invoice
      ↓
Customer Clicks "Pay Now"
      ↓
Django Creates PayMongo Checkout Session
      ↓
Customer Redirected to PayMongo Checkout
      ↓
Customer Chooses Payment Method
      ↓
Payment Processed by PayMongo
      ↓
PayMongo Sends Webhook
      ↓
Django Updates Payment Status
      ↓
Booking Confirmed
```

---

# Payment Responsibilities

## Customer

Responsible for

- Choosing payment method
- Completing payment
- Authorizing payment
- Viewing payment status

---

## Car Rental System

Responsible for

- Creating payment requests
- Redirecting customer to PayMongo
- Recording transaction information
- Updating booking status
- Displaying payment history

---

## PayMongo

Responsible for

- Payment processing
- Payment security
- Credit card handling
- Digital wallet handling
- Fraud detection
- Payment settlement
- Depositing funds to business owner

---

# Supported Payment Methods

## MVP

- Credit Card
- Debit Card
- GCash
- Maya

Future payment methods may include

- Bank Transfers
- QR Payments
- Installments
- Additional digital wallets

---

# Payment Workflow

## Step 1

Customer submits a booking request.

Booking Status

```text
Pending Approval
```

---

## Step 2

Administrator reviews booking.

Possible outcomes

- Approve
- Reject

Only approved bookings can proceed to payment.

---

## Step 3

System generates an invoice.

Invoice contains

- Booking Number
- Vehicle
- Rental Dates
- Rental Amount
- Security Deposit (Optional)
- Taxes (if applicable)
- Total Amount

Invoice Status

```text
Pending Payment
```

---

## Step 4

Customer clicks

```text
Pay Now
```

The frontend sends a request to Django.

Example

```http
POST /api/payments/create-session
```

The backend

- Validates booking
- Computes total
- Creates PayMongo Checkout Session

---

## Step 5

PayMongo returns

- Checkout URL
- Checkout Session ID

The frontend redirects the customer.

```text
Customer

↓

PayMongo Checkout
```

---

## Step 6

Customer completes payment.

Payment credentials are entered only on PayMongo's secure checkout page.

The Car Rental System never receives

- Card Number
- CVV
- OTP
- GCash PIN
- Online Banking Password

---

## Step 7

PayMongo processes payment.

Possible results

- Paid
- Failed
- Cancelled
- Expired

---

## Step 8

PayMongo calls the webhook.

Example

```http
POST /api/payments/webhook
```

The backend

- Validates webhook signature
- Finds booking
- Updates payment
- Updates booking

---

## Step 9

Customer returns to website.

Payment page displays

```text
Payment Successful
```

or

```text
Payment Failed
```

---

# Money Flow

```text
Customer

↓

PayMongo Checkout

↓

PayMongo

↓

Business Owner's PayMongo Account

↓

Business Owner's Connected Bank Account
```

The Car Rental System never directly receives customer funds.

---

# Security Principles

## Never Store

The application must never store

- Credit Card Number
- Debit Card Number
- CVV
- OTP
- GCash Password
- GCash PIN
- Online Banking Credentials

---

## Store Only

The system should store

- Booking ID
- Invoice ID
- Payment ID
- PayMongo Transaction ID
- Amount
- Currency
- Payment Method
- Payment Status
- Payment Date

---

# Payment Status

Possible payment states

```text
Pending

Paid

Failed

Cancelled

Expired

Refunded
```

---

# Booking Status

```text
Pending Approval

Approved

Awaiting Payment

Confirmed

Completed

Cancelled

Rejected
```

---

# Invoice Status

```text
Pending

Paid

Overdue

Cancelled
```

---

# Payment Database

## payments

| Field | Description |
|---------|------------|
| id | Primary Key |
| booking_id | Related booking |
| invoice_id | Related invoice |
| paymongo_payment_id | Transaction ID |
| amount | Amount paid |
| currency | PHP |
| payment_method | Card, GCash, Maya |
| payment_status | Pending, Paid, Failed |
| paid_at | Payment timestamp |
| created_at | Creation timestamp |
| updated_at | Last update |

---

# Invoice Database

## invoices

| Field | Description |
|---------|------------|
| id | Primary Key |
| booking_id | Related booking |
| subtotal | Rental fee |
| additional_charges | Optional charges |
| discount | Discount |
| total | Final amount |
| invoice_status | Pending, Paid, Overdue |
| due_date | Due date |
| created_at | Creation timestamp |

---

# Payment API Endpoints

## Customer

Create Checkout

```http
POST /api/payments/create-session
```

---

Get Payment

```http
GET /api/payments/{id}
```

---

Get Payment History

```http
GET /api/payments/history
```

---

## PayMongo

Webhook

```http
POST /api/payments/webhook
```

---

# Failed Payment

If payment fails

Booking

```text
Awaiting Payment
```

Customer may

- Retry Payment
- Cancel Booking

---

# Cancelled Payment

If customer closes checkout

Payment

```text
Cancelled
```

Booking remains

```text
Awaiting Payment
```

---

# Expired Payment

If checkout expires

Payment

```text
Expired
```

Customer may generate a new checkout session.

---

# Overdue Payments (Future)

Some rentals may allow payment after vehicle return.

Example

```text
Rental Fee

₱4,500

Late Fee

₱750

Damage Fee

₱0

------------------

Total

₱5,250
```

Invoice

```text
Overdue
```

Customer receives

- Email reminder
- Dashboard notification

Customer pays through a newly generated PayMongo checkout session.

---

# Refunds (Future)

Refunds should be initiated only by administrators.

Workflow

```text
Customer Requests Refund

↓

Administrator Reviews

↓

Approved

↓

PayMongo Refund API

↓

Payment Status

Refunded
```

---

# Deployment Checklist

Before switching to production:

- Business owner has a verified PayMongo account.
- Business bank account is connected.
- Live API keys are configured.
- Live webhook endpoint is registered.
- HTTPS is enabled.
- Sandbox keys are removed from the production environment.
- A live payment test is successfully completed.

# Future Enhancements

- Saved Payment Methods (PayMongo Tokenization, if supported)
- Automatic Charging for Authorized Payment Methods
- Partial Payments
- Security Deposits
- Damage Charges
- Installment Payments
- Promo Codes
- Gift Cards
- Loyalty Credits
- Automatic Invoice Generation
- Automated Payment Reminders
- Financial Reports

---

# Future Compatibility

The payment module should be designed to be payment-gateway agnostic.

A dedicated payment service layer should abstract gateway-specific logic so additional providers (e.g., Stripe or Xendit) can be integrated in the future with minimal changes to the rest of the application.

# Design Principles

The payment module should follow these principles:

- Never handle sensitive financial credentials.
- Delegate all payment processing to PayMongo.
- Validate all webhook requests before updating payment records.
- Record every payment transaction for audit purposes.
- Keep payment and booking records separate while linking them through foreign keys.
- Ensure payment failures do not corrupt booking data.
- Allow customers to retry failed or expired payments without creating duplicate bookings.
- Design the module so additional payment gateways can be integrated in the future with minimal changes.