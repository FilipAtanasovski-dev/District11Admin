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
    Float,
    select,
)

from sqlalchemy.dialects.postgresql import JSONB

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


# ============================================================
# FLOOR PLAN OBJECT
# ============================================================

class FloorPlanObject(Base):

    __tablename__ = "floor_plan_objects"

    id = Column(
        BigInteger,
        primary_key=True,
    )

    restaurant_id = Column(
        BigInteger,
        ForeignKey(
            "restaurants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    table_id = Column(
        BigInteger,
        ForeignKey(
            "restaurant_tables.id",
            ondelete="CASCADE",
        ),
        nullable=True,
    )

    object_type = Column(
        String(20),
        nullable=False,
    )

    x = Column(
        Float,
        nullable=True,
    )

    y = Column(
        Float,
        nullable=True,
    )

    width = Column(
        Float,
        nullable=True,
    )

    height = Column(
        Float,
        nullable=True,
    )

    rotation = Column(
        Float,
        nullable=False,
        default=0,
    )

    x1 = Column(
        Float,
        nullable=True,
    )

    y1 = Column(
        Float,
        nullable=True,
    )

    x2 = Column(
        Float,
        nullable=True,
    )

    y2 = Column(
        Float,
        nullable=True,
    )

    shape = Column(
        String(30),
        nullable=True,
    )

    properties = Column(
        JSONB,
        nullable=True,
    )

    active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
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
        ForeignKey(
            "restaurant_tables.id",
            ondelete="CASCADE",
        ),
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


# ============================================================
# ADD TABLE REQUEST
# ============================================================

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

    # --------------------------------------------------------
    # FLOOR PLAN POSITION
    # --------------------------------------------------------

    x: float

    y: float

    width: float = Field(
        default=100,
        gt=0,
    )

    height: float = Field(
        default=100,
        gt=0,
    )

    rotation: float = 0

    # "rectangle" or "ellipse"
    shape: str = Field(
        default="rectangle",
        min_length=1,
        max_length=30,
    )


# ============================================================
# FLOOR PLAN REQUEST MODELS
# ============================================================

class CreateFloorPlanObjectRequest(BaseModel):

    restaurant_name: str = Field(
        min_length=1
    )

    object_type: str = Field(
        min_length=1,
        max_length=20,
    )

    x: float | None = None

    y: float | None = None

    width: float | None = None

    height: float | None = None

    rotation: float = 0

    x1: float | None = None

    y1: float | None = None

    x2: float | None = None

    y2: float | None = None

    shape: str | None = None

    properties: dict | None = None


class UpdateFloorPlanObjectRequest(BaseModel):

    x: float | None = None

    y: float | None = None

    width: float | None = None

    height: float | None = None

    rotation: float | None = None

    x1: float | None = None

    y1: float | None = None

    x2: float | None = None

    y2: float | None = None

    shape: str | None = None

    properties: dict | None = None


class CreateFloorPlanTableRequest(BaseModel):

    restaurant_name: str = Field(
        min_length=1
    )

    table_number: int = Field(
        gt=0
    )

    capacity: int = Field(
        gt=0
    )

    x: float

    y: float

    width: float = Field(
        default=100,
        gt=0,
    )

    height: float = Field(
        default=100,
        gt=0,
    )

    rotation: float = 0

    shape: str = Field(
        default="rectangle",
        min_length=1,
        max_length=30,
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
    version="1.3.0",
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
# GET FLOOR PLAN
# ============================================================

@app.get("/api/admin/floor-plan")
def get_floor_plan(

    restaurant_name: str,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),
):

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

    objects = db.execute(

        select(FloorPlanObject)

        .where(

            FloorPlanObject.restaurant_id
            == restaurant.id,

            FloorPlanObject.active.is_(True),

        )

        .order_by(
            FloorPlanObject.id.asc()
        )

    ).scalars().all()

    result = []

    for obj in objects:

        result.append({

            "id":
                obj.id,

            "restaurant_id":
                obj.restaurant_id,

            "table_id":
                obj.table_id,

            "object_type":
                obj.object_type,

            "x":
                obj.x,

            "y":
                obj.y,

            "width":
                obj.width,

            "height":
                obj.height,

            "rotation":
                obj.rotation,

            "x1":
                obj.x1,

            "y1":
                obj.y1,

            "x2":
                obj.x2,

            "y2":
                obj.y2,

            "shape":
                obj.shape,

            "properties":
                obj.properties or {},

            "active":
                obj.active,

            "created_at":
                (
                    obj.created_at.isoformat()
                    if obj.created_at
                    else None
                ),

            "updated_at":
                (
                    obj.updated_at.isoformat()
                    if obj.updated_at
                    else None
                ),

        })

    return {

        "restaurant": {

            "id":
                restaurant.id,

            "name":
                restaurant.name,

        },

        "objects":
            result,

        "count":
            len(result),

    }


# ============================================================
# FIND AVAILABLE TABLES
#
# THIS IS THE SINGLE SOURCE OF TRUTH FOR AVAILABILITY.
# ============================================================

def find_available_tables(

    db: Session,

    restaurant_id: int,

    start_at: datetime,

    end_at: datetime,

    party_size: int,

):

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

    available_tables = [

        table

        for table in tables

        if table.id
        not in reserved_table_ids

    ]

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
                <
                len(best_combination)
            ):

                best_combination = combination
                best_capacity = capacity

                continue

            if (
                len(combination)
                ==
                len(best_combination)
                and
                capacity
                <
                best_capacity
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
# CREATE FLOOR PLAN OBJECT
#
# Used for:
#
# - line
# - rectangle
# - ellipse
#
# Tables should normally use /tables instead because a table
# also needs a restaurant_tables record.
# ============================================================

@app.post("/api/admin/floor-plan/objects")
def create_floor_plan_object(

    object_request:
        CreateFloorPlanObjectRequest,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    restaurant = db.execute(

        select(Restaurant)

        .where(
            Restaurant.name.ilike(
                object_request.restaurant_name
            )
        )

    ).scalar_one_or_none()

    if restaurant is None:

        raise HTTPException(
            status_code=404,
            detail="Restaurant not found.",
        )

    allowed_types = {
        "line",
        "rectangle",
        "ellipse",
    }

    if object_request.object_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid object type. "
                "Allowed types are: "
                "line, rectangle, ellipse."
            ),
        )

    if object_request.object_type == "line":

        if (
            object_request.x1 is None
            or object_request.y1 is None
            or object_request.x2 is None
            or object_request.y2 is None
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Lines require x1, y1, x2 and y2."
                ),
            )

    else:

        if (
            object_request.x is None
            or object_request.y is None
            or object_request.width is None
            or object_request.height is None
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Shapes require x, y, width and height."
                ),
            )

        if object_request.width <= 0:

            raise HTTPException(
                status_code=400,
                detail="Width must be greater than zero.",
            )

        if object_request.height <= 0:

            raise HTTPException(
                status_code=400,
                detail="Height must be greater than zero.",
            )

    if object_request.shape:

        allowed_shapes = {
            "rectangle",
            "ellipse",
        }

        if (
            object_request.shape
            not in allowed_shapes
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid shape. "
                    "Allowed shapes are: "
                    "rectangle, ellipse."
                ),
            )

    current_time = now_local()

    obj = FloorPlanObject(

        restaurant_id=
            restaurant.id,

        table_id=None,

        object_type=
            object_request.object_type,

        x=
            object_request.x,

        y=
            object_request.y,

        width=
            object_request.width,

        height=
            object_request.height,

        rotation=
            object_request.rotation,

        x1=
            object_request.x1,

        y1=
            object_request.y1,

        x2=
            object_request.x2,

        y2=
            object_request.y2,

        shape=
            object_request.shape,

        properties=
            object_request.properties or {},

        active=True,

        created_at=
            current_time,

        updated_at=
            current_time,

    )

    db.add(obj)

    db.commit()

    db.refresh(obj)

    return {

        "status":
            "created",

        "object": {

            "id":
                obj.id,

            "restaurant_id":
                obj.restaurant_id,

            "table_id":
                obj.table_id,

            "object_type":
                obj.object_type,

            "x":
                obj.x,

            "y":
                obj.y,

            "width":
                obj.width,

            "height":
                obj.height,

            "rotation":
                obj.rotation,

            "x1":
                obj.x1,

            "y1":
                obj.y1,

            "x2":
                obj.x2,

            "y2":
                obj.y2,

            "shape":
                obj.shape,

            "properties":
                obj.properties or {},

            "active":
                obj.active,

        },

    }


# ============================================================
# UPDATE FLOOR PLAN OBJECT
#
# Used when the user:
#
# - moves an object
# - resizes an object
# - rotates an object
# - changes line endpoints
# ============================================================

@app.put(
    "/api/admin/floor-plan/objects/{object_id}"
)
def update_floor_plan_object(

    object_id: int,

    object_request:
        UpdateFloorPlanObjectRequest,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    obj = db.get(
        FloorPlanObject,
        object_id,
    )

    if obj is None:

        raise HTTPException(
            status_code=404,
            detail="Floor plan object not found.",
        )

    if not obj.active:

        raise HTTPException(
            status_code=404,
            detail="Floor plan object is inactive.",
        )

    if object_request.width is not None:

        if object_request.width <= 0:

            raise HTTPException(
                status_code=400,
                detail="Width must be greater than zero.",
            )

        obj.width = object_request.width

    if object_request.height is not None:

        if object_request.height <= 0:

            raise HTTPException(
                status_code=400,
                detail="Height must be greater than zero.",
            )

        obj.height = object_request.height

    if object_request.x is not None:

        obj.x = object_request.x

    if object_request.y is not None:

        obj.y = object_request.y

    if object_request.rotation is not None:

        obj.rotation = object_request.rotation

    if object_request.x1 is not None:

        obj.x1 = object_request.x1

    if object_request.y1 is not None:

        obj.y1 = object_request.y1

    if object_request.x2 is not None:

        obj.x2 = object_request.x2

    if object_request.y2 is not None:

        obj.y2 = object_request.y2

    if object_request.shape is not None:

        allowed_shapes = {
            "rectangle",
            "ellipse",
        }

        if (
            object_request.shape
            not in allowed_shapes
        ):

            raise HTTPException(
                status_code=400,
                detail="Invalid shape.",
            )

        obj.shape = object_request.shape

    if object_request.properties is not None:

        obj.properties = (
            object_request.properties
        )

    obj.updated_at = now_local()

    db.commit()

    db.refresh(obj)

    return {

        "status":
            "updated",

        "object": {

            "id":
                obj.id,

            "restaurant_id":
                obj.restaurant_id,

            "table_id":
                obj.table_id,

            "object_type":
                obj.object_type,

            "x":
                obj.x,

            "y":
                obj.y,

            "width":
                obj.width,

            "height":
                obj.height,

            "rotation":
                obj.rotation,

            "x1":
                obj.x1,

            "y1":
                obj.y1,

            "x2":
                obj.x2,

            "y2":
                obj.y2,

            "shape":
                obj.shape,

            "properties":
                obj.properties or {},

            "active":
                obj.active,

        },

    }


# ============================================================
# DELETE FLOOR PLAN OBJECT
#
# Uses soft deletion for standalone floor-plan objects.
#
# If the object represents a table, the actual table is
# permanently deleted as well.
# ============================================================

@app.delete(
    "/api/admin/floor-plan/objects/{object_id}"
)
def delete_floor_plan_object(

    object_id: int,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    obj = db.get(
        FloorPlanObject,
        object_id,
    )

    if obj is None:

        raise HTTPException(
            status_code=404,
            detail="Floor plan object not found.",
        )

    if not obj.active:

        return {

            "status":
                "already_deleted",

            "object_id":
                obj.id,

        }

    current_time = now_local()

    # --------------------------------------------------------
    # If this object represents a table, permanently delete
    # the actual restaurant table as well.
    # --------------------------------------------------------

    if obj.table_id is not None:

        table = db.get(
            RestaurantTable,
            obj.table_id,
        )

        if table:

            # Do not allow deletion if the table has a future
            # reservation.

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
                        "Cannot delete this table "
                        "because it has a future "
                        "reservation."
                    ),
                )

            # ------------------------------------------------
            # Permanently delete the table.
            #
            # ON DELETE CASCADE will remove:
            #
            # - reservation_tables rows
            # - this floor_plan_objects row
            # ------------------------------------------------

            db.delete(table)

            db.commit()

            return {

                "status":
                    "deleted",

                "object_id":
                    object_id,

                "table_id":
                    table.id,

                "message":
                    "Table permanently deleted successfully.",

            }

    # --------------------------------------------------------
    # Standalone floor-plan object:
    # keep the existing soft-delete behavior.
    # --------------------------------------------------------

    obj.active = False

    obj.updated_at = current_time

    db.commit()

    return {

        "status":
            "deleted",

        "object_id":
            obj.id,

        "table_id":
            None,

        "message":
            "Floor plan object deleted successfully.",

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

    if start_at < now_local():

        raise HTTPException(

            status_code=400,

            detail=(
                "Reservation time "
                "cannot be in the past."
            ),

        )

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

            pass

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
#
# THIS CREATES:
#
# 1. restaurant_tables
#
# AND
#
# 2. floor_plan_objects
#
# linked using floor_plan_objects.table_id
# ============================================================

@app.post("/api/admin/tables")
def add_table(

    table_request: AddTableRequest,

    request: Request,

    db: Session = Depends(get_db),

    _: bool = Depends(require_admin),

):

    # --------------------------------------------------------
    # Find restaurant
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Check duplicate table number
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Validate floor-plan shape
    # --------------------------------------------------------

    allowed_shapes = {
        "rectangle",
        "ellipse",
    }

    if table_request.shape not in allowed_shapes:

        raise HTTPException(

            status_code=400,

            detail=(
                "Invalid table shape. "
                "Allowed shapes are: "
                "rectangle, ellipse."
            ),

        )

    # ========================================================
    # CREATE RESTAURANT TABLE
    # ========================================================

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

    # --------------------------------------------------------
    # Flush so PostgreSQL generates table.id
    #
    # We need this ID for floor_plan_objects.table_id.
    # --------------------------------------------------------

    db.flush()

    # ========================================================
    # CREATE FLOOR PLAN OBJECT
    # ========================================================

    current_time = now_local()

    floor_plan_object = FloorPlanObject(

        restaurant_id=
            restaurant.id,

        table_id=
            table.id,

        object_type=
            "table",

        x=
            table_request.x,

        y=
            table_request.y,

        width=
            table_request.width,

        height=
            table_request.height,

        rotation=
            table_request.rotation,

        shape=
            table_request.shape,

        properties={
            "table_number":
                table_request.table_number,

            "capacity":
                table_request.capacity,
        },

        active=True,

        created_at=
            current_time,

        updated_at=
            current_time,

    )

    db.add(
        floor_plan_object
    )

    # ========================================================
    # COMMIT BOTH AT ONCE
    # ========================================================

    db.commit()

    # --------------------------------------------------------
    # Refresh both objects
    # --------------------------------------------------------

    db.refresh(table)

    db.refresh(
        floor_plan_object
    )

    # ========================================================
    # RESPONSE
    # ========================================================

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

        "floor_plan_object": {

            "id":
                floor_plan_object.id,

            "restaurant_id":
                floor_plan_object.restaurant_id,

            "table_id":
                floor_plan_object.table_id,

            "object_type":
                floor_plan_object.object_type,

            "x":
                floor_plan_object.x,

            "y":
                floor_plan_object.y,

            "width":
                floor_plan_object.width,

            "height":
                floor_plan_object.height,

            "rotation":
                floor_plan_object.rotation,

            "shape":
                floor_plan_object.shape,

            "properties":
                floor_plan_object.properties,

            "active":
                floor_plan_object.active,

        },

    }


# ============================================================
# DELETE TABLE
#
# PERMANENTLY DELETES:
#
# 1. restaurant_tables
# 2. linked floor_plan_objects
# 3. reservation_tables links
#
# The table cannot be deleted if it has a future reservation.
# ============================================================

@app.delete(
    "/api/admin/tables/{table_id}"
)
def delete_table(

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

    # --------------------------------------------------------
    # Check for future reservations
    # --------------------------------------------------------

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
                "Cannot delete this table "
                "because it has a future "
                "reservation."
            ),

        )

    # --------------------------------------------------------
    # Permanently delete the table.
    #
    # PostgreSQL ON DELETE CASCADE will automatically delete:
    #
    # - reservation_tables rows
    # - linked floor_plan_objects rows
    #
    # The database performs the cascade.
    # --------------------------------------------------------

    db.delete(table)

    db.commit()

    return {

        "status":
            "deleted",

        "table_id":
            table_id,

        "message":
            "Table permanently deleted successfully.",

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