
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from . import models, schemas
from .database import get_db
from .permissions import require_business_role


router = APIRouter(tags=["Purchasing Management"])


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def get_purchase_query(db: Session):
    return db.query(models.Purchase).options(
        selectinload(models.Purchase.items),
        selectinload(
            models.Purchase.supplier_credit
        ).selectinload(
            models.SupplierCredit.payments
        )
    )


@router.post(
    "/businesses/{business_id}/purchases",
    response_model=schemas.PurchaseResponse,
    status_code=201
)
def create_purchase(
    business_id: int,
    purchase_data: schemas.PurchaseCreate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    if membership.business_id != business_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this business."
        )

    try:
        supplier = db.query(models.Supplier).filter(
            models.Supplier.id == purchase_data.supplier_id,
            models.Supplier.business_id == business_id
        ).first()

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found in this business."
            )

        product_ids = [
            item.product_id for item in purchase_data.items
        ]

        if len(product_ids) != len(set(product_ids)):
            raise HTTPException(
                status_code=400,
                detail="A product can only appear once in a purchase."
            )

        purchase_items = []
        total_amount = Decimal("0.00")

        for item in purchase_data.items:
            product = db.query(models.Product).filter(
                models.Product.id == item.product_id,
                models.Product.business_id == business_id
            ).first()

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product ID {item.product_id} not found in this business."
                )

            if not product.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"{product.name} is inactive."
                )

            unit_cost = money(Decimal(str(item.unit_cost)))
            line_total = money(unit_cost * item.quantity)
            total_amount += line_total

            purchase_items.append({
                "product": product,
                "quantity": item.quantity,
                "unit_cost": unit_cost,
                "line_total": line_total
            })

        total_amount = money(total_amount)

        if total_amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Purchase total must be greater than zero."
            )

        payment_type = purchase_data.payment_type
        amount_paid = purchase_data.amount_paid

        if payment_type == "cash":
            if amount_paid is None:
                amount_paid = total_amount
            else:
                amount_paid = money(Decimal(str(amount_paid)))

            if amount_paid != total_amount:
                raise HTTPException(
                    status_code=400,
                    detail="For a cash purchase, amount_paid must equal the full purchase total."
                )

        elif payment_type == "partial":
            if amount_paid is None:
                raise HTTPException(
                    status_code=400,
                    detail="Enter the amount paid for a partial purchase."
                )

            amount_paid = money(Decimal(str(amount_paid)))

            if amount_paid <= 0 or amount_paid >= total_amount:
                raise HTTPException(
                    status_code=400,
                    detail="Partial payment must be greater than zero and less than the purchase total."
                )

        elif payment_type == "credit":
            if amount_paid is None:
                amount_paid = Decimal("0.00")
            else:
                amount_paid = money(Decimal(str(amount_paid)))

            if amount_paid != 0:
                raise HTTPException(
                    status_code=400,
                    detail="For a credit purchase, the initial amount_paid must be zero."
                )

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid payment type."
            )

        amount_paid = money(amount_paid)
        balance_due = money(total_amount - amount_paid)

        if balance_due > 0 and purchase_data.due_date is None:
            raise HTTPException(
                status_code=400,
                detail="A due_date is required for unpaid or partially paid purchases."
            )

        if balance_due == 0:
            status = "paid"
        elif amount_paid > 0:
            status = "partially_paid"
        else:
            status = "unpaid"

        purchase = models.Purchase(
            business_id=business_id,
            supplier_id=supplier.id,
            user_id=membership.user_id,
            total_amount=total_amount
        )

        db.add(purchase)
        db.flush()

        for item in purchase_items:
            product = item["product"]
            quantity = item["quantity"]

            purchase_item = models.PurchaseItem(
                purchase_id=purchase.id,
                product_id=product.id,
                quantity=quantity,
                unit_cost=item["unit_cost"],
                line_total=item["line_total"]
            )

            db.add(purchase_item)

            stock_before = product.stock_quantity
            product.stock_quantity += quantity
            product.cost_price = item["unit_cost"]

            movement = models.StockMovement(
                business_id=business_id,
                product_id=product.id,
                user_id=membership.user_id,
                movement_type="add",
                quantity=quantity,
                stock_before=stock_before,
                stock_after=product.stock_quantity,
                reason=f"Purchase #{purchase.id}"
            )

            db.add(movement)

        credit = models.SupplierCredit(
            purchase_id=purchase.id,
            business_id=business_id,
            supplier_id=supplier.id,
            amount_paid=amount_paid,
            balance_due=balance_due,
            status=status,
            due_date=purchase_data.due_date,
            user_id=membership.user_id
        )

        db.add(credit)
        db.flush()

        if amount_paid > 0:
            initial_payment = models.SupplierCreditPayment(
                credit_id=credit.id,
                amount=amount_paid,
                payment_date=datetime.now(timezone.utc),
                reference=f"Initial payment for Purchase #{purchase.id}",
                user_id=membership.user_id
            )

            db.add(initial_payment)

        db.commit()

        saved_purchase = get_purchase_query(db).filter(
            models.Purchase.id == purchase.id,
            models.Purchase.business_id == business_id
        ).first()

        return saved_purchase

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


@router.get(
    "/businesses/{business_id}/purchases",
    response_model=list[schemas.PurchaseResponse]
)
def get_purchases(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    if membership.business_id != business_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this business."
        )

    return get_purchase_query(db).filter(
        models.Purchase.business_id == business_id
    ).order_by(
        models.Purchase.created_at.desc()
    ).all()


@router.get(
    "/businesses/{business_id}/purchases/{purchase_id}",
    response_model=schemas.PurchaseResponse
)
def get_purchase(
    business_id: int,
    purchase_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    if membership.business_id != business_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this business."
        )

    purchase = get_purchase_query(db).filter(
        models.Purchase.id == purchase_id,
        models.Purchase.business_id == business_id
    ).first()

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase not found."
        )

    return purchase
