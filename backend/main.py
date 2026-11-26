
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import Base, engine, get_db
from . import models, schemas
from .security import get_password_hash, verify_password
from .tokens import create_access_token
from .auth import get_current_user


# ==================================================
# APPLICATION CONFIGURATION
# ==================================================

app = FastAPI(
    title="KABOWA Business Management System",
    description="Business management platform for small and medium enterprises.",
    version="0.2.0"
)

app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

Base.metadata.create_all(bind=engine)


# ==================================================
# HOME AND DASHBOARD
# ==================================================

@app.get("/")
def home():
    return FileResponse("frontend/index.html")


@app.get("/app/dashboard.html")
def dashboard_page():
    return FileResponse("frontend/dashboard.html")


# ==================================================
# OWNER REGISTRATION
# ==================================================

@app.post(
    "/register-owner/",
    response_model=schemas.OwnerRegistrationResponse,
    status_code=201
)
@app.post(
    "/owner/register",
    response_model=schemas.OwnerRegistrationResponse,
    status_code=201,
    include_in_schema=False
)
def register_owner(
    registration: schemas.OwnerRegistration,
    db: Session = Depends(get_db)
):
    email = str(registration.email).lower()

    existing_user = db.query(models.User).filter(
        models.User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="This email address is already registered."
        )

    try:
        user = models.User(
            full_name=registration.full_name.strip(),
            email=email,
            hashed_password=get_password_hash(
                registration.password
            )
        )

        db.add(user)
        db.flush()

        business = models.Business(
            name=registration.business_name.strip(),
            business_type=registration.business_type.strip()
        )

        db.add(business)
        db.flush()

        membership = models.BusinessMembership(
            user_id=user.id,
            business_id=business.id,
            role="owner",
            is_active=True
        )

        db.add(membership)
        db.commit()

        db.refresh(user)
        db.refresh(business)

        return {
            "user": user,
            "business": business
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Unable to register this account."
        )


# ==================================================
# USER LOGIN
# ==================================================

@app.post(
    "/login/",
    response_model=schemas.TokenResponse
)
def login(
    credentials: schemas.LoginRequest,
    db: Session = Depends(get_db)
):
    email = str(credentials.email).lower()

    user = db.query(models.User).filter(
        models.User.email == email
    ).first()

    if user is None or not verify_password(
        credentials.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer"
    }


# ==================================================
# CURRENT USER
# ==================================================

@app.get(
    "/users/me",
    response_model=schemas.UserResponse
)
def read_current_user(
    current_user: models.User = Depends(get_current_user)
):
    return current_user


# ==================================================
# USER BUSINESS MEMBERSHIPS
# ==================================================

@app.get("/my-businesses/")
def get_my_businesses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memberships = db.query(
        models.BusinessMembership,
        models.Business
    ).join(
        models.Business,
        models.Business.id == models.BusinessMembership.business_id
    ).filter(
        models.BusinessMembership.user_id == current_user.id,
        models.BusinessMembership.is_active == True
    ).order_by(
        models.Business.id
    ).all()

    return [
        {
            "business_id": business.id,
            "business_name": business.name,
            "business_type": business.business_type,
            "role": membership.role
        }
        for membership, business in memberships
    ]


# ==================================================
# SECURE BUSINESS MANAGEMENT
# ==================================================

@app.post(
    "/businesses/",
    response_model=schemas.BusinessResponse,
    status_code=201
)
def create_business(
    business: schemas.BusinessCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    owner_membership = db.query(
        models.BusinessMembership
    ).filter(
        models.BusinessMembership.user_id == current_user.id,
        models.BusinessMembership.role == "owner",
        models.BusinessMembership.is_active == True
    ).first()

    if owner_membership is None:
        raise HTTPException(
            status_code=403,
            detail="Only active Owners can create businesses."
        )

    try:
        new_business = models.Business(
            name=business.name.strip(),
            business_type=business.business_type.strip()
        )

        db.add(new_business)
        db.flush()

        new_membership = models.BusinessMembership(
            user_id=current_user.id,
            business_id=new_business.id,
            role="owner",
            is_active=True
        )

        db.add(new_membership)
        db.commit()
        db.refresh(new_business)

        return new_business

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Business creation could not be completed."
        )


@app.get(
    "/businesses/",
    response_model=list[schemas.BusinessResponse]
)
def get_businesses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Business).join(
        models.BusinessMembership,
        models.Business.id == models.BusinessMembership.business_id
    ).filter(
        models.BusinessMembership.user_id == current_user.id,
        models.BusinessMembership.is_active == True
    ).order_by(
        models.Business.id
    ).all()


# ==================================================
# PRODUCTS AND INVENTORY
# ==================================================

from .operations import router as operations_router

app.include_router(operations_router)


# ==================================================
# SALES HISTORY AND RECEIPTS
# ==================================================

from .sales import router as sales_router

app.include_router(sales_router)


# ==================================================
# STAFF MANAGEMENT
# ==================================================

from .staff import router as staff_router

app.include_router(staff_router)


# ==================================================
# FINANCIAL REPORTS
# ==================================================

from .reports import router as reports_router

app.include_router(reports_router)


# ==================================================
# POINT OF SALE / CHECKOUT
# ==================================================

from .checkout import router as checkout_router

app.include_router(checkout_router)
# ==================================================
# CUSTOMER MANAGEMENT
# ==================================================

from .customers import router as customers_router

app.include_router(customers_router)
# ==================================================
# SUPPLIER MANAGEMENT
# ==================================================

from .suppliers import router as suppliers_router

app.include_router(suppliers_router)
# ==================================================
# PURCHASING MANAGEMENT
# ==================================================

from .purchasing import router as purchasing_router

app.include_router(purchasing_router)
# -----------------------------------------
# EXPENSE MANAGEMENT
# -----------------------------------------

from .expenses import router as expenses_router

app.include_router(expenses_router)
# -----------------------------------------
# LOAN MANAGEMENT
# -----------------------------------------

from .loans import router as loans_router

app.include_router(loans_router)
# -----------------------------------------
# CUSTOMER CREDIT SALES
# -----------------------------------------

from .credit_sales import router as credit_sales_router

app.include_router(credit_sales_router)
# -----------------------------------------
# SUPPLIER CREDIT MANAGEMENT
# -----------------------------------------

from .supplier_credit import router as supplier_credit_router

app.include_router(supplier_credit_router)
# -----------------------------------------
# BUSINESS PROFILE MANAGEMENT
# -----------------------------------------

from .business_profile import router as business_profile_router

app.include_router(business_profile_router)
# BUSINESS BACKUP AND RESTORE

from .backup import router as backup_router

app.include_router(backup_router)