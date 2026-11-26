
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .permissions import require_business_role


router = APIRouter(tags=["Expense Management"])


# -----------------------------------------
# RECORD A NEW EXPENSE
# -----------------------------------------

@router.post(
    "/businesses/{business_id}/expenses",
    response_model=schemas.ExpenseResponse,
    status_code=201
)
def create_expense(
    business_id: int,
    expense: schemas.ExpenseCreate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    new_expense = models.Expense(
        business_id=business_id,
        user_id=membership.user_id,
        category=expense.category.strip(),
        description=expense.description.strip(),
        amount=expense.amount
    )

    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

    return new_expense


# -----------------------------------------
# VIEW BUSINESS EXPENSES
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/expenses",
    response_model=list[schemas.ExpenseResponse]
)
def get_expenses(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    return db.query(models.Expense).filter(
        models.Expense.business_id == business_id
    ).order_by(
        models.Expense.created_at.desc()
    ).all()


# -----------------------------------------
# VIEW ONE EXPENSE
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/expenses/{expense_id}",
    response_model=schemas.ExpenseResponse
)
def get_expense(
    business_id: int,
    expense_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    expense = db.query(models.Expense).filter(
        models.Expense.id == expense_id,
        models.Expense.business_id == business_id
    ).first()

    if expense is None:
        raise HTTPException(
            status_code=404,
            detail="Expense not found in this business."
        )

    return expense
