
import os
import smtplib
import secrets

from datetime import datetime, timedelta
from email.message import EmailMessage
from itertools import combinations

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Depends,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

from sqlalchemy import (
    create_engine,
    Column,
    BigInteger,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    select,
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session,
)

from starlette.middleware.sessions import SessionMiddleware


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "admin",
)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

SECRET_KEY = os.getenv("SECRET_KEY")

SMTP_HOST = os.getenv("SMTP_HOST")

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587",
    )
)

SMTP_USERNAME = os.getenv("SMTP_USERNAME")

SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

EMAIL_FROM = os.getenv("EMAIL_FROM")


# ============================================================
# VALIDATE CONFIGURATION
# ============================================================

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured"
    )

if not ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_PASSWORD is not configured"
    )

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not configured"
    )


# ============================================================
# IMPORTANT:
# NO TIMEZONES ARE USED IN THIS APPLICATION.
#
# All dates/times are treated as plain local restaurant time.
#
# Example:
#
# 2026-08-15 23:00
#
# simply means:
#
# August 15, 2026 at 23:00.
# ============================================================


# ============================================================
# DATETIME HELPERS
# ============================================================

def parse_local_datetime(
    date_string: str,
    time_string: str,
):
    """
    Parse a frontend date/time into a NAIVE datetime.

    No timezone conversion is performed.
    """

    try:
        return datetime.strptime(
            f"{date_string} {time_string}",
            "%Y-%m-%d %H:%M",
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid date or time. "
                "Use YYYY-MM-DD and HH:MM."
            ),
        )


def normalize_datetime(value):
    """
    Convert any datetime coming from the database
    into a naive datetime.

    If the database happens to return a timezone-aware
    datetime, the timezone information is simply removed.

    IMPORTANT:
    We do NOT convert the clock time.

    23:00 stays 23:00.
    """

    if value is None:
        return None

    if value.tzinfo is not None:
        return value.replace(
            tzinfo=None
        )

    return value


def local_datetime_response(value):

    value = normalize_datetime(value)

    if value is None:
        return None

    return {
        "iso":
            value.strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),

        "date":
            value.strftime(
                "%Y-%m-%d"
            ),

        "time":
            value.strftime(
                "%H:%M"
            ),

        "display_date":
            value.strftime(
                "%d.%m.%Y"
            ),

        "display_time":
            value.strftime(
                "%H:%M"
            ),
    }


def now_local():
    """
    Return the current server/application time
    as a naive datetime.

    No timezone handling whatsoever.
    """

    return datetime.now()


# ============================================================
# DATABASE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


# ============================================================
# MODELS
# ============================================================

class Restaurant(Base):

    __tablename__ = "restaurants"

    id = Column(
        BigInteger,
        primary_key=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    address = Column(Text)

    timezone = Column(
        String,
        nullable=False,
    )


class RestaurantTable(Base):

    __tablename__ = "restaurant_tables"

    id = Column(
        BigInteger,
        primary_key=True,
    )

    restaurant_id = Column(
        BigInteger,
        ForeignKey("restaurants.id"),
        nullable=False,
    )

    table_number = Column(
        Integer,
        nullable=False,
    )

    capacity = Column(
        Integer,
        nullable=False,
    )

    active = Column(
        Boolean,
        nullable=False,
    )


class Customer(Base):

    __tablename__ = "customers"

    id = Column(
        BigInteger,
        primary_key=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    email = Column(String)

    phone = Column(String)

    created_at = Column(
        DateTime,
        nullable=False,
    )


class Reservation(Base):

    __tablename__ = "reservations"

    id = Column(
        BigInteger,
        primary_key=True,
    )

    restaurant_id = Column(
        BigInteger,
        ForeignKey("restaurants.id"),
        nullable=False,
    )

    customer_id = Column(
        BigInteger,
        ForeignKey("customers.id"),
        nullable=False,
    )

    start_at = Column(
        DateTime,
        nullable=False,
    )

    end_at = Column(
        DateTime,
        nullable=False,
    )

    party_size = Column(
        Integer,
        nullable=False,
    )

    status = Column(
        String,
        nullable=False,
    )

    confirmation_code = Column(
        String,
        unique=True,
    )

    notes = Column(Text)

    created_at = Column(
        DateTime,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
    )


class ReservationTable(Base):

    __tablename__ = "reservation_tables"

    reservation_id = Column(
        BigInteger,
        ForeignKey("reservations.id"),
        primary_key=True,
    )

    table_id = Column(
        BigInteger,
        ForeignKey("restaurant_tables.id"),
        primary_key=True,
    )


class NewsletterSubscriber(Base):

    __tablename__ = "newsletter_subscribers"

    id = Column(
        BigInteger,
        primary_key=True,
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
    )

    active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    subscribed_at = Column(
        DateTime,
        nullable=False,
    )


# ============================================================
# REQUEST MODELS
# ============================================================

class EmployeeReservationRequest(BaseModel):

    restaurant_name: str = Field(
        min_length=1
    )

    customer_name: str = Field(
        min_length=1,
        max_length=200
    )

    customer_email: str | None = None

    customer_phone: str | None = None

    date: str = Field(
        min_length=10,
        max_length=10
    )

    time: str = Field(
        min_length=5,
        max_length=5
    )

    party_size: int = Field(
        gt=0
    )

    duration_minutes: int = Field(
        default=120,
        gt=0,
        le=1440
    )

    notes: str | None = None


class LoginRequest(BaseModel):

    username: str

    password: str


class AddTableRequest(BaseModel):

    restaurant_name: str = Field(
        min_length=1
    )

    table_number: int = Field(
        gt=0
    )

    capacity: int = Field(
        gt=0
    )


class NewsletterRequest(BaseModel):

    subject: str = Field(
        min_length=1,
        max_length=200,
    )

    message: str = Field(
        min_length=1,
    )


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Restaurant Management API",
    version="1.2.0",
)


# ============================================================
# SESSION
# ============================================================

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="restaurant_admin_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=False,
)


# ============================================================
# STATIC FILES / TEMPLATES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# AUTHENTICATION
# ============================================================

def require_admin(
    request: Request,
):

    if not request.session.get(
        "admin_authenticated"
    ):

        raise HTTPException(
            status_code=401,
            detail="Admin authentication required",
        )

    return True


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status":
            "online",

        "service":
            "Restaurant Management API",

        "timezone":
            "none",

        "current_server_time":
            now_local().isoformat(),
    }


# ============================================================
# FRONTEND ROUTES
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
def home(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get(
    "/employee",
    response_class=HTMLResponse,
)
def employee(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="employee.html",
    )


@app.get(
    "/admin/login",
    response_class=HTMLResponse,
)
def admin_login_page(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
    )


@app.get(
    "/admin",
    response_class=HTMLResponse,
)
def admin_dashboard(
    request: Request,
):

    if not request.session.get(
        "admin_authenticated"
    ):

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.post("/api/admin/login")
def admin_login(
    login: LoginRequest,
    request: Request,
):

    if (
        login.username != ADMIN_USERNAME
        or login.password != ADMIN_PASSWORD
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    request.session[
        "admin_authenticated"
    ] = True

    return {
        "status":
            "success",

        "message":
            "Login successful",
    }


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.post("/api/admin/logout")
def admin_logout(
    request: Request,
):

    request.session.clear()

    return {
        "status":
            "logged_out"
    }


# ============================================================
# GET RESERVATIONS
# ============================================================

@app.get("/api/reservations")
def get_reservations(

    request: Request,

    date: str | None = None,

    status_filter: str | None = None,

    status: str | None = None,

    db: Session = Depends(get_db),


):

    start_date = None
    end_date = None

    if date:

        try:

            requested_date = datetime.strptime(
                date,
                "%Y-%m-%d",
            ).date()

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid date. "
                    "Use YYYY-MM-DD."
                ),
            )

        start_date = datetime.combine(
            requested_date,
            datetime.min.time(),
        )

        end_date = datetime.combine(
            requested_date,
            datetime.max.time(),
        )

    query = (
        select(
            Reservation,
            Customer,
            Restaurant,
        )
        .join(
            Customer,
            Customer.id
            == Reservation.customer_id,
        )
        .join(
            Restaurant,
            Restaurant.id
            == Reservation.restaurant_id,
        )
    )

    if start_date:

        query = query.where(

            Reservation.start_at
            <= end_date,

            Reservation.end_at
            >= start_date,

        )

    selected_status = (
        status
        or status_filter
    )

    if (
        selected_status
        and selected_status != "all"
    ):

        query = query.where(
            Reservation.status
            == selected_status
        )

    query = query.order_by(
        Reservation.start_at.asc()
    )

    rows = db.execute(
        query
    ).all()

    result = []

    for (
        reservation,
        customer,
        restaurant,
    ) in rows:

        table_query = (
            select(RestaurantTable)
            .join(
                ReservationTable,
                ReservationTable.table_id
                == RestaurantTable.id,
            )
            .where(
                ReservationTable.reservation_id
                == reservation.id
            )
            .order_by(
                RestaurantTable.table_number
            )
        )

        tables = (
            db.execute(table_query)
            .scalars()
            .all()
        )

        start_info = local_datetime_response(
            reservation.start_at
        )

        end_info = local_datetime_response(
            reservation.end_at
        )

        result.append(
            {
                "id":
                    reservation.id,

                "restaurant":
                    restaurant.name,

                "start_at":
                    start_info["iso"],

                "start_date":
                    start_info["date"],

                "start_time":
                    start_info["time"],

                "start_display_date":
                    start_info["display_date"],

                "start_display_time":
                    start_info["display_time"],

                "end_at":
                    end_info["iso"],

                "end_date":
                    end_info["date"],

                "end_time":
                    end_info["time"],

                "end_display_date":
                    end_info["display_date"],

                "end_display_time":
                    end_info["display_time"],

                "party_size":
                    reservation.party_size,

                "status":
                    reservation.status,

                "confirmation_code":
                    reservation.confirmation_code,

                "notes":
                    reservation.notes,

                "customer": {

                    "id":
                        customer.id,

                    "name":
                        customer.name,

                    "email":
                        customer.email,

                    "phone":
                        customer.phone,

                },

                "tables": [

                    {

                        "id":
                            table.id,

                        "table_number":
                            table.table_number,

                        "capacity":
                            table.capacity,

                    }

                    for table in tables

                ],

            }
        )

    return {

        "reservations":
            result,

        "count":
            len(result),

    }


# ============================================================
# CANCEL RESERVATION
# ============================================================

@app.post(
    "/api/admin/reservations/{reservation_id}/cancel"
)
def cancel_reservation(

    reservation_id: int,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    reservation = db.get(
        Reservation,
        reservation_id,
    )

    if reservation is None:

        raise HTTPException(
            status_code=404,
            detail="Reservation not found",
        )

    if reservation.status == "cancelled":

        return {
            "status":
                "cancelled",

            "reservation_id":
                reservation.id,

            "message":
                "Reservation was already cancelled.",
        }

    reservation.status = "cancelled"

    reservation.updated_at = now_local()

    db.commit()

    return {

        "status":
            "cancelled",

        "reservation_id":
            reservation.id,

        "confirmation_code":
            reservation.confirmation_code,

        "message":
            "Reservation cancelled successfully.",

    }


# ============================================================
# GET TABLES
# ============================================================

@app.get("/api/tables")
def get_tables(

    request: Request,

    date: str | None = None,

    db: Session = Depends(get_db),



):

    tables = db.execute(

        select(
            RestaurantTable,
            Restaurant,
        )

        .join(
            Restaurant,
            Restaurant.id
            == RestaurantTable.restaurant_id,
        )

        .where(
            RestaurantTable.active.is_(True)
        )

        .order_by(
            Restaurant.name,
            RestaurantTable.table_number,
        )

    ).all()

    result = []

    now = now_local()

    for table, restaurant in tables:

        occupied = False
        occupied_until = None

        reservation_query = (

            select(Reservation)

            .join(
                ReservationTable,
                ReservationTable.reservation_id
                == Reservation.id,
            )

            .where(

                ReservationTable.table_id
                == table.id,

                Reservation.status.in_(
                    [
                        "pending",
                        "confirmed",
                    ]
                ),

                Reservation.start_at <= now,

                Reservation.end_at > now,

            )

            .order_by(
                Reservation.start_at.asc()
            )
        )

        reservation = (
            db.execute(
                reservation_query
            )
            .scalars()
            .first()
        )

        if reservation:

            occupied = True

            occupied_until = reservation.end_at
            

        result.append(
            {
                "id":
                    table.id,

                "restaurant":
                    restaurant.name,

                "table_number":
                    table.table_number,

                "capacity":
                    table.capacity,

                "active":
                    table.active,

                "occupied":
                    occupied,

                "occupied_until":
                    occupied_until,
            }
        )

    return {

        "tables":
            result,

        "count":
            len(result),

    }


# ============================================================
# FIND AVAILABLE TABLES
#
# THIS IS THE SINGLE SOURCE OF TRUTH FOR AVAILABILITY.
#
# Both:
#   /reservation-availability
#
# and:
#   /reservations
#
# use this exact function.
# ============================================================

def find_available_tables(

    db: Session,

    restaurant_id: int,

    start_at: datetime,

    end_at: datetime,

    party_size: int,

):

    # --------------------------------------------------------
    # Get active tables
    # --------------------------------------------------------

    tables = db.execute(

        select(RestaurantTable)

        .where(

            RestaurantTable.restaurant_id
            == restaurant_id,

            RestaurantTable.active.is_(True),

        )

        .order_by(
            RestaurantTable.capacity.asc()
        )

    ).scalars().all()

    if not tables:

        return {
            "available":
                False,

            "reason":
                "There are no active tables at this restaurant.",

            "available_tables":
                [],

            "selected_tables":
                [],

            "available_capacity":
                0,
        }

    # --------------------------------------------------------
    # Find reservations that overlap.
    #
    # IMPORTANT:
    #
    # Reservation A:
    #     21:00 -> 23:00
    #
    # Requested:
    #     23:00 -> 01:00
    #
    # These DO NOT overlap.
    #
    # Because:
    #
    #     existing.start < requested.end
    #
    # AND
    #
    #     existing.end > requested.start
    #
    # At exactly 23:00:
    #
    #     existing.end > requested.start
    #
    # becomes:
    #
    #     23:00 > 23:00
    #
    # which is FALSE.
    #
    # Therefore the table becomes available immediately.
    # --------------------------------------------------------

    overlapping_reservations = db.execute(

        select(
            ReservationTable.table_id
        )

        .join(
            Reservation,
            Reservation.id
            == ReservationTable.reservation_id,
        )

        .where(

            Reservation.restaurant_id
            == restaurant_id,

            Reservation.status.in_(
                [
                    "pending",
                    "confirmed",
                ]
            ),

            Reservation.start_at
            < end_at,

            Reservation.end_at
            > start_at,

        )

    ).scalars().all()

    reserved_table_ids = set(
        overlapping_reservations
    )

    # --------------------------------------------------------
    # Remove occupied tables
    # --------------------------------------------------------

    available_tables = [

        table

        for table in tables

        if table.id
        not in reserved_table_ids

    ]

    # --------------------------------------------------------
    # Find the smallest number of tables that can
    # accommodate the party.
    # --------------------------------------------------------

    best_combination = None
    best_capacity = None

    for number_of_tables in range(
        1,
        len(available_tables) + 1,
    ):

        for combination in combinations(
            available_tables,
            number_of_tables,
        ):

            capacity = sum(
                table.capacity
                for table in combination
            )

            if capacity < party_size:
                continue

            if best_combination is None:

                best_combination = combination
                best_capacity = capacity

                continue

            if (
                len(combination)
                < len(best_combination)
            ):

                best_combination = combination
                best_capacity = capacity

                continue

            if (
                len(combination)
                ==
                len(best_combination)
                and capacity
                < best_capacity
            ):

                best_combination = combination
                best_capacity = capacity

    available_capacity = sum(
        table.capacity
        for table in available_tables
    )

    if best_combination is None:

        return {

            "available":
                False,

            "reason":
                "No tables are available for "
                "this party at the requested time.",

            "available_tables":
                available_tables,

            "selected_tables":
                [],

            "available_capacity":
                available_capacity,

        }

    return {

        "available":
            True,

        "reason":
            "Tables are available.",

        "available_tables":
            available_tables,

        "selected_tables":
            list(best_combination),

        "available_capacity":
            best_capacity,

    }


# ============================================================
# EMPLOYEE - CHECK RESERVATION AVAILABILITY
# ============================================================

@app.get(
    "/api/employee/reservation-availability"
)
def employee_reservation_availability(

    restaurant_name: str,

    date: str,

    time: str,

    party_size: int,

    duration_minutes: int = 120,

    db: Session = Depends(get_db),

):

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if party_size <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Party size must be "
                "greater than 0."
            ),
        )

    if duration_minutes <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Duration must be "
                "greater than 0."
            ),
        )

    # --------------------------------------------------------
    # Find restaurant
    # --------------------------------------------------------

    restaurant = db.execute(

        select(Restaurant)

        .where(
            Restaurant.name.ilike(
                restaurant_name
            )
        )

    ).scalar_one_or_none()

    if restaurant is None:

        raise HTTPException(
            status_code=404,
            detail="Restaurant not found.",
        )

    # --------------------------------------------------------
    # Parse requested time.
    #
    # NO TIMEZONE.
    # --------------------------------------------------------

    start_at = parse_local_datetime(
        date,
        time,
    )

    end_at = (
        start_at
        + timedelta(
            minutes=duration_minutes
        )
    )

    # --------------------------------------------------------
    # Check if the requested time is in the past.
    # --------------------------------------------------------

    if start_at < now_local():

        return {

            "available":
                False,

            "reason":
                "Reservation time cannot be in the past.",

            "available_capacity":
                0,

            "requested_party_size":
                party_size,

            "start_at":
                start_at.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),

            "start_date":
                start_at.strftime(
                    "%Y-%m-%d"
                ),

            "start_time":
                start_at.strftime(
                    "%H:%M"
                ),

            "end_at":
                end_at.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),

            "end_date":
                end_at.strftime(
                    "%Y-%m-%d"
                ),

            "end_time":
                end_at.strftime(
                    "%H:%M"
                ),

            "tables":
                [],

        }

    # --------------------------------------------------------
    # Find tables
    # --------------------------------------------------------

    availability = find_available_tables(

        db=db,

        restaurant_id=restaurant.id,

        start_at=start_at,

        end_at=end_at,

        party_size=party_size,

    )

    selected_tables = (
        availability["selected_tables"]
    )

    # --------------------------------------------------------
    # NOT AVAILABLE
    # --------------------------------------------------------

    if not availability["available"]:

        return {

            "available":
                False,

            "reason":
                availability["reason"],

            "restaurant":
                restaurant.name,

            "available_capacity":
                availability["available_capacity"],

            "requested_party_size":
                party_size,

            "start_at":
                start_at.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),

            "start_date":
                start_at.strftime(
                    "%Y-%m-%d"
                ),

            "start_time":
                start_at.strftime(
                    "%H:%M"
                ),

            "start_display_date":
                start_at.strftime(
                    "%d.%m.%Y"
                ),

            "start_display_time":
                start_at.strftime(
                    "%H:%M"
                ),

            "end_at":
                end_at.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),

            "end_date":
                end_at.strftime(
                    "%Y-%m-%d"
                ),

            "end_time":
                end_at.strftime(
                    "%H:%M"
                ),

            "end_display_date":
                end_at.strftime(
                    "%d.%m.%Y"
                ),

            "end_display_time":
                end_at.strftime(
                    "%H:%M"
                ),

            "tables": [

                {

                    "id":
                        table.id,

                    "table_number":
                        table.table_number,

                    "capacity":
                        table.capacity,

                }

                for table
                in availability["available_tables"]

            ],

        }

    # --------------------------------------------------------
    # AVAILABLE
    # --------------------------------------------------------

    selected_capacity = sum(

        table.capacity

        for table
        in selected_tables

    )

    return {

        "available":
            True,

        "reason":
            "Tables are available.",

        "restaurant":
            restaurant.name,

        "requested_party_size":
            party_size,

        "available_capacity":
            selected_capacity,

        "start_at":
            start_at.strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),

        "start_date":
            start_at.strftime(
                "%Y-%m-%d"
            ),

        "start_time":
            start_at.strftime(
                "%H:%M"
            ),

        "start_display_date":
            start_at.strftime(
                "%d.%m.%Y"
            ),

        "start_display_time":
            start_at.strftime(
                "%H:%M"
            ),

        "end_at":
            end_at.strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),

        "end_date":
            end_at.strftime(
                "%Y-%m-%d"
            ),

        "end_time":
            end_at.strftime(
                "%H:%M"
            ),

        "end_display_date":
            end_at.strftime(
                "%d.%m.%Y"
            ),

        "end_display_time":
            end_at.strftime(
                "%H:%M"
            ),

        "timezone":
            "none",

        "tables": [

            {

                "id":
                    table.id,

                "table_number":
                    table.table_number,

                "capacity":
                    table.capacity,

            }

            for table
            in selected_tables

        ],

    }


# ============================================================
# EMPLOYEE - CREATE RESERVATION
# ============================================================

@app.post(
    "/api/employee/reservations"
)
def employee_create_reservation(

    reservation_request:
        EmployeeReservationRequest,

    db: Session = Depends(
        get_db
    ),

):

    # --------------------------------------------------------
    # Restaurant
    # --------------------------------------------------------

    restaurant = db.execute(

        select(Restaurant)

        .where(
            Restaurant.name.ilike(
                reservation_request.restaurant_name
            )
        )

    ).scalar_one_or_none()

    if restaurant is None:

        raise HTTPException(
            status_code=404,
            detail="Restaurant not found.",
        )

    # --------------------------------------------------------
    # Requested time
    # --------------------------------------------------------

    start_at = parse_local_datetime(

        reservation_request.date,

        reservation_request.time,

    )

    end_at = (

        start_at

        + timedelta(
            minutes=
            reservation_request.duration_minutes
        )

    )

    # --------------------------------------------------------
    # Past reservation
    # --------------------------------------------------------

    if start_at < now_local():

        raise HTTPException(

            status_code=400,

            detail=(
                "Reservation time "
                "cannot be in the past."
            ),

        )

    # --------------------------------------------------------
    # Check availability AGAIN.
    #
    # This is important.
    #
    # Even if the frontend checked availability,
    # another employee/browser could have created a
    # reservation between the availability check and
    # the actual reservation.
    # --------------------------------------------------------

    availability = find_available_tables(

        db=db,

        restaurant_id=restaurant.id,

        start_at=start_at,

        end_at=end_at,

        party_size=
            reservation_request.party_size,

    )

    if not availability["available"]:

        raise HTTPException(

            status_code=409,

            detail=(
                "No tables are available for "
                f"{reservation_request.party_size} "
                "guest(s) at the requested "
                "date and time."
            ),

        )

    best_combination = (
        availability["selected_tables"]
    )

    # ========================================================
    # CUSTOMER
    # ========================================================

    customer = None

    if reservation_request.customer_email:

        customer = db.execute(

            select(Customer)

            .where(
                Customer.email
                ==
                reservation_request.customer_email
            )

        ).scalar_one_or_none()

    if customer is None:

        customer = Customer(

            name=
                reservation_request.customer_name,

            email=
                reservation_request.customer_email,

            phone=
                reservation_request.customer_phone,

            created_at=
                now_local(),

        )

        db.add(customer)

        db.flush()

    else:

        customer.name = (
            reservation_request.customer_name
        )

        customer.phone = (
            reservation_request.customer_phone
        )

    # ========================================================
    # CONFIRMATION CODE
    # ========================================================

    confirmation_code = None

    for _ in range(10):

        candidate = (
            secrets.token_hex(4)
            .upper()
        )

        existing = db.execute(

            select(Reservation)

            .where(
                Reservation.confirmation_code
                == candidate
            )

        ).scalar_one_or_none()

        if existing is None:

            confirmation_code = candidate

            break

    if confirmation_code is None:

        raise HTTPException(

            status_code=500,

            detail=(
                "Could not generate "
                "reservation confirmation code."
            )

        )

    # ========================================================
    # CREATE RESERVATION
    # ========================================================

    current_time = now_local()

    reservation = Reservation(

        restaurant_id=
            restaurant.id,

        customer_id=
            customer.id,

        start_at=
            start_at,

        end_at=
            end_at,

        party_size=
            reservation_request.party_size,

        status=
            "confirmed",

        confirmation_code=
            confirmation_code,

        notes=
            reservation_request.notes,

        created_at=
            current_time,

        updated_at=
            current_time,

    )

    db.add(reservation)

    db.flush()

    # ========================================================
    # ASSIGN TABLES
    # ========================================================

    for table in best_combination:

        db.add(

            ReservationTable(

                reservation_id=
                    reservation.id,

                table_id=
                    table.id,

            )

        )

    db.commit()

    db.refresh(
        reservation
    )

    # ========================================================
    # CUSTOMER EMAIL
    # ========================================================

    if (
        customer.email
        and customer.email.strip()
    ):

        try:

            table_numbers = ", ".join(

                f"Table {table.table_number}"

                for table
                in best_combination

            )

            email_body = (

                f"Hello {customer.name},\n\n"

                f"Your reservation has been "
                f"confirmed.\n\n"

                f"Restaurant: "
                f"{restaurant.name}\n"

                f"Date: "
                f"{start_at.strftime('%d.%m.%Y')}\n"

                f"Time: "
                f"{start_at.strftime('%H:%M')}\n"

                f"Guests: "
                f"{reservation.party_size}\n"

                f"Table(s): "
                f"{table_numbers}\n"

                f"Confirmation code: "
                f"{reservation.confirmation_code}\n\n"

                f"Notes: "
                f"{reservation.notes or 'None'}\n\n"

                f"Thank you for choosing "
                f"{restaurant.name}.\n\n"

                f"Please keep this email as "
                f"your reservation confirmation."

            )

            send_email(

                recipient=
                    customer.email.strip(),

                subject=
                    f"Reservation Confirmation - "
                    f"{restaurant.name}",

                body=
                    email_body,

            )

        except Exception:

            # Email failure does not invalidate
            # an already-created reservation.
            pass

    # ========================================================
    # RESPONSE
    # ========================================================

    start_info = local_datetime_response(
        reservation.start_at
    )

    end_info = local_datetime_response(
        reservation.end_at
    )

    return {

        "status":
            "created",

        "message":
            "Reservation created successfully.",

        "timezone":
            "none",

        "reservation": {

            "id":
                reservation.id,

            "restaurant":
                restaurant.name,

            "customer": {

                "id":
                    customer.id,

                "name":
                    customer.name,

                "email":
                    customer.email,

                "phone":
                    customer.phone,

            },

            "start_at":
                start_info["iso"],

            "start_date":
                start_info["date"],

            "start_time":
                start_info["time"],

            "start_display_date":
                start_info["display_date"],

            "start_display_time":
                start_info["display_time"],

            "end_at":
                end_info["iso"],

            "end_date":
                end_info["date"],

            "end_time":
                end_info["time"],

            "end_display_date":
                end_info["display_date"],

            "end_display_time":
                end_info["display_time"],

            "party_size":
                reservation.party_size,

            "status":
                reservation.status,

            "confirmation_code":
                reservation.confirmation_code,

            "tables": [

                {

                    "id":
                        table.id,

                    "table_number":
                        table.table_number,

                    "capacity":
                        table.capacity,

                }

                for table
                in best_combination

            ],

        },

    }


# ============================================================
# ADD TABLE
# ============================================================

@app.post("/api/admin/tables")
def add_table(

    table_request: AddTableRequest,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    restaurant = db.execute(

        select(Restaurant)

        .where(
            Restaurant.name.ilike(
                table_request.restaurant_name
            )
        )

    ).scalar_one_or_none()

    if restaurant is None:

        raise HTTPException(
            status_code=404,
            detail="Restaurant not found.",
        )

    existing = db.execute(

        select(RestaurantTable)

        .where(

            RestaurantTable.restaurant_id
            == restaurant.id,

            RestaurantTable.table_number
            == table_request.table_number,

        )

    ).scalar_one_or_none()

    if existing:

        raise HTTPException(

            status_code=409,

            detail=(
                f"Table "
                f"{table_request.table_number} "
                f"already exists at "
                f"{restaurant.name}."
            ),

        )

    table = RestaurantTable(

        restaurant_id=
            restaurant.id,

        table_number=
            table_request.table_number,

        capacity=
            table_request.capacity,

        active=True,

    )

    db.add(table)

    db.commit()

    db.refresh(table)

    return {

        "status":
            "created",

        "table": {

            "id":
                table.id,

            "restaurant_name":
                restaurant.name,

            "table_number":
                table.table_number,

            "capacity":
                table.capacity,

            "active":
                table.active,

        },

    }


# ============================================================
# DEACTIVATE TABLE
# ============================================================

@app.delete(
    "/api/admin/tables/{table_id}"
)
def deactivate_table(

    table_id: int,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    table = db.get(
        RestaurantTable,
        table_id,
    )

    if table is None:

        raise HTTPException(
            status_code=404,
            detail="Table not found",
        )

    current_time = now_local()

    future_reservation = db.execute(

        select(Reservation)

        .join(
            ReservationTable,
            ReservationTable.reservation_id
            == Reservation.id,
        )

        .where(

            ReservationTable.table_id
            == table.id,

            Reservation.status.in_(
                [
                    "pending",
                    "confirmed",
                ]
            ),

            Reservation.end_at
            > current_time,

        )

    ).scalars().first()

    if future_reservation:

        raise HTTPException(

            status_code=409,

            detail=(
                "Cannot deactivate this table "
                "because it has a future "
                "reservation."
            ),

        )

    table.active = False

    db.commit()

    return {

        "status":
            "deactivated",

        "table_id":
            table.id,

        "message":
            "Table deactivated successfully.",

    }


# ============================================================
# GET RESTAURANTS
# ============================================================

@app.get("/api/admin/restaurants")
def get_restaurants(

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    restaurants = db.execute(

        select(Restaurant)

        .order_by(
            Restaurant.name.asc()
        )

    ).scalars().all()

    return {

        "restaurants": [

            {

                "id":
                    restaurant.id,

                "name":
                    restaurant.name,

            }

            for restaurant
            in restaurants

        ],

        "count":
            len(restaurants),

    }


# ============================================================
# NEWSLETTER SUBSCRIBERS
# ============================================================

@app.get(
    "/api/admin/newsletter/subscribers"
)
def newsletter_subscribers(

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    subscribers = db.execute(

        select(
            NewsletterSubscriber
        )

        .where(
            NewsletterSubscriber.active.is_(True)
        )

        .order_by(
            NewsletterSubscriber.subscribed_at.desc()
        )

    ).scalars().all()

    return {

        "subscribers": [

            {

                "id":
                    subscriber.id,

                "email":
                    subscriber.email,

                "subscribed_at":
                    subscriber.subscribed_at,

            }

            for subscriber
            in subscribers

        ],

        "count":
            len(subscribers),

    }

# ============================================================
# GET RESTAURANTS - EMPLOYEE
# ============================================================

@app.get("/api/employee/restaurants")
def get_employee_restaurants(
    db: Session = Depends(get_db),
):

    restaurants = db.execute(

        select(Restaurant)

        .order_by(
            Restaurant.name.asc()
        )

    ).scalars().all()

    return {

        "restaurants": [

            {

                "id":
                    restaurant.id,

                "name":
                    restaurant.name,

            }

            for restaurant
            in restaurants

        ],

        "count":
            len(restaurants),

    }

# ============================================================
# SEND EMAIL
# ============================================================

def send_email(

    recipient: str,

    subject: str,

    body: str,

):

    if not all(
        [
            SMTP_HOST,
            SMTP_USERNAME,
            SMTP_PASSWORD,
            EMAIL_FROM,
        ]
    ):

        raise RuntimeError(
            "SMTP configuration is incomplete."
        )

    message = EmailMessage()

    message["Subject"] = subject

    message["From"] = EMAIL_FROM

    message["To"] = recipient

    message.set_content(body)

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=20,
    ) as smtp:

        smtp.starttls()

        smtp.login(
            SMTP_USERNAME,
            SMTP_PASSWORD,
        )

        smtp.send_message(
            message
        )


# ============================================================
# SEND NEWSLETTER
# ============================================================

@app.post(
    "/api/admin/newsletter/send"
)
def send_newsletter(

    newsletter: NewsletterRequest,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    subscribers = db.execute(

        select(
            NewsletterSubscriber
        )

        .where(
            NewsletterSubscriber.active.is_(True)
        )

    ).scalars().all()

    if not subscribers:

        raise HTTPException(

            status_code=404,

            detail=(
                "There are no active "
                "newsletter subscribers."
            ),

        )

    sent = 0
    failed = 0

    for subscriber in subscribers:

        try:

            send_email(

                recipient=
                    subscriber.email,

                subject=
                    newsletter.subject,

                body=
                    newsletter.message,

            )

            sent += 1

        except Exception:

            failed += 1

    return {

        "status":
            "completed",

        "total_subscribers":
            len(subscribers),

        "sent":
            sent,

        "failed":
            failed,

    }
