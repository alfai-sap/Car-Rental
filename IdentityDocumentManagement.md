# Identity Document Management

> Module Version: 1.0 (MVP)
>
> Purpose: Protect the integrity of customer identity information during the booking process while maintaining accurate historical transaction records.

---

# Overview

The Identity Document Management module ensures that the identity information reviewed by the business owner remains unchanged throughout an active rental transaction.

Once a customer submits a rental request, the identity information used for that request is preserved and cannot be modified until the transaction reaches a final state.

This prevents inconsistencies between the identity documents reviewed by the owner and the customer's current profile information.

---

# Identity Information

Each customer profile stores the following identity information:

- ID Type
- ID Number
- Driver's License Front Image
- Driver's License Back Image

These fields are used during the rental booking process.

---

# Identity Locking Policy

Upon submission of a rental request, the customer's identity information becomes **locked**.

While locked, the customer may view their identity information but cannot:

- Change ID Type
- Change ID Number
- Replace Driver's License Front Image
- Replace Driver's License Back Image
- Remove uploaded identity documents

The lock remains active until all active bookings have reached a final state.

---

# Booking Status Lock Rules

The identity information remains locked while a booking is in any of the following statuses:

- Pending Approval
- Approved
- Awaiting Payment
- Confirmed
- Active Rental

During these stages, identity information cannot be modified.

---

# Unlock Conditions

The identity information becomes editable again when there are **no active bookings** associated with the customer.

The identity section is automatically unlocked when all bookings are in one of the following final statuses:

- Completed
- Cancelled
- Rejected
- Payment Expired *(if implemented)*

Once unlocked, customers may update their identity information for future bookings.

---

# Editable Profile Information

Only identity-related fields are locked.

Customers may continue to update other profile information at any time, including:

- Phone Number
- Address
- Emergency Contact
- Profile Photo
- Password
- Notification Preferences

These updates do not affect existing bookings.

---

# Identity Snapshot

When the customer submits a rental request, the system immediately creates an immutable snapshot of the customer's identity information.

The snapshot contains:

## Customer Information

- Full Name
- Email Address
- Phone Number

## Identity Information

- ID Type
- ID Number
- Driver's License Front Image
- Driver's License Back Image

## Booking Information

- Booking ID
- Submission Date and Time

This snapshot is permanently attached to the booking record.

---

# Snapshot Behavior

The booking snapshot is completely independent of the customer's profile.

Any future changes to the customer's profile **must not** modify previously created booking snapshots.

Each booking maintains its own historical copy of the identity information used during submission.

Example:

```text
Customer Profile

ID Number
D01-99-888888

↓

Booking #100

ID Number
D01-23-123456
```

Updating the customer's profile only affects future bookings.

Previous bookings continue to display the original identity information submitted during that transaction.

---

# Booking Workflow

```text
Customer Updates Identity Information

↓

Customer Submits Rental Request

↓

System Creates Identity Snapshot

↓

Identity Fields Locked

↓

Administrator Reviews Snapshot

↓

Booking Process Continues

↓

Booking Completed / Cancelled / Rejected

↓

Identity Fields Automatically Unlocked
```

---

# Administrator View

Each booking contains its own identity snapshot.

Example

```text
Booking #CR-2026-00125

Customer Information

Name
John Doe

Email
john@example.com

Phone
09123456789

--------------------------------

Identity Information

ID Type
Driver's License

ID Number
D01-23-123456

Front Image
[ View ]

Back Image
[ View ]

Snapshot Date
August 6, 2026
```

Administrators always review the snapshot stored with the booking rather than the customer's current profile.

---

# Backend Enforcement

Identity locking must be enforced on both the frontend and backend.

## Frontend

When identity information is locked:

- Disable all identity input fields.
- Disable upload controls.
- Disable delete actions.
- Display an informational message explaining why the fields are locked.

## Backend

All API requests attempting to modify locked identity information must be rejected.

Example response:

```http
HTTP 403 Forbidden
```

```json
{
    "message": "Identity information cannot be modified while you have an active booking."
}
```

Backend validation prevents unauthorized modifications even if a user bypasses the frontend interface.

---

# User Interface

When identity information is locked, display an informational notice.

Example:

> **Your identity information is currently locked because it is associated with an active rental request. You can update it once all active bookings have been completed, cancelled, or rejected.**

The customer may still view all identity information but cannot make changes until the lock is removed.

---

# Design Principles

This implementation follows the following principles:

- Preserve historical transaction records.
- Ensure administrators always review immutable identity information.
- Prevent identity changes during active transactions.
- Allow profile updates that do not affect booking integrity.
- Keep the implementation simple and suitable for small businesses.
- Maintain scalability for future identity verification features.

---

# Future Enhancements

Potential future improvements include:

- Administrative identity verification.
- Multiple identity documents per customer.
- Identity document version history.
- Identity verification status (Pending, Verified, Rejected).
- Automatic document expiration reminders.
- Audit logs for identity updates.