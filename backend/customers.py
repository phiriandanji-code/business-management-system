
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models, schemas
from .database import get_db
from .permissions import require_business_role


router = APIRouter(tags=["Customer Management"])


# -----------------------------------------
# REGISTER A NEW CUSTOMER
# -----------------------------------------

@router.post(
    "/businesses/{business_id}/customers",
    response_model=schemas.CustomerResponse,
    status_code=201
)
def create_customer(
    business_id: int,
    customer: schemas.CustomerCreate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    try:
        new_customer = models.Customer(
            business_id=business_id,
            full_name=customer.full_name.strip(),
            phone=customer.phone.strip(),
            email=str(customer.email).lower() if customer.email else None,
            address=customer.address.strip() if customer.address else None
        )

        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)

        return new_customer

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A customer with this phone number already exists in this business."
        )


# -----------------------------------------
# VIEW ALL CUSTOMERS
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/customers",
    response_model=list[schemas.CustomerListResponse]
)
def get_customers(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    return db.query(models.Customer).filter(
        models.Customer.business_id == business_id
    ).order_by(
        models.Customer.full_name
    ).all()


# -----------------------------------------
# VIEW ONE CUSTOMER
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/customers/{customer_id}",
    response_model=schemas.CustomerResponse
)
def get_customer(
    business_id: int,
    customer_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == customer_id,
        models.Customer.business_id == business_id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found in this business."
        )

    return customer


# -----------------------------------------
# UPDATE CUSTOMER DETAILS
# -----------------------------------------

@router.put(
    "/businesses/{business_id}/customers/{customer_id}",
    response_model=schemas.CustomerResponse
)
def update_customer(
    business_id: int,
    customer_id: int,
    customer_update: schemas.CustomerUpdate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == customer_id,
        models.Customer.business_id == business_id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found in this business."
        )

    customer.full_name = customer_update.full_name.strip()
    customer.phone = customer_update.phone.strip()
    customer.email = (
        str(customer_update.email).lower()
        if customer_update.email else None
    )
    customer.address = (
        customer_update.address.strip()
        if customer_update.address else None
    )

    try:
        db.commit()
        db.refresh(customer)
        return customer

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A customer with this phone number already exists in this business."
        )
