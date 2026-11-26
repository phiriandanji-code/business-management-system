
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from . import models, schemas
from .database import get_db
from .permissions import require_business_role

router = APIRouter(tags=["Supplier Credit Management"])


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def get_credit_status(credit, reference_date: date) -> str:
    if credit.balance_due <= 0:
        return "paid"

    if credit.due_date and credit.due_date.date() < reference_date:
        return "overdue"

    if credit.amount_paid > 0:
        return "partially_paid"

    return "unpaid"


def get_credit_query(db: Session):
    return db.query(models.SupplierCredit).options(
        selectinload(models.SupplierCredit.payments)
    )


@router.get(
    "/businesses/{business_id}/supplier-credits",
    response_model=list[schemas.SupplierCreditResponse]
)
def get_supplier_credits(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    credits = get_credit_query(db).filter(
        models.SupplierCredit.business_id == business_id
    ).order_by(
        models.SupplierCredit.created_at.desc()
    ).all()

    today = datetime.now(timezone.utc).date()
    changed = False

    for credit in credits:
        new_status = get_credit_status(credit, today)
        if credit.status != new_status:
            credit.status = new_status
            changed = True

    if changed:
        db.commit()

    return credits


@router.get(
    "/businesses/{business_id}/supplier-credits/{credit_id}",
    response_model=schemas.SupplierCreditResponse
)
def get_supplier_credit(
    business_id: int,
    credit_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    credit = get_credit_query(db).filter(
        models.SupplierCredit.id == credit_id,
        models.SupplierCredit.business_id == business_id
    ).first()

    if not credit:
        raise HTTPException(
            status_code=404,
            detail="Supplier credit not found."
        )

    today = datetime.now(timezone.utc).date()
    new_status = get_credit_status(credit, today)

    if credit.status != new_status:
        credit.status = new_status
        db.commit()
        db.refresh(credit)

    return credit


@router.post(
    "/businesses/{business_id}/supplier-credits/{credit_id}/payments",
    response_model=schemas.SupplierCreditResponse,
    status_code=201
)
def record_supplier_credit_payment(
    business_id: int,
    credit_id: int,
    payment_data: schemas.SupplierCreditPaymentCreate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    credit = db.query(models.SupplierCredit).filter(
        models.SupplierCredit.id == credit_id,
        models.SupplierCredit.business_id == business_id
    ).first()

    if not credit:
        raise HTTPException(
            status_code=404,
            detail="Supplier credit not found."
        )

    if credit.balance_due <= 0:
        raise HTTPException(
            status_code=400,
            detail="This supplier credit has already been fully paid."
        )

    amount = money(payment_data.amount)
    outstanding = money(credit.balance_due)

    if amount > outstanding:
        raise HTTPException(
            status_code=400,
            detail="Payment cannot exceed the outstanding balance."
        )

    if payment_data.payment_date.date() > datetime.now(timezone.utc).date():
        raise HTTPException(
            status_code=400,
            detail="Payment date cannot be in the future."
        )

    payment = models.SupplierCreditPayment(
        credit_id=credit.id,
        amount=amount,
        payment_date=payment_data.payment_date,
        reference=payment_data.reference,
        user_id=membership.user_id
    )

    credit.amount_paid = money(credit.amount_paid + amount)
    credit.balance_due = money(credit.balance_due - amount)

    reference_date = payment_data.payment_date.date()
    credit.status = get_credit_status(credit, reference_date)

    db.add(payment)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not record supplier payment."
        )

    updated_credit = get_credit_query(db).filter(
        models.SupplierCredit.id == credit.id,
        models.SupplierCredit.business_id == business_id
    ).first()

    return updated_credit
