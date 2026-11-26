from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models, schemas
from .database import get_db
from .security import get_password_hash
from .permissions import require_business_role


router = APIRouter(tags=["Staff Management"])


# -----------------------------------------
# VIEW REGISTERED EMPLOYEES
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/staff",
    response_model=list[schemas.StaffResponse]
)
def get_staff(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner")
    ),
    db: Session = Depends(get_db)
):
    employees = db.query(
        models.BusinessMembership,
        models.User
    ).join(
        models.User,
        models.User.id == models.BusinessMembership.user_id
    ).filter(
        models.BusinessMembership.business_id == business_id,
        models.BusinessMembership.role.in_(["manager", "cashier"])
    ).order_by(
        models.User.full_name
    ).all()

    return [
        {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "business_id": business_id,
            "role": employee_membership.role,
            "is_active": employee_membership.is_active
        }
        for employee_membership, user in employees
    ]


# -----------------------------------------
# REGISTER A NEW EMPLOYEE
# -----------------------------------------

@router.post(
    "/businesses/{business_id}/staff",
    response_model=schemas.StaffResponse,
    status_code=201
)
def create_staff(
    business_id: int,
    staff: schemas.StaffCreate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner")
    ),
    db: Session = Depends(get_db)
):
    email = str(staff.email).lower()

    existing_user = db.query(models.User).filter(
        models.User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="This email address is already registered."
        )

    try:
        new_user = models.User(
            full_name=staff.full_name.strip(),
            email=email,
            hashed_password=get_password_hash(staff.password)
        )

        db.add(new_user)
        db.flush()

        new_membership = models.BusinessMembership(
            user_id=new_user.id,
            business_id=business_id,
            role=staff.role,
            is_active=True
        )

        db.add(new_membership)
        db.commit()
        db.refresh(new_user)
        db.refresh(new_membership)

        return {
            "user_id": new_user.id,
            "full_name": new_user.full_name,
            "email": new_user.email,
            "business_id": business_id,
            "role": new_membership.role,
            "is_active": new_membership.is_active
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Employee registration could not be completed."
        )


# -----------------------------------------
# ACTIVATE OR DEACTIVATE AN EMPLOYEE
# -----------------------------------------

@router.patch(
    "/businesses/{business_id}/staff/{user_id}/status",
    response_model=schemas.StaffResponse
)
def update_staff_status(
    business_id: int,
    user_id: int,
    status_update: schemas.StaffStatusUpdate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner")
    ),
    db: Session = Depends(get_db)
):
    employee_membership = db.query(
        models.BusinessMembership
    ).filter(
        models.BusinessMembership.user_id == user_id,
        models.BusinessMembership.business_id == business_id,
        models.BusinessMembership.role.in_(["manager", "cashier"])
    ).first()

    if employee_membership is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found in this business."
        )

    employee = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee account not found."
        )

    employee_membership.is_active = status_update.is_active

    db.commit()
    db.refresh(employee_membership)

    return {
        "user_id": employee.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "business_id": business_id,
        "role": employee_membership.role,
        "is_active": employee_membership.is_active
    }