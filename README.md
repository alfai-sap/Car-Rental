# Car Rental Management System

A full-stack car rental management platform built with **Vue 3 + Django REST Framework + PostgreSQL**.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Tailwind CSS, shadcn-vue |
| Backend | Django 5.2.17, Django REST Framework |
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

### Prerequisites

Install these before starting:

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Backend runtime |
| PostgreSQL | 15+ | Database |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Frontend package manager |

> **Windows note:** all terminal commands below assume **PowerShell**. For
> macOS/Linux, use `source venv/bin/activate` instead of `venv\Scripts\activate`.

---

### 1. Clone & install backend

```bash
git clone <repo-url>
cd Car-Rental/backend

python -m venv venv
venv\Scripts\activate          # Windows (PowerShell)
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env           # Windows
# cp .env.example .env         # macOS / Linux
```

Edit `.env` and fill in:

- `SECRET_KEY` — generate one with:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` — your
  PostgreSQL credentials (see "Database setup" below).
- `GOOGLE_CLIENT_ID` — only needed for Google Sign-In (optional).

> **Never commit `.env`.** It is already in `.gitignore`.

### 3. Create the database

```bash
psql -U postgres -c "CREATE DATABASE car_rental;"
```

> If you already have a database with an old schema and want a clean start,
> see the **"Database reset & seeding"** section below.

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create an admin superuser

```bash
python manage.py createsuperuser
```

> The prompt asks for an **email** (used for login) and a password.

### 6. Start the backend server

```bash
python manage.py runserver
```

The API runs at <http://127.0.0.1:8000/>. The Django admin is at
<http://127.0.0.1:8000/admin/> (or your custom `ADMIN_URL`).

---

### 7. Install & run the frontend

In a **second** terminal:

```bash
cd Car-Rental/frontend
npm install
npm run dev
```

The SPA runs at <http://localhost:5173/> and proxies `/api` requests to the
backend.

---

### 8. Seed sample data (optional)

Seed 18 demo vehicles (with units and images):

```bash
cd ../backend
python manage.py seed_vehicles
```

> Requires internet access to download Unsplash photos; falls back to
> generated placeholder images if offline.

---

## Database reset & seeding

> ⚠️ **Destructive** — these commands delete data. Use only on a dev/staging
> database.

**Option A — full reset (drop schema + data, then reseed):**

```bash
# 1. Drop and recreate the database (run as the PostgreSQL superuser)
psql -U postgres -c "DROP DATABASE IF EXISTS car_rental;"
psql -U postgres -c "CREATE DATABASE car_rental;"

# 2. Re-run all migrations from scratch
python manage.py migrate

# 3. Recreate the admin account
python manage.py createsuperuser

# 4. Seed 18 vehicles
python manage.py seed_vehicles
```

**Option B — data-only refresh (keep schema, clear data):**

```bash
# Delete all business data but keep tables & migration history
python manage.py flush --noinput

# Re-seed vehicles (replaces any existing vehicles)
python manage.py seed_vehicles --clear

# Recreate the admin account (flush removes all users)
python manage.py createsuperuser
```

> **Note:** after `flush`, all users — including your superuser — are gone.
> Always run `createsuperuser` again after a data-only refresh.

**Seed command reference:**

| Command | Effect |
|---|---|
| `python manage.py seed_vehicles` | Seed 18 vehicles with units & images (skips if vehicles exist) |
| `python manage.py seed_vehicles --clear` | Delete all vehicles, then seed fresh |

---

## Payment integration (PayMongo)

To enable live payments, follow these steps:

1. **Create a PayMongo account** at <https://www.paymongo.com/> and verify it.
2. **Acquire API keys** from the PayMongo dashboard (Developers → API keys):
   - Public key (`pk_...`)
   - Secret key (`sk_...`)
3. **Set the keys in `.env`:**
   ```env
   PAYMENT_PROVIDER=paymongo
   PAYMONGO_PUBLIC_KEY=pk_...
   PAYMONGO_SECRET_KEY=sk_...
   PAYMONGO_WEBHOOK_SECRET=whsk_...   # created in step 6
   ```
4. **Install ngrok** from <https://ngrok.com/> (required for local webhook testing).
5. **Start a tunnel** to your local backend:
   ```bash
   ngrok http 8000
   ```
   Copy the generated HTTPS URL (e.g. `https://abc123.ngrok.io`).
6. **Create a webhook** in PayMongo:
   - Go to Developers → Webhooks → Add webhook.
   - Paste your ngrok URL + `/api/payments/webhook/` as the endpoint URL:
     ```
     https://abc123.ngrok.io/api/payments/webhook/
     ```
   - Select the applicable events (`checkout_session.payment.paid`,
     `payment.paid`, `payment.failed`).
   - Copy the webhook **secret** and put it in `PAYMONGO_WEBHOOK_SECRET`.
7. **Add the ngrok URL to `ALLOWED_HOSTS`** in `.env`:
   ```env
   ALLOWED_HOSTS=127.0.0.1,localhost,abc123.ngrok.io
   ```

> With `PAYMENT_PROVIDER=disabled`, the app works end-to-end but payment is
> simulated. The manual "Confirm Payment" button is gated behind
> `ALLOW_MANUAL_PAYMENT_CONFIRM=True` (dev/test only — keep it `False` in
> production).

---

## Useful development commands

```bash
# Run the test suite
python manage.py test

# Check for pending migrations (should report "No changes detected")
python manage.py makemigrations --check --dry-run

# Show applied migrations per app
python manage.py showmigrations

# Create a database backup (PostgreSQL client tools required)
python manage.py dbbackup

# List existing backups
python manage.py dbbackup --list

# Reconcile pending PayMongo payments against the gateway
python manage.py reconcile_payments
```