# Booking Workflow Specification

> Version: MVP 1.0

## Overview

The booking workflow is designed to balance **customer convenience**, **business security**, and **operational simplicity**. Customers submit booking requests, while the business owner retains full control over approving rentals. The system automates payment verification and availability management to minimize manual work.

---

# Booking Workflow

```text
Browse Vehicle
        │
        ▼
Submit Booking Request
        │
        ▼
Pending Approval
        │
   ┌────┴────┐
Reject     Approve
   │          │
   ▼          ▼
 End    Awaiting Payment
               │
        ┌──────┴──────┐
 Cancel         Payment
(No Charge)         │
                    ▼
          Booking Confirmed
                    │
     Request Reschedule (Optional)
      ≥ 3 Days Before Pickup
                    │
                    ▼
          Waiting for Pickup
                    │
        Owner Releases Vehicle
                    │
                    ▼
             Active Rental
                    │
        ┌───────────┴───────────┐
   Return Vehicle        Request Extension
        │                        │
        ▼                        ▼
 Vehicle Inspection     Availability Check
        │                        │
        ▼                        ▼
 Late Fee?              Approve / Reject
        │
   ┌────┴────┐
  No        Yes
   │          │
   ▼          ▼
Completed  Additional Invoice
                 │
                 ▼
              Payment
                 │
                 ▼
             Completed
```

---

# Booking Status

| Status | Description |
|---------|-------------|
| Draft | Customer is preparing the booking. |
| Pending Approval | Booking request submitted and awaiting owner review. |
| Rejected | Booking request declined by the owner. |
| Awaiting Payment | Booking approved and waiting for customer payment. Vehicle is temporarily reserved. |
| Confirmed | Payment verified successfully. Booking is finalized. |
| Waiting for Pickup | Customer is waiting for the scheduled pickup date. |
| Active Rental | Vehicle has been released to the customer and the rental has officially started. |
| Completed | Vehicle returned and transaction completed successfully. |
| Cancelled | Booking cancelled before payment or automatically due to payment expiration. |

---

# Booking Process

## 1. Submit Booking Request

The customer:

- Selects rental dates.
- Selects estimated pickup and return times.
- Reviews the booking summary.
- Submits a booking request.

Status:

```text
Pending Approval
```

The customer may cancel the request at this stage.

---

## 2. Owner Review

The owner reviews:

- Vehicle availability
- Driver information
- Booking details

Actions:

- Approve
- Reject

Rejected bookings are closed immediately.

Approved bookings proceed to payment.

---

## 3. Payment

After approval:

- An invoice is generated.
- The vehicle is temporarily reserved.
- The customer is redirected to PayMongo Checkout.

Payment is automatically verified through the payment gateway webhook.

Successful payment changes the booking status to:

```text
Confirmed
```

If payment is not completed before the configured deadline, the booking is automatically cancelled and the reserved dates become available again.

---

## 4. Waiting for Pickup

The booking remains in **Waiting for Pickup** until the scheduled pickup date.

### Rescheduling

Customers may request to reschedule their booking if:

- The request is submitted at least **3 days before the pickup date**.
- The new dates are available.

The rental duration remains unchanged. Only the rental period is moved.

---

## 5. Vehicle Pickup

On the pickup day, the owner verifies the customer and releases the vehicle.

The owner manually confirms vehicle release.

Status:

```text
Active Rental
```

This records the actual handover time instead of relying solely on the scheduled pickup time.

---

## 6. Active Rental

While the rental is active:

- The assigned vehicle is unavailable for new bookings.
- Customers may request an extension.
- The owner approves or rejects extension requests based on vehicle availability.

If approved, an additional invoice is generated for the extra rental period.

---

## 7. Vehicle Return

Upon return, the owner performs a vehicle inspection.

Inspection may include:

- Vehicle condition
- Fuel level
- Mileage *(Optional)*
- Accessories
- Damage assessment

If overdue charges apply, the system generates an additional invoice before completing the booking.

---

## 8. Booking Completion

Once:

- The vehicle has been returned,
- Inspection is completed,
- Outstanding balances are paid,

The owner marks the booking as:

```text
Completed
```

The vehicle immediately becomes available for future bookings.

---

# Cancellation Policy

### Before Payment

Customers may cancel their approved booking without penalty.

No refund process is required because payment has not yet been collected.

### After Payment

Customer cancellation is not permitted.

Instead, customers may request a **reschedule** if submitted at least **3 days before the scheduled pickup date**.

This policy simplifies operations by eliminating refund handling during the MVP.

---

# Availability Rules

Vehicle availability is determined using **actual vehicle inventory**, not just the vehicle model.

Example:

```text
Toyota Vios

Available Units: 2 of 3
```

A booking is allowed as long as at least one vehicle unit is available for the selected rental period.

Calendar indicators:

- No indicator — Available
- 🔴 Red dot — Fully booked (no available units)

Pending booking requests do **not** block availability. Only approved and reserved bookings affect the booking calendar.

---

# Design Principles

The booking workflow should prioritize:

- Simple and intuitive user experience
- Minimal manual input
- Clear booking status progression
- Real-time availability checking
- Automatic payment verification
- Transparent pricing
- Minimal administrative workload
- Secure and auditable booking lifecycle
- Scalability for future features such as deposits, refunds, promotions, and multiple branches