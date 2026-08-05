# Car Rental Management System (MVP)

**Version:** 1.1  
**Status:** MVP Prototype Specification

---

# Table of Contents

1. Project Overview
2. Project Goals
3. Technology Stack
4. System Architecture
5. User Roles
6. MVP Modules
7. Authentication Module
8. Customer Module
9. Vehicle Module
10. Search & Filtering
11. Booking Module
12. Payment Module
13. Customer Dashboard
14. Administrator Dashboard
15. Vehicle Management
16. Booking Management
17. Reports
18. Business Settings
19. Database Design
20. UI Pages
21. Non-Functional Requirements
22. Development Roadmap
23. Future Scope

---

# 1. Project Overview

## Project Name

**Car Rental Management System**

## Goal

Develop a modern, responsive web application that allows customers to browse available rental vehicles, create an account, reserve a vehicle, and complete online payments.

The application should also provide administrators with tools to manage vehicles, customers, bookings, and business operations.

This MVP serves as a complete working prototype that can be demonstrated to clients while establishing a scalable foundation for future expansion into a production-ready platform.

---

# 2. Project Goals

## Customer Goals

- Create an account
- Securely login
- Browse available vehicles
- Search and filter vehicles
- View vehicle information
- Book a vehicle
- Pay online
- View booking history
- Manage personal profile

---

## Business Goals

- Manage vehicles
- Manage bookings
- Manage customers
- Track rental activity
- View reports
- Configure rental settings

---

# 3. Technology Stack

## Frontend

- Vue 3
- TypeScript
- Inertia.js
- Tailwind CSS
- Pinia
- Vite

---

## Backend

- Django

---

## Database

- PostgreSQL

---

## Authentication

- Django Session Authentication
- CSRF Protection

---

## Payment Gateway

- PayMongo (Philippines)
- Stripe (Future International Expansion)

---

## File Storage

### MVP

- Local Storage

### Production

- Amazon S3
- Cloudflare R2
- Backblaze B2

---

## Deployment

- Docker
- Gunicorn
- Nginx

---

## Future Infrastructure

- Redis
- Celery

---

# 4. System Architecture

```text
Vue 3
│
├── TypeScript
├── Inertia.js
├── Tailwind CSS
├── Pinia
│
▼
Django
│
▼
PostgreSQL
```

Future Production Architecture

```text
Vue
        │
        ▼
Inertia.js
        │
        ▼
Nginx
        │
        ▼
Gunicorn
        │
        ▼
Django
        │
        ▼
PostgreSQL
        │
        ▼
Redis (Future)
        │
        ▼
Celery (Future)
```

---

# 5. User Roles

## Guest

### Permissions

- Browse vehicles
- Search vehicles
- View vehicle information
- Register
- Login

### Restrictions

- Cannot book vehicles
- Cannot make payments
- Cannot access dashboard

---

## Customer

Can

- Browse vehicles
- Book rentals
- Pay online
- Manage profile
- View bookings
- Cancel pending bookings
- View payment history

---

## Administrator

Can

- Manage vehicles
- Manage customers
- Manage bookings
- Configure business settings
- View reports
- Manage payments

---

# 6. MVP Modules

- Authentication
- Customer Management
- Vehicle Management
- Vehicle Catalog
- Booking Management
- Payment Integration
- Customer Dashboard
- Administrator Dashboard
- Reports
- Business Settings

---

# 7. Authentication Module

## Register

### Fields

- First Name
- Last Name
- Email
- Password
- Confirm Password
- Phone Number
- Driver's License Number

### Validation

- Email must be unique
- Strong password
- Minimum eight characters
- Valid phone number
- Driver's license required

---

## Login

Fields

- Email
- Password
- Remember Me

---

## Forgot Password

- Email password reset

---

## Logout

- Destroy authenticated session

---

# 8. Customer Module

## Customer Profile

Contains

- Name
- Email
- Phone Number
- Driver's License
- Address
- Profile Picture

Editable

- Phone Number
- Address
- Profile Picture

---

## Booking History

Display

- Rental History
- Current Rentals
- Upcoming Rentals
- Payment Records

---

# 9. Vehicle Module

## Vehicle Information

Each vehicle contains

- Images
- Brand
- Model
- Year
- Transmission
- Fuel Type
- Seats
- Color
- Mileage
- Description
- Rental Price
- Status

---

## Vehicle Status

- Available
- Booked
- Maintenance
- Inactive

---

## Vehicle Detail Page

Contains

- Image Gallery
- Specifications
- Rental Price
- Availability
- Book Now Button

---

# 10. Search & Filtering

## Search

- Keyword

---

## Filters

- Brand
- Transmission
- Fuel Type
- Number of Seats
- Price Range
- Availability

---

## Sorting

- Newest
- Lowest Price
- Highest Price
- Most Popular

---

# 11. Booking Module

Customer selects

- Vehicle
- Pickup Date
- Return Date
- Pickup Location
- Return Location

---

System Calculates

- Rental Duration
- Daily Rate
- Insurance
- Taxes
- Total Cost

---

Booking Status

- Pending
- Confirmed
- Cancelled
- Completed

---

Booking Summary

Display

- Vehicle
- Rental Period
- Price Breakdown
- Terms & Conditions
- Payment Button

---

# 12. Payment Module

## Supported Payments

- Credit Card
- Debit Card
- GCash (Supported Gateway)

---

## Payment Status

- Pending
- Paid
- Failed
- Refunded

---

Store Only

- Transaction ID
- Gateway Reference
- Amount
- Timestamp
- Payment Status

Never Store

- Card Number
- CVV
- Expiration Date

---

# 13. Customer Dashboard

Sections

- Upcoming Rentals
- Booking History
- Payment History
- Invoices
- Profile

---

# 14. Administrator Dashboard

Summary Cards

- Total Vehicles
- Available Vehicles
- Active Rentals
- Registered Customers
- Revenue
- Pending Bookings

---

# 15. Vehicle Management

Administrator can

- Add Vehicle
- Edit Vehicle
- Delete Vehicle
- Upload Images
- Change Status
- Update Rental Price

---

# 16. Booking Management

Administrator can

- Approve Booking
- Reject Booking
- Cancel Booking
- Complete Booking

Booking Information

- Customer
- Vehicle
- Rental Dates
- Payment Status
- Booking Status

---

# 17. Reports

Generate

- Booking Reports
- Revenue Reports
- Vehicle Reports
- Customer Reports

Future

- Export CSV
- Export PDF

---

# 18. Business Settings

## Company Information

- Business Name
- Contact Number
- Email
- Address

---

## Rental Settings

- Minimum Rental Days
- Maximum Rental Days
- Grace Period
- Late Fee
- Tax Percentage

---

# 19. Database Design

## Core Tables

```text
users
roles
customer_profiles

vehicles
vehicle_images

bookings
booking_status

payments
payment_transactions

business_settings
```

---

## Future Tables

```text
reviews
notifications
maintenance_records
promotions
coupons
audit_logs
vehicle_categories
insurance_policies
```

---

# 20. UI Pages

## Public Pages

- Home
- Vehicle Listing
- Vehicle Details
- About
- Contact
- Login
- Register

---

## Customer Pages

- Dashboard
- Bookings
- Payments
- Profile

---

## Administrator Pages

- Dashboard
- Vehicles
- Bookings
- Customers
- Reports
- Business Settings

---

# 21. Non-Functional Requirements

## Performance

- Initial load under 2 seconds
- Responsive on desktop, tablet, and mobile
- Lazy-load vehicle images
- Pagination for large datasets
- Optimized images using WebP

---

## Security

- HTTPS only
- Django Session Authentication
- CSRF Protection
- XSS Protection
- SQL Injection Protection through Django ORM
- Server-side validation
- Secure password hashing
- Role-based authorization
- Secure file uploads

---

## Scalability

Designed to support

- Thousands of users
- Thousands of vehicles
- Large booking history
- Future background processing using Redis and Celery

---

## Usability

- Mobile-first design
- Accessible forms
- Consistent navigation
- Simple booking workflow

---

# 22. Development Roadmap

## Phase 1 — Foundation

- Project Setup
- Authentication
- User Roles
- Database Setup
- Global Layout
- Navigation

---

## Phase 2 — Vehicle Catalog

- Vehicle CRUD
- Image Upload
- Search
- Filters
- Vehicle Detail Page

---

## Phase 3 — Booking System

- Availability Checking
- Booking Creation
- Booking Management

---

## Phase 4 — Payments

- PayMongo Integration
- Payment Callback
- Booking Confirmation
- Payment History

---

## Phase 5 — Dashboards

- Customer Dashboard
- Administrator Dashboard
- Reports

---

## Phase 6 — Production Ready

- Responsive Improvements
- Performance Optimization
- Error Handling
- Testing
- Deployment

---

# 23. Future Scope

Not included in the MVP

- Mobile Application
- Progressive Web App (PWA)
- Multi-branch Management
- Driver Assignment
- Fleet Maintenance
- Dynamic Pricing
- Coupons
- Loyalty Rewards
- SMS Notifications
- Email Notifications
- GPS Tracking
- Live Chat
- AI Vehicle Recommendations
- Multi-language Support
- Multi-currency Support
- Accounting Integration
- Advanced Analytics
- Redis Caching
- Celery Background Jobs

---

# MVP Summary

The Car Rental Management System MVP is designed as a **vertical slice prototype**, demonstrating the complete customer journey from account registration to vehicle booking and payment.

The chosen stack emphasizes simplicity, maintainability, and scalability:

- **Vue 3 + Inertia.js** provides a modern, SPA-like user experience without requiring a separate REST API.
- **Django** handles business logic, authentication, validation, and server-side rendering through Inertia.
- **PostgreSQL** offers a reliable and scalable relational database.
- **Tailwind CSS** enables rapid development of a responsive, professional interface.
- **Pinia** manages client-side state where appropriate.
- **Django Session Authentication** provides secure authentication with built-in CSRF protection.

This architecture minimizes complexity during the MVP phase while allowing the application to evolve into a production-ready platform with future additions such as Redis, Celery, cloud storage, Progressive Web App support, and advanced business features without significant architectural changes.