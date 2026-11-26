from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models, schemas
from .database import get_db
from .permissions import require_business_role


router = APIRouter(tags=["Supplier Management"])


# REGISTER A NEW SUPPLIER

@router.post(
    "/businesses/{business_id}/suppliers",
    response_model=schemas.SupplierResponse,
    status_code=201
)
def create_supplier(
    business_id: int,
    supplier: schemas.SupplierCreate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    try:
        new_supplier = models.Supplier(
            business_id=business_id,
            company_name=supplier.company_name.strip(),
            contact_person=(
                supplier.contact_person.strip()
                if supplier.contact_person else None
            ),
            phone=supplier.phone.strip(),
            email=str(supplier.email).lower() if supplier.email else None,
            address=supplier.address.strip() if supplier.address else None
        )

        db.add(new_supplier)
        db.commit()
        db.refresh(new_supplier)

        return new_supplier

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A supplier with this phone number already exists in this business."
        )


# VIEW ALL SUPPLIERS

@router.get(
    "/businesses/{business_id}/suppliers",
    response_model=list[schemas.SupplierListResponse]
)
def get_suppliers(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    return db.query(models.Supplier).filter(
        models.Supplier.business_id == business_id
    ).order_by(
        models.Supplier.company_name
    ).all()


# VIEW ONE SUPPLIER

@router.get(
    "/businesses/{business_id}/suppliers/{supplier_id}",
    response_model=schemas.SupplierResponse
)
def get_supplier(
    business_id: int,
    supplier_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    supplier = db.query(models.Supplier).filter(
        models.Supplier.id == supplier_id,
        models.Supplier.business_id == business_id
    ).first()

    if supplier is None:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found in this business."
        )

    return supplier


# UPDATE SUPPLIER DETAILS

@router.put(
    "/businesses/{business_id}/suppliers/{supplier_id}",
    response_model=schemas.SupplierResponse
)
def update_supplier(
    business_id: int,
    supplier_id: int,
    supplier_update: schemas.SupplierUpdate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    supplier = db.query(models.Supplier).filter(
        models.Supplier.id == supplier_id,
        models.Supplier.business_id == business_id
    ).first()

    if supplier is None:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found in this business."
        )

    supplier.company_name = supplier_update.company_name.strip()
    supplier.contact_person = (
        supplier_update.contact_person.strip()
        if supplier_update.contact_person else None
    )
    supplier.phone = supplier_update.phone.strip()
    supplier.email = (
        str(supplier_update.email).lower()
        if supplier_update.email else None
    )
    supplier.address = (
        supplier_update.address.strip()
        if supplier_update.address else None
    )

    try:
        db.commit()
        db.refresh(supplier)
        return supplier

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A supplier with this phone number already exists in this business."
        )