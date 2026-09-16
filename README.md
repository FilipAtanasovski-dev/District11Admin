# District 11 Brunch Bar & Restaurant

A full-stack restaurant website and management system developed for **District 11 Brunch Bar & Restaurant**, a restaurant in Belgrade, Serbia.

The system is actively being developed and will soon be deployed in a real business setting to support online reservations and internal restaurant operations.

## Overview

The project combines a customer-facing restaurant website with a FastAPI backend and an administrative system for managing reservations, tables, floor plans, and newsletter subscribers.

### Key Features

* Online table reservations
* Automatic table allocation
* Reservation and availability management
* Interactive restaurant floor plan
* Table management
* Admin and employee functionality
* Customer management
* Newsletter subscriber management
* Email notifications and newsletters
* REST API with interactive documentation

## Tech Stack

**Backend**

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Pydantic

**Frontend**

* HTML
* CSS
* JavaScript
* Bootstrap
* Jinja2

**Infrastructure & Services**

* Supabase
* SMTP
* Uvicorn

## System Architecture

```text
                    ┌─────────────────────┐
                    │   Restaurant Website │
                    │   Customer Interface │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │       Backend       │
                    └──────┬────────┬─────┘
                           │        │
                    ┌──────▼───┐  ┌─▼──────┐
                    │PostgreSQL│  │  SMTP  │
                    │ Supabase │  │ Emails  │
                    └──────────┘  └────────┘
```

## Reservation Management

The backend handles the complete reservation workflow, including availability checking and table allocation.

Reservations are associated with specific tables and time periods, allowing the system to prevent conflicting bookings and manage restaurant capacity.

## Floor Plan Management

The administrative system includes an interactive floor plan for managing restaurant tables and other objects.

Administrators can add, update, and remove tables while keeping the floor plan synchronized with the underlying database.

## Database

The application uses PostgreSQL with SQLAlchemy as the ORM.

The main entities include:

* Restaurants
* Tables
* Floor plan objects
* Customers
* Reservations
* Reservation-table relationships
* Newsletter subscribers

## API

The backend exposes REST endpoints for the main application functionality, including:

* Reservations
* Tables
* Restaurants
* Customers
* Floor plans
* Authentication
* Newsletter management

FastAPI also provides interactive API documentation for development and testing.

## Running Locally

### Requirements

* Python 3.13+
* PostgreSQL database

### Installation

```bash
git clone <repository-url>
cd <repository-folder>

python -m venv venv
```

Windows:

```powershell
venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file containing the required database, authentication, and SMTP configuration.

Start the development server:

run the start_server.bat batch file.

The API documentation is then available at:

```text
*displayed_ip_adress_and_port*/docs
```

## Security

Production credentials and sensitive configuration are kept outside the repository using environment variables.

A public deployment should never contain real database credentials, administrator passwords, SMTP credentials, or customer data.

## Project

This project was developed as a real-world software engineering system for a restaurant, covering both customer-facing functionality and internal business operations.

It is also part of my software engineering portfolio, demonstrating experience designing and implementing a complete application from the frontend through the backend and database.
