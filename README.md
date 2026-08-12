# Car Rental Management System

A full-stack car rental management platform built with **Vue 3 + Django REST Framework + PostgreSQL**.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Tailwind CSS, shadcn-vue |
| Backend | Django 4.2, Django REST Framework |
| Auth | JWT (Simple JWT) |
| Database | PostgreSQL |
| Payments | PayMongo (MVP) |

## Project Structure

```
Car-Rental/
├── backend/          # Django REST API
│   ├── config/       # Project settings
│   ├── apps/         # Django applications
│   │   ├── core/     # Shared utilities
│   │   ├── accounts/ # Authentication
│   │   ├── vehicles/ # Vehicle management
│   │   ├── bookings/ # Booking management
│   │   └── payments/ # Payment integration
│   ├── static/
│   ├── media/
│   └── manage.py
├── frontend/         # Vue 3 SPA
│   ├── src/
│   └── public/
└── docs/             # Project documentation
```

## Getting Started

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # Edit with your database credentials
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

# Seed 18 vehicles with images
```bash
python manage.py seed_vehicles
```
# Clear all and re-seed fresh
```bash
python manage.py seed_vehicles --clear
```
# delete all data, keep schema
python manage.py flush --noinput


# 1. Drop and recreate the database
psql -U postgres -c "DROP DATABASE IF EXISTS car_rental;"
psql -U postgres -c "CREATE DATABASE car_rental;"

# 2. Re-run all migrations
python manage.py migrate

# 3. Seed 18 vehicles with generated images
python manage.py seed_vehicles

# Data-only refresh (keep schema, clear data)
python manage.py shell -c "from apps.bookings.models import Booking; from apps.payments.models import Payment; Payment.objects.all().delete(); Booking.objects.all().delete()"
python manage.py seed_vehicles --clear

# 4. Create admin superuser
python manage.py createsuperuser