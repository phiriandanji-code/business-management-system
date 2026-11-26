from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .permissions import require_business_role


router = APIRouter(tags=["Business Profile"])


# VIEW BUSINESS PROFILE
@router.get(
    "/businesses/{business_id}/profile",
    response_model=schemas.BusinessResponse
)
def get_business_profile(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    business = db.query(models.Business).filter(
        models.Business.id == business_id
    ).first()

    if business is None:
        raise HTTPException(
            status_code=404,
            detail="Business not found."
        )

    return business


# UPDATE BUSINESS PROFILE - OWNER ONLY
@router.put(
    "/businesses/{business_id}/profile",
    response_model=schemas.BusinessResponse
)
def update_business_profile(
    business_id: int,
    profile: schemas.BusinessProfileUpdate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner")
    ),
    db: Session = Depends(get_db)
):
    business = db.query(models.Business).filter(
        models.Business.id == business_id
    ).first()

    if business is None:
        raise HTTPException(
            status_code=404,
            detail="Business not found."
        )

    for field in ("phone", "email", "address"):
        if field in profile.model_fields_set:
            value = getattr(profile, field)

            if value is not None:
                value = str(value).strip()

            setattr(business, field, value)

    db.commit()
    db.refresh(business)

    return business