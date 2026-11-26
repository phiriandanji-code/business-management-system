from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .auth import get_current_user
from .permissions import require_business_role


router = APIRouter(tags=["Sales Processing"])


@router.post(
    "/businesses/{business_id}/sales",
    response_model=schemas.SaleResponse,
    status_code=201
)
def create_sale(
    business_id: int,
    sale_data: schemas.SaleCreate,
    current_user: models.User = Depends(get_current_user),
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    quantities = {}

    for item in sale_data.items:
        quantities[item.product_id] = (
            quantities.get(item.product_id, 0) + item.quantity
        )

    products = db.query(models.Product).filter(
        models.Product.business_id == business_id,
        models.Product.id.in_(quantities.keys()),
        models.Product.is_active == True
    ).all()

    product_map = {
        product.id: product for product in products
    }

    if set(quantities) != set(product_map):
        raise HTTPException(
            status_code=404,
            detail="One or more products were not found."
        )

    for product_id, quantity in quantities.items():
        product = product_map[product_id]

        if product.stock_quantity < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}."
            )

    try:
        new_sale = models.Sale(
            business_id=business_id,
            user_id=current_user.id,
            total_amount=Decimal("0.00")
        )

        db.add(new_sale)
        db.flush()

        total_amount = Decimal("0.00")

        for product_id, quantity in quantities.items():
            product = product_map[product_id]

            stock_before = product.stock_quantity
            stock_after = stock_before - quantity

            unit_price = Decimal(str(product.selling_price))
            cost_price = Decimal(str(product.cost_price))

            line_total = (
                unit_price * quantity
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            total_amount += line_total

            product.stock_quantity = stock_after

            db.add(models.SaleItem(
                sale_id=new_sale.id,
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                quantity=quantity,
                cost_price=cost_price,
                unit_price=unit_price,
                line_total=line_total
            ))

            db.add(models.StockMovement(
                business_id=business_id,
                product_id=product.id,
                user_id=current_user.id,
                movement_type="remove",
                quantity=quantity,
                stock_before=stock_before,
                stock_after=stock_after,
                reason=f"Sale SALE-{new_sale.id:06d}"
            ))

        new_sale.total_amount = total_amount

        db.commit()
        db.refresh(new_sale)

        saved_items = db.query(models.SaleItem).filter(
            models.SaleItem.sale_id == new_sale.id
        ).all()

        return {
            "id": new_sale.id,
            "business_id": new_sale.business_id,
            "user_id": new_sale.user_id,
            "total_amount": new_sale.total_amount,
            "created_at": new_sale.created_at,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total
                }
                for item in saved_items
            ]
        }

    except Exception:
        db.rollback()
        raise