
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models
from .database import get_db
from .permissions import require_business_role


router = APIRouter(tags=["Financial Reports"])


@router.get("/businesses/{business_id}/reports/summary")
def get_business_report(
    business_id: int,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be after end date."
        )

    # SALES FILTER
    sales_query = db.query(models.Sale).filter(
        models.Sale.business_id == business_id
    )

    if start_date:
        sales_query = sales_query.filter(
            func.date(models.Sale.created_at) >= start_date.isoformat()
        )

    if end_date:
        sales_query = sales_query.filter(
            func.date(models.Sale.created_at) <= end_date.isoformat()
        )

    transaction_count = sales_query.count()

    total_revenue = (
        sales_query.with_entities(
            func.coalesce(func.sum(models.Sale.total_amount), 0)
        ).scalar()
        or Decimal("0.00")
    )

    sale_ids = sales_query.with_entities(
        models.Sale.id
    ).subquery()

    sale_id_query = db.query(sale_ids.c.id)

    # UNITS SOLD
    units_sold = db.query(
        func.coalesce(func.sum(models.SaleItem.quantity), 0)
    ).filter(
        models.SaleItem.sale_id.in_(sale_id_query)
    ).scalar() or 0

    # COST OF GOODS SOLD
    total_cogs = db.query(
        func.coalesce(
            func.sum(
                models.SaleItem.cost_price * models.SaleItem.quantity
            ),
            0
        )
    ).filter(
        models.SaleItem.sale_id.in_(sale_id_query)
    ).scalar() or Decimal("0.00")

    # GROSS PROFIT
    gross_profit = total_revenue - total_cogs

    # OPERATING EXPENSES
    expenses_query = db.query(models.Expense).filter(
        models.Expense.business_id == business_id
    )

    if start_date:
        expenses_query = expenses_query.filter(
            func.date(models.Expense.created_at) >= start_date.isoformat()
        )

    if end_date:
        expenses_query = expenses_query.filter(
            func.date(models.Expense.created_at) <= end_date.isoformat()
        )

    total_expenses = (
        expenses_query.with_entities(
            func.coalesce(func.sum(models.Expense.amount), 0)
        ).scalar()
        or Decimal("0.00")
    )

    # OPERATING PROFIT
    operating_profit = gross_profit - total_expenses

    # BORROWED LOAN INTEREST EXPENSE
    # Only interest paid is an expense. Principal repayments are excluded.
    borrowed_interest_query = db.query(
        models.BorrowedLoanRepayment
    ).join(
        models.BorrowedLoan,
        models.BorrowedLoan.id == models.BorrowedLoanRepayment.loan_id
    ).filter(
        models.BorrowedLoan.business_id == business_id
    )

    if start_date:
        borrowed_interest_query = borrowed_interest_query.filter(
            func.date(
                models.BorrowedLoanRepayment.payment_date
            ) >= start_date.isoformat()
        )

    if end_date:
        borrowed_interest_query = borrowed_interest_query.filter(
            func.date(
                models.BorrowedLoanRepayment.payment_date
            ) <= end_date.isoformat()
        )

    borrowed_loan_interest_expense = (
        borrowed_interest_query.with_entities(
            func.coalesce(
                func.sum(models.BorrowedLoanRepayment.interest_paid),
                0
            )
        ).scalar()
        or Decimal("0.00")
    )

    # CUSTOMER LOAN INTEREST INCOME
    # Only interest received is income. Principal repayments are excluded.
    customer_interest_query = db.query(
        models.CustomerLoanRepayment
    ).join(
        models.CustomerLoan,
        models.CustomerLoan.id == models.CustomerLoanRepayment.loan_id
    ).filter(
        models.CustomerLoan.business_id == business_id
    )

    if start_date:
        customer_interest_query = customer_interest_query.filter(
            func.date(
                models.CustomerLoanRepayment.payment_date
            ) >= start_date.isoformat()
        )

    if end_date:
        customer_interest_query = customer_interest_query.filter(
            func.date(
                models.CustomerLoanRepayment.payment_date
            ) <= end_date.isoformat()
        )

    customer_loan_interest_income = (
        customer_interest_query.with_entities(
            func.coalesce(
                func.sum(models.CustomerLoanRepayment.interest_paid),
                0
            )
        ).scalar()
        or Decimal("0.00")
    )

    # PROFIT AFTER FINANCE INCOME AND EXPENSES
    profit_after_finance = (
        operating_profit
        + customer_loan_interest_income
        - borrowed_loan_interest_expense
    )

    # TOP FIVE PRODUCTS
    top_products = db.query(
        models.SaleItem.product_name.label("product_name"),
        models.SaleItem.sku.label("sku"),
        func.sum(models.SaleItem.quantity).label("quantity_sold"),
        func.sum(models.SaleItem.line_total).label("sales_value")
    ).filter(
        models.SaleItem.sale_id.in_(sale_id_query)
    ).group_by(
        models.SaleItem.product_name,
        models.SaleItem.sku
    ).order_by(
        func.sum(models.SaleItem.quantity).desc()
    ).limit(5).all()

    # AVERAGE TRANSACTION
    average_transaction = (
        total_revenue / transaction_count
        if transaction_count else Decimal("0.00")
    )

    return {
        "total_revenue": total_revenue,
        "total_cogs": total_cogs,
        "gross_profit": gross_profit,
        "total_expenses": total_expenses,
        "operating_profit": operating_profit,
        "borrowed_loan_interest_expense": borrowed_loan_interest_expense,
        "customer_loan_interest_income": customer_loan_interest_income,
        "profit_after_finance": profit_after_finance,
        "transaction_count": transaction_count,
        "units_sold": units_sold,
        "average_transaction": average_transaction,
        "top_products": [
            {
                "product_name": product.product_name,
                "sku": product.sku,
                "quantity_sold": product.quantity_sold,
                "sales_value": product.sales_value
            }
            for product in top_products
        ]
    }
