# Vehicle Management Module

> Module Version: MVP 1.0

---

# Overview

The Vehicle Management Module separates **Vehicle Models** from **Vehicle Units**.

This architecture allows a single listing (e.g., Toyota Vios 2024) to represent multiple physical vehicles owned by the business.

Benefits:

- Cleaner customer interface
- Easier administration
- Better inventory management
- Scalable fleet management
- Accurate booking availability

---

# Data Structure

The system consists of two main entities.

## Vehicle Model

Represents the vehicle listing displayed to customers.

Example

```text
Toyota Vios

2024

Automatic

₱1,500 / Day
```

Vehicle Model stores:

- Make
- Model
- Year
- Vehicle Type
- Transmission
- Fuel Type
- Seating Capacity
- Daily Rental Price
- Description
- Images
- Features

A Vehicle Model contains one or more Vehicle Units.

---

## Vehicle Unit

Represents an actual physical vehicle.

Example

```text
Toyota Vios

Plate Number

ABC-1234
```

Each Vehicle Unit has its own:

- Plate Number
- Current Status
- Mileage
- Branch (Future)
- Maintenance Status
- Booking History

Customers never browse individual Vehicle Units.

---

# Database Structure

## vehicle_models

| Field | Description |
|--------|-------------|
| id | Primary Key |
| make | Vehicle manufacturer |
| model | Vehicle model |
| year | Manufacturing year |
| type | Sedan, SUV, Van, etc. |
| transmission | Automatic / Manual |
| fuel | Gasoline / Diesel / Hybrid / EV |
| seats | Passenger capacity |
| price_per_day | Daily rental rate |
| description | Listing description |
| created_at | Creation timestamp |
| updated_at | Last update timestamp |

---

## vehicle_units

| Field | Description |
|--------|-------------|
| id | Primary Key |
| vehicle_model_id | Related vehicle model |
| plate_number | Vehicle plate number |
| status | Available, Reserved, Booked, Active Rental, Maintenance |
| mileage | Current mileage *(Optional MVP)* |
| created_at | Creation timestamp |
| updated_at | Last update timestamp |

---

# Customer Experience

Customers only see one listing.

Example

```text
Toyota Vios

Automatic

5 Seats

₱1,500 / Day

Available Units

2

[ Book Now ]
```

Customers never choose a specific plate number.

---

# Vehicle Availability

Availability is calculated from Vehicle Units.

Example

```text
Toyota Vios

Total Units

3

Available

2

Booked

1
```

The listing remains bookable while at least one Vehicle Unit is available.

---

# Admin Workflow

## Vehicle Listings

Vehicle listings represent Vehicle Models.

The owner manages:

- Create Listing
- View Listing
- Edit Listing
- Delete Listing

---

# Create Listing

The owner creates the rental listing once.

Required Information

- Make
- Model
- Year
- Vehicle Type
- Transmission
- Fuel Type
- Seats
- Daily Rental Price
- Description
- Vehicle Images

Example

```text
Make

Toyota

Model

Vios

Year

2024

Transmission

Automatic

Fuel

Gasoline

Seats

5

Daily Rate

₱1,500
```

The listing is now available.

No vehicle units exist yet.

---

# Add Vehicle Units

After creating the listing, the owner adds physical vehicles.

Example

Toyota Vios

↓

Add Vehicle

Vehicle 1

```text
Plate Number

ABC-1234
```

Vehicle 2

```text
Plate Number

XYZ-5678
```

Vehicle 3

```text
Plate Number

DEF-9012
```

Each added unit increases the available inventory.

---

# View Listing

Example

```text
Toyota Vios

2024

Automatic

₱1,500 / Day

Vehicle Units

3

Available

2

Booked

1

[ Manage Units ]
```

---

# Manage Vehicle Units

Selecting **Manage Units** opens the inventory page.

| Plate Number | Status | Action |
|--------------|--------|--------|
| ABC-1234 | Available | Edit |
| XYZ-5678 | Booked | View Booking |
| DEF-9012 | Maintenance | Edit |

Each unit can be managed independently.

---

# Update Listing

Editing a listing updates shared information for every Vehicle Unit.

Editable fields include:

- Daily Rate
- Description
- Images
- Features
- Specifications

Changing the daily rental price automatically applies to all units under the listing.

Vehicle-specific information is not edited here.

---

# Update Vehicle Unit

Each physical vehicle can be updated independently.

Editable fields:

- Plate Number
- Status
- Mileage
- Notes *(Optional)*

Changing one Vehicle Unit does not affect other units.

---

# Delete Listing

A listing can only be deleted when:

- No Vehicle Units exist

OR

- All Vehicle Units are removed

OR

- The owner confirms deletion

Deleting a listing also removes its associated Vehicle Units.

Deletion should be blocked if active bookings exist.

---

# Vehicle Status

Each Vehicle Unit has its own status.

Available

Vehicle can accept bookings.

Reserved

Approved booking awaiting payment.

Booked

Booking confirmed.

Active Rental

Currently rented.

Maintenance

Unavailable due to maintenance or repair.

Inactive

Temporarily removed from service.

---

# Booking Assignment

Customers book the Vehicle Model.

Example

```text
Toyota Vios

Aug 10 → Aug 12
```

The system checks every Vehicle Unit.

If at least one unit is available:

Booking is accepted.

The specific Vehicle Unit is assigned by the owner before vehicle pickup or automatically by the system from the available inventory.

---

# Availability Rules

Customer Calendar

- No indicator = Vehicle available.
- Red dot = No available units for the selected date.

Pending booking requests do not reduce availability.

Only:

- Reserved
- Booked
- Active Rental

affect the availability calculation.

---

One additional recommendation

Instead of having a generic status in your current vehicles table, move it to vehicle_units. The listing itself rarely needs a status. The availability should be derived from its units.

For example:

Toyota Vios
├── ABC-1234 (Available)
├── XYZ-5678 (Booked)
├── DEF-9012 (Maintenance)

The listing automatically displays:

Available Units: 1 of 3

# Future Expansion

The architecture supports future features without major database changes.

Possible additions include:

- Multiple branches
- Vehicle mileage tracking
- Vehicle maintenance history
- Insurance information
- VIN/Engine number
- QR code check-in
- GPS tracking
- Automatic vehicle assignment
- Fleet analytics
- Vehicle documents

