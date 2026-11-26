from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from . import models, schemas
from .permissions import require_business_role


router = APIRouter(tags=["Loan Management"])

ZERO = Decimal("0.00")
ONE_HUNDRED = Decimal("100")
CENT = Decimal("0.01")


# ==================================================
# GENERAL INTEREST AND BALANCE CALCULATIONS
# ==================================================

def money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def normalise_datetime(value):
    """Convert timezone-aware datetimes to naive datetimes."""
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def get_repayment_date(repayment):
    return normalise_datetime(repayment.payment_date).date()


def calculate_loan_balances(loan, as_of=None):
    """
    Calculate outstanding principal and interest.

    Flat:
        One-time interest on the original principal.

    Monthly:
        Reducing-balance interest using the monthly rate,
        divided by the number of days in each calendar month.

    Annual:
        Reducing-balance interest using the annual rate,
        divided by 365 or 366 days.

    Monthly and annual interest starts accruing the day
    after the loan issue date.
    """
    if as_of is None:
        as_of = datetime.now()

    as_of = normalise_datetime(as_of)
    issue_date = normalise_datetime(loan.issue_date)

    original_principal = money(loan.principal_amount)
    rate = Decimal(str(loan.interest_rate))
    interest_type = loan.interest_type

    repayments = sorted(
        [
            repayment
            for repayment in loan.repayments
            if normalise_datetime(repayment.payment_date) <= as_of
        ],
        key=lambda repayment: (
            get_repayment_date(repayment),
            repayment.id or 0
        )
    )

    total_principal_paid = sum(
        (money(item.principal_paid) for item in repayments),
        ZERO
    )

    total_interest_paid = sum(
        (money(item.interest_paid) for item in repayments),
        ZERO
    )

    outstanding_principal = max(
        ZERO,
        original_principal - total_principal_paid
    )

    # Flat interest: charged once for the entire loan term.
    if interest_type == "flat":
        total_interest = money(
            original_principal * rate / ONE_HUNDRED
        )

        outstanding_interest = max(
            ZERO,
            total_interest - total_interest_paid
        )

        return {
            "outstanding_principal": money(outstanding_principal),
            "outstanding_interest": money(outstanding_interest)
        }

    # Reducing-balance interest calculation.
    balance = original_principal
    accrued_interest = ZERO

    start_date = issue_date.date()
    end_date = as_of.date()

    repayments_by_date = {}

    for repayment in repayments:
        payment_day = get_repayment_date(repayment)
        repayments_by_date.setdefault(payment_day, []).append(repayment)

    if end_date >= start_date:
        current_day = start_date

        while current_day <= end_date:
            if balance <= ZERO:
                break

            # Interest starts accruing the day after issue.
            if current_day > start_date:

                if interest_type == "monthly":
                    days_in_period = monthrange(
                        current_day.year,
                        current_day.month
                    )[1]

                    daily_interest = (
                        balance * rate
                        / ONE_HUNDRED
                        / Decimal(days_in_period)
                    )

                elif interest_type == "annual":
                    days_in_year = (
                        366 if monthrange(current_day.year, 2)[1] == 29
                        else 365
                    )

                    daily_interest = (
                        balance * rate
                        / ONE_HUNDRED
                        / Decimal(days_in_year)
                    )

                else:
                    raise ValueError("Unsupported interest type.")

                accrued_interest += daily_interest

            # Apply principal repayments after that day's interest.
            for repayment in repayments_by_date.get(current_day, []):
                balance -= money(repayment.principal_paid)
                balance = max(ZERO, balance)

            current_day += timedelta(days=1)

    outstanding_interest = max(
        ZERO,
        money(accrued_interest) - total_interest_paid
    )

    return {
        "outstanding_principal": money(balance),
        "outstanding_interest": money(outstanding_interest)
    }


# ==================================================
# LOAN STATUS AND RESPONSE HELPERS
# ==================================================

def update_loan_status(loan, as_of=None):
    if as_of is None:
        as_of = datetime.now()

    as_of = normalise_datetime(as_of)

    balances = calculate_loan_balances(loan, as_of)

    if (
        balances["outstanding_principal"] <= ZERO
        and balances["outstanding_interest"] <= ZERO
    ):
        loan.status = "paid"

    elif as_of.date() > normalise_datetime(loan.due_date).date():
        loan.status = "overdue"

    else:
        loan.status = "active"

    return loan.status


def build_loan_response(loan, response_schema, as_of=None):
    balances = calculate_loan_balances(loan, as_of)

    data = {
        "id": loan.id,
        "business_id": loan.business_id,
        "principal_amount": loan.principal_amount,
        "interest_rate": loan.interest_rate,
        "interest_type": loan.interest_type,
        "issue_date": loan.issue_date,
        "due_date": loan.due_date,
        "status": update_loan_status(loan, as_of),
        "notes": loan.notes,
        "user_id": loan.user_id,
        "created_at": loan.created_at,
        "repayments": loan.repayments,
        "outstanding_principal": balances["outstanding_principal"],
        "outstanding_interest": balances["outstanding_interest"]
    }

    if isinstance(loan, models.BorrowedLoan):
        data["lender_name"] = loan.lender_name

    elif isinstance(loan, models.CustomerLoan):
        data["customer_id"] = loan.customer_id

    return response_schema.model_validate(data)


def validate_loan_dates(issue_date, due_date):
    issue_date = normalise_datetime(issue_date)
    due_date = normalise_datetime(due_date)

    if due_date <= issue_date:
        raise HTTPException(
            status_code=400,
            detail="The loan due date must be after the issue date."
        )


def validate_new_repayment(loan, principal_paid, interest_paid, payment_date):
    payment_date = normalise_datetime(payment_date)
    issue_date = normalise_datetime(loan.issue_date)

    if payment_date < issue_date:
        raise HTTPException(
            status_code=400,
            detail="Payment date cannot be before the loan issue date."
        )

    if payment_date > datetime.now():
        raise HTTPException(
            status_code=400,
            detail="Payment date cannot be in the future."
        )

    if money(principal_paid) == ZERO and money(interest_paid) == ZERO:
        raise HTTPException(
            status_code=400,
            detail="Enter a principal payment, an interest payment, or both."
        )

    existing_repayments = sorted(
        loan.repayments,
        key=lambda item: normalise_datetime(item.payment_date)
    )

    if existing_repayments:
        latest_payment_date = normalise_datetime(
            existing_repayments[-1].payment_date
        )

        if payment_date < latest_payment_date:
            raise HTTPException(
                status_code=400,
                detail="Payment date cannot be before an existing repayment."
            )

    balances = calculate_loan_balances(loan, payment_date)

    if money(principal_paid) > balances["outstanding_principal"]:
        raise HTTPException(
            status_code=400,
            detail="Principal payment exceeds the outstanding principal."
        )

    if money(interest_paid) > balances["outstanding_interest"]:
        raise HTTPException(
            status_code=400,
            detail="Interest payment exceeds the outstanding interest."
        )


def get_loan_or_404(db, loan_model, business_id, loan_id):
    loan = db.query(loan_model).filter(
        loan_model.id == loan_id,
        loan_model.business_id == business_id
    ).first()

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found in this business."
        )

    return loan


# ==================================================
# BORROWED LOANS
# ==================================================

@router.post(
    "/businesses/{business_id}/borrowed-loans",
    response_model=schemas.BorrowedLoanResponse,
    status_code=201
)
def create_borrowed_loan(
    business_id: int,
    loan_data: schemas.BorrowedLoanCreate,
    membership=Depends(require_business_role("owner", "manager")),
    db: Session = Depends(get_db)
):
    validate_loan_dates(
        loan_data.issue_date,
        loan_data.due_date
    )

    loan = models.BorrowedLoan(
        business_id=business_id,
        lender_name=loan_data.lender_name,
        principal_amount=money(loan_data.principal_amount),
        interest_rate=loan_data.interest_rate,
        interest_type=loan_data.interest_type,
        issue_date=loan_data.issue_date,
        due_date=loan_data.due_date,
        status="active",
        notes=loan_data.notes,
        user_id=membership.user_id
    )

    try:
        db.add(loan)
        db.commit()
        db.refresh(loan)

        return build_loan_response(
            loan,
            schemas.BorrowedLoanResponse
        )

    except Exception:
        db.rollback()
        raise


@router.get(
    "/businesses/{business_id}/borrowed-loans",
    response_model=list[schemas.BorrowedLoanResponse]
)
def get_borrowed_loans(
    business_id: int,
    membership=Depends(require_business_role("owner", "manager")),
    db: Session = Depends(get_db)
):
    loans = db.query(models.BorrowedLoan).filter(
        models.BorrowedLoan.business_id == business_id
    ).order_by(
        models.BorrowedLoan.created_at.desc()
    ).all()

    responses = [
        build_loan_response(loan, schemas.BorrowedLoanResponse)
        for loan in loans
    ]

    db.commit()
    return responses


@router.get(
    "/businesses/{business_id}/borrowed-loans/{loan_id}",
    response_model=schemas.BorrowedLoanResponse
)
def get_borrowed_loan(
    business_id: int,
    loan_id: int,
    membership=Depends(require_business_role("owner", "manager")),
    db: Session = Depends(get_db)
):
    loan = get_loan_or_404(
        db,
        models.BorrowedLoan,
        business_id,
        loan_id
    )

    response = build_loan_response(
        loan,
        schemas.BorrowedLoanResponse
    )

    db.commit()
    return response


@router.post(
    "/businesses/{business_id}/borrowed-loans/{loan_id}/repayments",
    response_model=schemas.BorrowedLoanResponse,
    status_code=201
)
def record_borrowed_loan_repayment(
    business_id: int,
    loan_id: int,
    repayment_data: schemas.BorrowedLoanRepaymentCreate,
    membership=Depends(require_business_role("owner", "manager")),
    db: Session = Depends(get_db)
):
    loan = get_loan_or_404(
        db,
        models.BorrowedLoan,
        business_id,
        loan_id
    )

    validate_new_repayment(
        loan,
        repayment_data.principal_paid,
        repayment_data.interest_paid,
        repayment_data.payment_date
    )

    repayment = models.BorrowedLoanRepayment(
        loan_id=loan.id,
        principal_paid=money(repayment_data.principal_paid),
        interest_paid=money(repayment_data.interest_paid),
        payment_date=repayment_data.payment_date,
        reference=repayment_data.reference,
        user_id=membership.user_id
    )

    try:
        db.add(repayment)
        db.flush()

        update_loan_status(loan)

        db.commit()
        db.refresh(loan)

        return build_loan_response(
            loan,
            schemas.BorrowedLoanResponse
        )

    except Exception:
        db.rollback()
        raise


# ==================================================
# CUSTOMER LOANS
# ==================================================

@router.post(
    "/businesses/{business_id}/customer-loans",
    response_model=schemas.CustomerLoanResponse,
    status_code=201
)
def create_customer_loan(
    business_id: int,
    loan_data: schemas.CustomerLoanCreate,
    membership=Depends(require_business_role("owner", "manager")),
    db: Session = Depends(get_db)
):
    validate_loan_dates(
        loan_data.issue_date,
        loan_data.due_date
    )

    customer = db.query(models.Customer).filter(
        models.Customer.id == loan_data.customer_id,
        models.Customer.business_id == business_id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found in this business."
        )

    loan = models.CustomerLoan(
        business_id=business_id,
        customer_id=loan_data.customer_id,
        principal_amount=money(loan_data.principal_amount),
        interest_rate=loan_data.interest_rate,
        interest_type=loan_data.interest_type,
        issue_date=loan_data.issue_date,
        due_date=loan_data.due_date,
        status="active",
        notes=loan_data.notes,
        user_id=membership.user_id
    )

    try:
        db.add(loan)
        db.commit()
        db.refresh(loan)

        return build_loan_response(
            loan,
            schemas.CustomerLoanResponse
        )

    except Exception:
        db.rollback()
        raise


@router.get(
    "/businesses/{business_id}/customer-loans",
    response_model=list[schemas.CustomerLoanResponse]
)
def get_customer_loans(
    business_id: int,
    membership=Depends(require_business_role("owner", "manager")),
    db: Session = Depends(get_db)
):
    loans = db.query(models.CustomerLoan).filter(
        models.CustomerLoan.business_id == business_id
    ).order_by(
        models.CustomerLoan.created_at.desc()
    ).all()

    responses = [
        build_loan_response(loan, schemas.CustomerLoanResponse)
        for loan in loans
    ]

    db.commit()
    return responses


@router.get(
    "/businesses/{business_id}/customer-loans/{loan_id}",
    response_model=schemas.CustomerLoanResponse
)
def get_customer_loan(
    business_id: int,
    loan_id: int,
    membership=Depends(require_business_role("owner", "manager")),
    db: Session = Depends(get_db)
):
    loan = get_loan_or_404(
        db,
        models.CustomerLoan,
        business_id,
        loan_id
    )

    response = build_loan_response(
        loan,
        schemas.CustomerLoanResponse
    )

    db.commit()
    return response


@router.post(
    "/businesses/{business_id}/customer-loans/{loan_id}/repayments",
    response_model=schemas.CustomerLoanResponse,
    status_code=201
)
def record_customer_loan_repayment(
    business_id: int,
    loan_id: int,
    repayment_data: schemas.CustomerLoanRepaymentCreate,
    membership=Depends(require_business_role("owner", "manager")),
    db: Session = Depends(get_db)
):
    loan = get_loan_or_404(
        db,
        models.CustomerLoan,
        business_id,
        loan_id
    )

    validate_new_repayment(
        loan,
        repayment_data.principal_paid,
        repayment_data.interest_paid,
        repayment_data.payment_date
    )

    repayment = models.CustomerLoanRepayment(
        loan_id=loan.id,
        principal_paid=money(repayment_data.principal_paid),
        interest_paid=money(repayment_data.interest_paid),
        payment_date=repayment_data.payment_date,
        reference=repayment_data.reference,
        user_id=membership.user_id
    )

    try:
        db.add(repayment)
        db.flush()

        update_loan_status(loan)

        db.commit()
        db.refresh(loan)

        return build_loan_response(
            loan,
            schemas.CustomerLoanResponse
        )

    except Exception:
        db.rollback()
        raise