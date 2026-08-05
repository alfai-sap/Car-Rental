# Car Rental Management System

> **Software Requirements Specification (SRS)**
>
> **Version:** 1.0
>
> **Status:** MVP
>
> **Project Type:** Web Application
>
> **Last Updated:** August 2026

---

# Table of Contents

1. Project Overview
2. Project Vision
3. Project Goals
4. Target Users
5. Technology Stack
6. System Architecture
7. Design Philosophy
8. Core Features (MVP)
9. Functional Modules Overview
10. Database Overview
11. API Overview
12. Security Overview
13. Development Roadmap
14. Future Expansion

---

# 1. Project Overview

## Introduction

The Car Rental Management System is a modern web application designed to digitize and simplify the complete vehicle rental process for both customers and business owners.

Customers can browse available vehicles, create an account, reserve vehicles, complete online payments, and manage their rentals through an intuitive and responsive interface.

Administrators manage the entire rental operation through a centralized dashboard where they can oversee vehicles, bookings, payments, customers, and business settings.

The application is designed to provide a professional, secure, scalable, and user-friendly experience while serving as a long-term platform capable of supporting future business growth.

---

## Purpose

The primary objective of this project is to replace manual rental processes with a centralized digital platform that improves operational efficiency and customer experience.

The MVP focuses on validating the complete rental workflow while establishing an architecture that supports future expansion without requiring major redesign.

---

## Scope

The MVP includes every feature necessary to complete an end-to-end vehicle rental process.

Customers will be able to:

- Register an account
- Login securely
- Browse available vehicles
- Search and filter vehicles
- View vehicle information
- Reserve vehicles
- Complete online payments
- View booking history
- Manage personal information

Administrators will be able to:

- Manage vehicles
- Manage bookings
- Manage customers
- Manage payments
- Configure business settings
- View reports

Features such as loyalty programs, multi-branch support, fleet maintenance, analytics, and native mobile applications are intentionally excluded from the MVP and reserved for future releases.

---

# 2. Project Vision

The objective is not simply to build a booking website.

The long-term vision is to develop a scalable vehicle rental platform capable of supporting growing businesses through modular architecture and modern software engineering practices.

Future versions may include:

- Progressive Web App (PWA)
- Native mobile applications
- Multi-branch operations
- Fleet maintenance
- Driver management
- Dynamic pricing
- Customer loyalty programs
- GPS tracking
- Advanced analytics
- Third-party integrations

The system architecture should support these future enhancements without requiring major structural changes.

---

# 3. Project Goals

## Business Goals

- Digitize the rental process
- Reduce manual administrative work
- Improve customer experience
- Increase booking efficiency
- Provide real-time rental information
- Centralize business management

---

## Technical Goals

The application should be:

- Secure
- Scalable
- Responsive
- Maintainable
- Modular
- High performance
- API-driven
- Easy to extend

---

## User Experience Goals

The application should prioritize:

- Simplicity
- Speed
- Accessibility
- Professional appearance
- Ease of navigation
- Minimal learning curve

---

# 4. Target Users

The application supports four primary user groups.

## Guest

Visitors who browse available vehicles before creating an account.

Primary actions:

- Browse vehicles
- Search vehicles
- View pricing
- Register
- Login

---

## Customer

Registered users who rent vehicles.

Primary actions:

- Manage profile
- Book vehicles
- Complete payments
- View booking history
- Cancel bookings

---

## Administrator

Staff responsible for daily operations.

Primary actions:

- Vehicle management
- Booking management
- Customer management
- Payment management
- Business configuration

---

## Business Owner

Responsible for monitoring overall business performance.

Primary actions:

- Revenue monitoring
- Business reports
- Fleet utilization
- Operational oversight

---

# 5. Technology Stack

## Frontend

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Axios
- Tailwind CSS
- shadcn-vue (always use, to avoid hardcoding reusable components and maintain consistency. implement this first before deciding to create component.)
- Lucide Vue

STRICTLY NO INERTIA js the Website is a standard SPA
---

## Backend

- Django
- Django REST Framework
- JWT Authentication (Simple JWT)

---

## Database

- PostgreSQL

---

## Payments

### MVP

- PayMongo

### Future

- Stripe

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

# 6. System Architecture

The project follows a decoupled client-server architecture.

```text
Client (Browser / Future PWA)

        │

        ▼

Vue 3 Application

(TypeScript)

Vue Router

Pinia

Axios

Tailwind CSS

shadcn-vue

        │

        ▼

REST API

        │

        ▼

Django REST Framework

        │

Business Logic

        │

        ▼

PostgreSQL
```

The frontend and backend communicate exclusively through RESTful APIs, allowing each application to evolve independently while maintaining a clear separation of concerns.

---

# 7. Design Philosophy

The project follows a minimalist and professional design philosophy.

Core principles include:

- Function over decoration
- Minimalist interface
- Consistent layouts
- Responsive design
- Accessible interactions
- Professional aesthetics
- High usability
- Fast user workflows

The interface intentionally avoids unnecessary gradients, decorative shadows, excessive animations, and visual clutter.

Every component should exist because it serves a functional purpose.

---

# 8. Core Features (MVP)

The MVP focuses on delivering a complete rental workflow.

Core capabilities include:

- User Authentication
- Customer Profiles
- Vehicle Catalog
- Vehicle Search & Filtering
- Booking Management
- Online Payments
- Customer Dashboard
- Administrator Dashboard
- Business Settings
- Reporting

---

# 9. Functional Modules Overview

The application is divided into independent modules to improve maintainability and future scalability.

The major modules include:

- Authentication Module
- Customer Module
- Vehicle Management Module
- Booking Module
- Payment Module
- Dashboard Module
- Reports Module
- Business Settings Module

Each module is designed to operate independently while integrating seamlessly through the backend API.

---

# 10. Database Overview

The application uses PostgreSQL as its primary relational database.

Core entities include:

- Users
- Roles
- Customer Profiles
- Vehicles
- Vehicle Images
- Bookings
- Payments
- Business Settings

The database schema follows normalization principles to reduce redundancy while maintaining efficient query performance.

---

# 11. API Overview

The frontend communicates with the backend exclusively through RESTful APIs provided by Django REST Framework.

The API follows standard REST conventions, including:

- Authentication endpoints
- Customer endpoints
- Vehicle endpoints
- Booking endpoints
- Payment endpoints
- Reporting endpoints
- Settings endpoints

JWT authentication secures all protected endpoints.

---

# 12. Security Overview

Security is treated as a primary project requirement.

The system incorporates:

- JWT Authentication
- Password hashing
- HTTPS
- Role-based authorization
- Server-side validation
- SQL injection protection
- XSS protection
- Secure file handling
- Rate limiting (Future)

---

# 13. Development Roadmap

The project will be developed incrementally.

Development phases include:

1. Project Foundation
2. Authentication
3. Vehicle Management
4. Booking System
5. Payment Integration
6. Customer Dashboard
7. Administrator Dashboard
8. Reports
9. Deployment
10. Production Optimization

Each phase builds upon the previous one while maintaining a deployable application.

---

# 14. Future Expansion

The project architecture is intentionally designed for long-term scalability.

Future enhancements may include:

- Progressive Web App (PWA)
- Native Android Application
- Native iOS Application
- Multi-branch Support
- Fleet Maintenance
- Driver Assignment
- Dynamic Pricing
- Promotions
- Customer Loyalty Program
- Push Notifications
- SMS Notifications
- Email Notifications
- Cloud Storage
- GPS Tracking
- AI-powered Recommendations
- Advanced Analytics
- Redis Caching
- Celery Background Processing

---

# Summary

The Car Rental Management System is a scalable, API-driven rental management platform designed with modern software architecture and long-term maintainability in mind.

The MVP delivers a complete end-to-end rental experience while providing a strong foundation for future business growth, additional services, and enterprise-level functionality.