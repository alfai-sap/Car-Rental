# Booking Module Specification

> Module Version: 1.0 (MVP)
>
> Purpose: Allow customers to request a vehicle rental through an intuitive booking workflow while enabling the business owner to review and approve requests before payment.

---

# Overview

The Booking Module provides customers with a simple and transparent rental experience.

Rather than immediately creating a booking, the system guides customers through a booking workflow where they:

- Select rental dates
- View vehicle availability
- Review real-time pricing
- Complete required information
- Submit a booking request

The business owner then reviews the request before the customer proceeds to payment.

---

# Booking Workflow

```text
Browse Vehicles

↓

Vehicle Details

↓

Book Now

↓

Booking Page

↓

Select Rental Dates

↓

Check Availability

↓

Calculate Rental Cost

↓

Review Booking Summary

↓

Driver Information Complete?

├── No
│      ↓
│  Complete Driver Information
│
└── Yes
│
▼

Submit Booking Request

↓

Booking Status

Pending Approval

↓

Administrator Review

↓

Approve / Reject

↓

If Approved

↓

Payment

↓

Booking Confirmed
```

---

# Booking Process

## Step 1 - Browse Vehicles

Customers browse available vehicles.

Each vehicle card displays:

- Vehicle Image
- Vehicle Name
- Vehicle Category
- Daily Rental Rate
- Seating Capacity
- Transmission
- Fuel Type
- Availability Status

---

## Step 2 - Vehicle Details

The customer selects a vehicle to view detailed information.

The page contains:

- Vehicle Images
- Description
- Daily Rental Rate
- Features
- Specifications
- Rental Terms
- Availability Indicator

Primary Action

```text
Book Now
```

---

## Step 3 - Booking Page

Instead of immediately submitting a booking request, clicking **Book Now** opens a dedicated booking page.

Example URL

```text
/vehicles/{vehicle_id}/book
```

Using a dedicated page provides:

- Better mobile experience
- Shareable URL
- Easier navigation
- Future scalability
- Space for additional booking features

---

# Booking Form

The booking page contains the following sections.

## Rental Dates

Required

- Pickup Date
- Return Date

A Date Range Picker should be used instead of two separate calendars.

The calendar should prevent users from selecting:

- Past dates
- Fully booked dates
- Invalid date ranges

---

## Pickup Details

Required

- Pickup Time

Optional

- Pickup Location (if multiple branches are supported)
- Special Requests

---

## Driver Information

Before submitting a booking, the system verifies whether the customer has completed their Driver Information.

If incomplete, the user is redirected to:

```text
Profile

↓

Driver Information
```

Required fields include:

- Driver's License Number
- License Expiration Date
- Driver's License Image (Front)
- Driver's License Image (Back) *(Optional depending on business requirements)*

After completion, the customer is returned to the booking page.

---

# Calendar Behavior

The booking calendar should provide immediate visual feedback.

Availability States

🟢 Available

Vehicle can be booked.

---

🔴 Unavailable

Vehicle is already reserved.

Selection should be disabled.

---

⚫ Past Date

Cannot be selected.

---

🔵 Selected Dates

Current booking range.

---

# Availability Check

Whenever the customer changes either rental date, the frontend automatically requests availability from the backend.

Example API

```http
GET /api/vehicles/{id}/availability
```

Parameters

- Start Date
- End Date

Example Response

```json
{
    "available": true
}
```

If unavailable, the system displays an informative message and prevents submission.

---

# Real-Time Price Calculation

The booking summary updates automatically whenever the rental dates change.

The frontend calculates:

- Rental Days
- Daily Rate
- Rental Cost
- Deposit (Optional)
- Discounts (Future)
- Taxes (Future)
- Estimated Total

No page refresh should be required.

---

# Booking Summary

A booking summary should always remain visible while completing the booking.

Example

```text
Booking Summary

Vehicle

Toyota Vios

Rental Period

August 6 - August 10

Rental Duration

4 Days

Daily Rate

₱1,500

Subtotal

₱6,000

Security Deposit

₱2,000

Estimated Total

₱8,000
```

All values should update automatically whenever booking details change.

---

# Booking Validation

The **Submit Booking Request** button should only become available when all requirements are met.

Validation Checklist

- User is logged in
- Email is verified
- Driver Information is complete
- Vehicle is available
- Pickup date is valid
- Return date is valid
- Rental period is valid

---

# Booking Submission

After validation, the frontend submits the booking request.

Example API

```http
POST /api/bookings
```

Example Payload

```json
{
    "vehicle_id": 12,
    "pickup_date": "2026-08-06",
    "return_date": "2026-08-10",
    "pickup_time": "09:00",
    "special_request": ""
}
```

The backend creates a booking.

Initial Status

```text
Pending Approval
```

No payment is collected at this stage.

---

# Administrator Review

Administrators review every booking request before payment.

Booking Review includes:

Customer

- Name
- Phone Number
- Email

Driver Information

- License Number
- Expiration Date
- License Images

Booking

- Vehicle
- Rental Dates
- Rental Duration
- Estimated Cost

Available Actions

```text
Approve

Reject
```

---

# Approval Workflow

If Approved

```text
Booking Approved

↓

Invoice Generated

↓

Customer Receives Notification

↓

Pay Now

↓

PayMongo Checkout

↓

Payment Successful

↓

Booking Confirmed
```

---

# Rejection Workflow

If Rejected

The administrator must provide a reason.

Examples

- Vehicle unavailable
- Driver information invalid
- Requested dates unavailable
- Business policy

Customer receives:

- Dashboard notification
- Email notification

Booking Status

```text
Rejected
```

---

# Booking Status

```text
Draft

Pending Approval

Approved

Awaiting Payment

Confirmed

Active Rental

Completed

Cancelled

Rejected
```

---

# Booking Database

## bookings

| Field | Description |
|---------|------------|
| id | Primary Key |
| booking_number | Human-readable booking number |
| customer_id | Customer |
| vehicle_id | Selected vehicle |
| pickup_date | Rental start |
| return_date | Rental end |
| pickup_time | Pickup time |
| rental_days | Number of rental days |
| subtotal | Rental amount |
| estimated_total | Estimated payment |
| status | Booking status |
| special_request | Customer notes |
| created_at | Created timestamp |
| updated_at | Updated timestamp |

---

# Notifications

Customers should receive notifications when:

- Booking submitted
- Booking approved
- Booking rejected
- Payment required
- Payment successful
- Rental reminder *(Future)*

Notification channels

- Dashboard
- Email

---

# Design Principles

The booking process should prioritize:

- Simplicity
- Transparency
- Real-time feedback
- Minimal user input
- Clear pricing
- Fast interactions
- Mobile responsiveness

The customer should always understand:

- What they are booking
- Whether the vehicle is available
- How much it will cost
- What information is still required
- What happens after submitting the request

The booking experience should resemble modern hotel and airline reservation systems, providing immediate feedback and a seamless progression from vehicle selection to payment.