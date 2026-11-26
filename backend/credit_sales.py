
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .auth import get_current_user
from .permissions import require_business_role


router = APIRouter(tags=["Customer Credit Sales"])


def get_credit_sale_response(
    db: Session,
    credit_sale: models.CreditSale
):
    payments = db.query(
        models.CreditSalePayment
    ).filter(
        models.CreditSalePayment.credit_sale_id == credit_sale.id
    ).order_by(
        models.CreditSalePayment.payment_date
    ).all()

    if credit_sale.balance_due <= Decimal("0.00"):
        status = "paid"
    elif (
        credit_sale.due_date is not None
        and credit_sale.due_date.date() < date.today()
    ):
        status = "overdue"
    elif credit_sale.amount_paid > Decimal("0.00"):
        status = "partially_paid"
    else:
        status = "unpaid"

    credit_sale.status = status

    return {
        "id": credit_sale.id,
        "business_id": credit_sale.business_id,
        "customer_id": credit_sale.customer_id,
        "sale_id": credit_sale.sale_id,
        "total_amount": credit_sale.total_amount,
        "amount_paid": credit_sale.amount_paid,
        "balance_due": credit_sale.balance_due,
        "status": status,
        "due_date": credit_sale.due_date,
        "user_id": credit_sale.user_id,
        "created_at": credit_sale.created_at,
        "payments": payments
    }


@router.post(
    "/businesses/{business_id}/credit-sales",
    response_model=schemas.CreditSaleResponse,
    status_code=201
)
def create_credit_sale(
    business_id: int,
    sale_data: schemas.CreditSaleCreate,
    current_user: models.User = Depends(get_current_user),
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == sale_data.customer_id,
        models.Customer.business_id == business_id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found in this business."
        )

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
        total_amount = Decimal("0.00")

        for product_id, quantity in quantities.items():
            product = product_map[product_id]

            unit_price = Decimal(str(product.selling_price))

            line_total = (
                unit_price * quantity
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            total_amount += line_total

        total_amount = total_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        initial_payment = Decimal(
            str(sale_data.amount_paid)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if initial_payment > total_amount:
            raise HTTPException(
                status_code=400,
                detail="Initial payment cannot exceed the sale total."
            )

        new_sale = models.Sale(
            business_id=business_id,
            user_id=current_user.id,
            total_amount=total_amount
        )

        db.add(new_sale)
        db.flush()

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
                reason=f"Credit Sale SALE-{new_sale.id:06d}"
            ))

        balance = total_amount - initial_payment

        if balance <= Decimal("0.00"):
            initial_status = "paid"
        elif initial_payment > Decimal("0.00"):
            initial_status = "partially_paid"
        else:
            initial_status = "unpaid"

        new_credit_sale = models.CreditSale(
            business_id=business_id,
            customer_id=customer.id,
            sale_id=new_sale.id,
            total_amount=total_amount,
            amount_paid=initial_payment,
            balance_due=balance,
            status=initial_status,
            due_date=sale_data.due_date,
            user_id=current_user.id
        )

        db.add(new_credit_sale)
        db.flush()

        if initial_payment > Decimal("0.00"):
            db.add(models.CreditSalePayment(
                credit_sale_id=new_credit_sale.id,
                amount=initial_payment,
                payment_date=datetime.now(),
                reference="Initial payment",
                user_id=current_user.id
            ))

        db.commit()
        db.refresh(new_credit_sale)

        return get_credit_sale_response(
            db,
            new_credit_sale
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


@router.get(
    "/businesses/{business_id}/credit-sales",
    response_model=list[schemas.CreditSaleResponse]
)
def get_credit_sales(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    credit_sales = db.query(
        models.CreditSale
    ).filter(
        models.CreditSale.business_id == business_id
    ).order_by(
        models.CreditSale.created_at.desc()
    ).all()

    return [
        get_credit_sale_response(db, credit_sale)
        for credit_sale in credit_sales
    ]


@router.get(
    "/businesses/{business_id}/credit-sales/{credit_sale_id}",
    response_model=schemas.CreditSaleResponse
)
def get_credit_sale(
    business_id: int,
    credit_sale_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    credit_sale = db.query(models.CreditSale).filter(
        models.CreditSale.id == credit_sale_id,
        models.CreditSale.business_id == business_id
    ).first()

    if credit_sale is None:
        raise HTTPException(
            status_code=404,
            detail="Credit sale not found."
        )

    return get_credit_sale_response(db, credit_sale)


@router.post(
    "/businesses/{business_id}/credit-sales/{credit_sale_id}/payments",
    response_model=schemas.CreditSaleResponse,
    status_code=201
)
def record_credit_sale_payment(
    business_id: int,
    credit_sale_id: int,
    payment_data: schemas.CreditSalePaymentCreate,
    current_user: models.User = Depends(get_current_user),
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    credit_sale = db.query(models.CreditSale).filter(
        models.CreditSale.id == credit_sale_id,
        models.CreditSale.business_id == business_id
    ).first()

    if credit_sale is None:
        raise HTTPException(
            status_code=404,
            detail="Credit sale not found."
        )

    amount = Decimal(str(payment_data.amount)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if amount > credit_sale.balance_due:
        raise HTTPException(
            status_code=400,
            detail="Payment cannot exceed the outstanding balance."
        )

    try:
        new_payment = models.CreditSalePayment(
            credit_sale_id=credit_sale.id,
            amount=amount,
            payment_date=payment_data.payment_date,
            reference=payment_data.reference,
            user_id=current_user.id
        )

        credit_sale.amount_paid = (
            credit_sale.amount_paid + amount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        credit_sale.balance_due = (
            credit_sale.total_amount - credit_sale.amount_paid
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if credit_sale.balance_due <= Decimal("0.00"):
            credit_sale.status = "paid"
        elif (
            credit_sale.due_date is not None
            and credit_sale.due_date.date() < date.today()
        ):
            credit_sale.status = "overdue"
        else:
            credit_sale.status = "partially_paid"

        db.add(new_payment)
        db.commit()
        db.refresh(credit_sale)

        return get_credit_sale_response(
            db,
            credit_sale
        )

    except Exception:
        db.rollback()
        raise
