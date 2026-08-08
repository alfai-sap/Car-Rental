# 🚗 Car Rental Management System — Complete Project Analysis

## 1. What Is This Project?

This is a **full-stack web application** for managing a vehicle rental business, built with **Vue 3 + Django REST Framework + PostgreSQL**. It digitizes the entire rental process — from browsing vehicles, submitting booking requests, admin approval, online payment (via PayMongo), to vehicle handover and return. The project is at **MVP (Phase 4)** stage and has substantial code already written across both frontend and backend.

The current branch is **`Phase4-Booking-System-Codex`** and the default branch is `main`.

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Vue 3 (Composition API), TypeScript, Vite, Tailwind CSS v4, Radix-Vue, Pinia, Vue Router, Axios, Lucide icons |
| **Backend** | Django 4.2+, Django REST Framework, Simple JWT, django-cors-headers, django-filter, psycopg2-binary |
| **Database** | PostgreSQL |
| **Payments** | PayMongo (Philippines-focused: GCash, Maya, credit/debit cards) |
| **Auth** | JWT with access/refresh token rotation and blacklisting |
| **File Storage** | Local (MVP), with plans for S3/R2/B2 in production |
| **Deployment** | Docker + Gunicorn + Nginx (planned) |

---

## 3. Architecture & Project Structure

```
Car-Rental/
├── backend/                    # Django REST API
│   ├── config/                 # Project settings, URLs, WSGI/ASGI
│   │   ├── settings.py         # All Django + DRF config
│   │   └── urls.py            # Routes all API apps under /api/
│   ├── apps/
│   │   ├── core/              # Shared utilities (health check endpoint)
│   │   ├── accounts/          # User auth, JWT, identity documents
│   │   ├── vehicles/          # Vehicle models, units, images
│   │   ├── bookings/          # Booking lifecycle, workflow
│   │   └── payments/          # Invoices, payments, PayMongo integration
│   ├── templates/emails/      # HTML email templates
│   ├── media/                 # Uploaded files (identity docs, vehicle images)
│   └── manage.py
├── frontend/                   # Vue 3 SPA
│   └── src/
│       ├── router/index.ts    # 17 routes with auth guards
│       ├── stores/auth.ts     # Pinia auth store (login, JWT refresh, logout)
│       ├── services/api.ts    # Axios with JWT interceptor + auto-refresh
│       ├── components/        # Navbar, UI components (shadcn-vue)
│       └── views/             # 18 view components
└── *.md                       # 7 documentation files
```

---

## 4. Database Models (7 Core Models)

### `accounts.User` (Custom User)
- Extends Django's `AbstractUser`
- Uses **email** as the username field (`USERNAME_FIELD = 'email'`)
- Fields: `email` (unique), `phone`, `is_verified`, `verified_at`
- Has `IdentityDocument` related model

### `accounts.IdentityDocument`
- Linked to `User` via FK
- Fields: `document_type`, `document_number`, `front_image`, `back_image`
- Images stored in `media/identity_docs/front/` and `media/identity_docs/back/`

### `vehicles.Vehicle` (Vehicle Model/Listing)
- Represents a **vehicle listing** shown to customers (e.g., "Toyota Vios 2024")
- Fields: `make`, `model`, `year`, `type`, `transmission`, `fuel`, `seats`, `price_per_day`, `description`, `status`
- Has related `VehicleImage` and `VehicleUnit` models

### `vehicles.VehicleUnit` (Physical Vehicle)
- Represents an **actual physical vehicle** with a plate number
- Separates "what you see" (Vehicle listing) from "what's available" (actual units)
- Fields: `plate_number` (unique), `status` (available/reserved/booked/active_rental/maintenance/inactive), `mileage`, `notes`

### `vehicles.VehicleImage`
- Multiple images per vehicle, with `is_primary` flag

### `bookings.Booking`
- The core transaction model with **10 statuses**: `draft`, `pending_approval`, `approved`, `awaiting_payment`, `confirmed`, `waiting_for_pickup`, `active`, `completed`, `cancelled`, `rejected`
- Fields: `booking_number` (BK-XXXXXXXX), `pickup_date`, `return_date`, `pickup_time`, `return_time`, `rental_days` (auto-calculated), `subtotal`, `estimated_total`, `handover_time`, `special_request`, `rejection_reason`, `cancellation_reason`
- **Identity snapshot**: `identity_snapshot` (JSONField) — immutable copy of customer's identity at booking time
- Links to `customer` (User), `vehicle` (Vehicle), `vehicle_unit` (VehicleUnit)

### `payments.Invoice`
- One-to-one with `Booking`
- Fields: `invoice_number`, `subtotal`, `additional_charges`, `discount`, `total` (auto-calculated), `invoice_status` (pending/paid/overdue/cancelled), `due_date`

### `payments.Payment`
- Fields: `payment_number`, `provider` (disabled/paymongo), `provider_reference`, `checkout_url`, `currency` (PHP), `amount`, `payment_method`, `payment_status` (pending/paid/failed/cancelled/expired/refunded), `paid_at`, `raw_payload`
- Links to `Booking` and `Invoice`

---

## 5. Key Features & Workflows

### 🔐 Authentication & User Management
- **Email-based registration** with email verification (HTML emails with `TimestampSigner` tokens)
- **JWT authentication** with access token (60 min default) and refresh token (7 days), automatic refresh in the Axios interceptor
- **Password reset** flow (5-minute token expiry)
- **Logout** with token blacklisting
- **Profile management** with identity document upload (driver's license front/back images)
- **Identity locking**: Identity documents cannot be modified while a booking is active. Unlocks when all bookings reach final status (completed/cancelled/rejected)

### 🚙 Vehicle Management (Admin)
- Full **CRUD for vehicle listings** (Vehicle model) with image upload
- **Vehicle Unit management** — add/edit/delete individual units per listing
- Each unit tracked by plate number with per-unit status
- **Availability** calculated from VehicleUnits, not the listing status

### 📅 Booking System
The booking workflow is the heart of the system:

1. **Browse** → Customer browses vehicle listings (with availability indicators)
2. **View Details** → Sees full vehicle info, images, specs, price
3. **Book Now** → Opens dedicated booking page (`/vehicles/:id/book`)
4. **Select Dates** → Date range picker with availability checking via `GET /api/bookings/availability/`
5. **Price Calculation** → Real-time: rental days × daily rate = estimated total
6. **Validation** → Must be logged in, email verified, have driver's license uploaded
7. **Submit** → `POST /api/bookings` — creates booking with status `pending_approval`, captures identity snapshot
8. **Admin Review** → Approve or reject with reason
9. **Payment** → If approved, invoice generated → customer clicks "Pay Now" → PayMongo checkout (when configured)
10. **Confirmation** → Payment verified via webhook → status → `confirmed`
11. **Pickup** → Admin marks `waiting_for_pickup` → then `active` (handover time recorded)
12. **Return** → Vehicle inspection → late fees if needed → mark `completed`

### 💳 Payment Integration (PayMongo)
- **Never stores** sensitive payment credentials (CC numbers, CVV, GCash PIN)
- Creates a PayMongo Checkout Session, redirects customer to PayMongo's secure page
- Webhook endpoint for automatic payment verification
- Supports sandbox (test) and live environments
- Current state: scaffolding complete, provider activation is configuration-only

### 📧 Email Notifications
- Verification email on registration
- Booking submitted confirmation
- Booking approved (with payment link)
- Booking rejected (with reason)
- Booking confirmed (payment received)
- Password reset emails
- All emails use HTML + plain text with responsive templates

### 📊 Dashboards
- **Customer dashboard** (`/dashboard`): view booking history, status, payments
- **Admin dashboard** (`/admin/dashboard`): manage all bookings, vehicles, customers

### 🛡️ Security Features
- Environment variables via `.env` (secrets never hardcoded)
- Production settings: SSL redirect, HSTS, secure cookies, content type nosniff, X-Frame-Options DENY
- CSRF trusted origins configurable
- Rate limiting (1000 req/min anon, 2000 req/min authenticated)
- Identity snapshot preserves audit trail for every booking
- `on_delete=PROTECT` on critical FKs (can't accidentally delete customer with bookings)

---

## 6. Frontend Routes & Views

| Route | View | Auth Required |
|-------|------|:---:|
| `/` | HomeView | No |
| `/vehicles` | VehicleListView | No |
| `/vehicles/:id` | VehicleDetailView | No |
| `/vehicles/:id/book` | BookingView | Yes |
| `/login` | LoginView | Guest only |
| `/register` | RegisterView | Guest only |
| `/forgot-password` | ForgotPasswordView | Guest only |
| `/reset-password/:uid/:token` | ResetPasswordView | No |
| `/verify-email/:uid/:token` | VerifyEmailView | No |
| `/profile` | ProfileView | Yes |
| `/dashboard` | CustomerDashboardView | Yes |
| `/transactions/:id` | TransactionView | Yes |
| `/notifications` | NotificationsView | Yes |
| `/admin/login` | AdminLoginView | Guest only |
| `/admin/dashboard` | AdminDashboardView | Yes |
| `/admin/vehicles` | AdminVehiclesView | Yes |
| `/admin/vehicles/:id` | AdminVehicleDetailView | Yes |
| `/admin/transactions/:id` | AdminTransactionView | Yes |

Staff users are restricted to admin pages (auto-redirected).

---

## 7. API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health/` | GET | Health check |
| `/api/auth/register/` | POST | Register user |
| `/api/auth/login/` | POST | Login (returns JWT + user) |
| `/api/auth/token/refresh/` | POST | Refresh JWT |
| `/api/auth/logout/` | POST | Logout (blacklist token) |
| `/api/auth/verify-email/` | POST | Verify email |
| `/api/auth/resend-verification/` | POST | Resend verification |
| `/api/auth/me/` | GET | Current user profile |
| `/api/auth/reset-password/` | POST | Request password reset |
| `/api/auth/reset-password/confirm/` | POST | Confirm password reset |
| `/api/identity-documents/` | GET/POST | List/upload identity docs |
| `/api/identity-documents/:pk/` | GET/PUT | Get/update identity doc |
| `/api/notifications/` | GET | User notifications |
| `/api/vehicles/` | GET/POST | List/create vehicles |
| `/api/vehicles/:id/` | GET/PUT/DELETE | Vehicle detail |
| `/api/vehicles/:id/images/` | CRUD | Vehicle images |
| `/api/vehicles/:id/units/` | CRUD | Vehicle units |
| `/api/bookings/` | GET/POST | List/create bookings |
| `/api/bookings/:id/` | GET | Booking detail |
| `/api/bookings/:id/approve/` | POST | Admin: approve booking |
| `/api/bookings/:id/reject/` | POST | Admin: reject booking |
| `/api/bookings/:id/cancel/` | POST | Customer: cancel booking |
| `/api/bookings/:id/confirm/` | POST | Admin: confirm payment |
| `/api/bookings/:id/mark-waiting/` | POST | Admin: mark waiting for pickup |
| `/api/bookings/:id/mark-active/` | POST | Admin: mark active rental |
| `/api/bookings/availability/` | GET | Check availability |
| `/api/dashboard/customer/` | GET | Customer dashboard data |
| `/api/dashboard/admin/` | GET | Admin dashboard data |
| `/api/payments/create-session/` | POST | Create payment checkout |
| `/api/payments/:pk/` | GET | Payment detail |
| `/api/payments/webhook/` | POST | PayMongo webhook |

---

## 8. Project Status (Phase 4 - Booking System Codex)

Based on the repository memory and code analysis:

- ✅ Backend models, serializers, views, URLs complete for all 5 apps
- ✅ JWT auth with refresh + blacklisting
- ✅ Email system with HTML templates
- ✅ Vehicle listing + unit management (with seed data command for 18 vehicles)
- ✅ Booking CRUD with full status workflow
- ✅ Identity document management with snapshot/locking
- ✅ Payment scaffolding with PayMongo provider interface
- ✅ Frontend routing with 17 routes and auth guards
- ✅ Axios interceptor with automatic JWT refresh
- ✅ Pinia auth store
- ✅ Frontend build passes (`vue-tsc --build && vite build`)
- ✅ Backend tests pass (57 tests)
- ⏳ PayMongo live integration (scaffolding ready, configuration-only)
- ⏳ Rescheduling, extensions, late fees (defined in spec, may be future phases)

---

## 9. Design Patterns & Conventions

- **MVC architecture**: Models (Django ORM), Views (DRF ViewSets/APIViews), Controllers merged in views
- **Model-Unit separation** (Vehicle vs VehicleUnit): Clean inventory management
- **Immutable snapshots**: Identity data captured at booking time, never modified retroactively
- **Transaction atomicity**: Critical operations (booking creation, approval, payment) wrapped in `transaction.atomic()`
- **Composition API**: All Vue components use `<script setup>` with TypeScript
- **Centralized configuration**: All settings in settings.py via env vars, no scattered config
- **DRY**: Shared email helper, shared identity snapshot builder, shared availability finder

The project follows the principles in AGENTS.md well — modular, clean, secure, with proper separation of concerns.