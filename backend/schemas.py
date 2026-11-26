from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BusinessCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    business_type: str = Field(min_length=2, max_length=100)


class BusinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    business_type: str
    phone: str | None
    email: str | None
    address: str | None
    created_at: datetime


class BusinessProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)

class OwnerRegistration(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    business_name: str = Field(min_length=2, max_length=150)
    business_type: str = Field(min_length=2, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    created_at: datetime


class OwnerRegistrationResponse(BaseModel):
    user: UserResponse
    business: BusinessResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StaffCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: Literal["manager", "cashier"]


class StaffResponse(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    business_id: int
    role: Literal["manager", "cashier"]
    is_active: bool


class StaffStatusUpdate(BaseModel):
    is_active: bool


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    cost_price: Decimal = Field(ge=0)
    selling_price: Decimal = Field(ge=0)
    stock_quantity: int = Field(ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
class ProductUpdate(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    cost_price: Decimal = Field(ge=0)
    selling_price: Decimal = Field(ge=0)
    low_stock_threshold: int = Field(ge=0)

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    sku: str
    name: str
    description: str | None
    cost_price: Decimal
    selling_price: Decimal
    stock_quantity: int
    low_stock_threshold: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None


class ProductCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    sku: str
    name: str
    description: str | None
    selling_price: Decimal
    stock_quantity: int
    low_stock_threshold: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
class StockAdjustmentCreate(BaseModel):
    movement_type: Literal["add", "remove"]
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=255)


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    product_id: int
    user_id: int
    movement_type: str
    quantity: int
    stock_before: int
    stock_after: int
    reason: str
    created_at: datetime
class SaleItemCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class SaleCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)


class SaleItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class SaleResponse(BaseModel):
    id: int
    business_id: int
    user_id: int
    total_amount: Decimal
    created_at: datetime
    items: list[SaleItemResponse]
class SaleReceiptItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class SaleReceiptResponse(BaseModel):
    receipt_number: str
    business_name: str
    cashier_name: str
    created_at: datetime
    total_amount: Decimal
    items: list[SaleReceiptItemResponse]
class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=5, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)


class CustomerUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=5, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    full_name: str
    phone: str
    email: str | None
    address: str | None
    created_at: datetime


class CustomerListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    full_name: str
    phone: str
    email: str | None
    address: str | None
    created_at: datetime
class SupplierCreate(BaseModel):
    company_name: str = Field(min_length=2, max_length=150)
    contact_person: str | None = Field(default=None, max_length=150)
    phone: str = Field(min_length=5, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)


class SupplierUpdate(BaseModel):
    company_name: str = Field(min_length=2, max_length=150)
    contact_person: str | None = Field(default=None, max_length=150)
    phone: str = Field(min_length=5, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    company_name: str
    contact_person: str | None
    phone: str
    email: str | None
    address: str | None
    created_at: datetime


class SupplierListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    company_name: str
    contact_person: str | None
    phone: str
    email: str | None
    address: str | None
    created_at: datetime
class PurchaseItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class SupplierCreditPaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_date: datetime
    reference: str | None = Field(default=None, max_length=100)
class SupplierCreditPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credit_id: int
    amount: Decimal
    payment_date: datetime
    reference: str | None
    user_id: int
    created_at: datetime


class SupplierCreditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_id: int
    business_id: int
    supplier_id: int
    amount_paid: Decimal
    balance_due: Decimal
    status: Literal["unpaid", "partially_paid", "paid", "overdue"]
    due_date: datetime | None
    user_id: int
    created_at: datetime
    payments: list[SupplierCreditPaymentResponse]
class PurchaseCreate(BaseModel):
    supplier_id: int = Field(gt=0)
    items: list[PurchaseItemCreate] = Field(min_length=1)
    payment_type: Literal["cash", "partial", "credit"] = "cash"
    amount_paid: Decimal | None = Field(default=None, ge=0)
    due_date: datetime | None = None
class PurchaseItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_cost: Decimal
    line_total: Decimal


class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    supplier_id: int
    user_id: int
    total_amount: Decimal
    created_at: datetime
    items: list[PurchaseItemResponse]
    supplier_credit: SupplierCreditResponse | None = None
# -----------------------------------------
# EXPENSE MANAGEMENT SCHEMAS
# -----------------------------------------

class ExpenseCreate(BaseModel):
    category: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=3, max_length=255)
    amount: Decimal = Field(gt=0)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    user_id: int
    category: str
    description: str
    amount: Decimal
    created_at: datetime
# =========================================
# LOAN MANAGEMENT SCHEMAS
# =========================================

# BORROWED LOANS

class BorrowedLoanCreate(BaseModel):
    lender_name: str = Field(min_length=2, max_length=150)
    principal_amount: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(ge=0, le=100)
    interest_type: Literal["flat", "monthly", "annual"] = "flat"
    issue_date: datetime
    due_date: datetime
    notes: str | None = Field(default=None, max_length=500)


class BorrowedLoanRepaymentCreate(BaseModel):
    principal_paid: Decimal = Field(ge=0)
    interest_paid: Decimal = Field(ge=0)
    payment_date: datetime
    reference: str | None = Field(default=None, max_length=100)


class BorrowedLoanRepaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    principal_paid: Decimal
    interest_paid: Decimal
    payment_date: datetime
    reference: str | None
    user_id: int
    created_at: datetime


class BorrowedLoanResponse(BaseModel):
    outstanding_principal: Decimal
    outstanding_interest: Decimal
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    lender_name: str
    principal_amount: Decimal
    interest_rate: Decimal
    interest_type: Literal["flat", "monthly", "annual"]
    issue_date: datetime
    due_date: datetime
    status: Literal["active", "paid", "overdue"]
    notes: str | None
    user_id: int
    created_at: datetime
    repayments: list[BorrowedLoanRepaymentResponse]


# CUSTOMER LOANS

class CustomerLoanCreate(BaseModel):
    customer_id: int = Field(gt=0)
    principal_amount: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(ge=0, le=100)
    interest_type: Literal["flat", "monthly", "annual"] = "flat"
    issue_date: datetime
    due_date: datetime
    notes: str | None = Field(default=None, max_length=500)


class CustomerLoanRepaymentCreate(BaseModel):
    principal_paid: Decimal = Field(ge=0)
    interest_paid: Decimal = Field(ge=0)
    payment_date: datetime
    reference: str | None = Field(default=None, max_length=100)


class CustomerLoanRepaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    principal_paid: Decimal
    interest_paid: Decimal
    payment_date: datetime
    reference: str | None
    user_id: int
    created_at: datetime


class CustomerLoanResponse(BaseModel):
    outstanding_principal: Decimal
    outstanding_interest: Decimal
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: int
    principal_amount: Decimal
    interest_rate: Decimal
    interest_type: Literal["flat", "monthly", "annual"]
    issue_date: datetime
    due_date: datetime
    status: Literal["active", "paid", "overdue"]
    notes: str | None
    user_id: int
    created_at: datetime
    repayments: list[CustomerLoanRepaymentResponse]

# =========================================
# CUSTOMER CREDIT SALES SCHEMAS
# =========================================

class CreditSaleCreate(BaseModel):
    customer_id: int = Field(gt=0)
    items: list[SaleItemCreate] = Field(min_length=1)
    amount_paid: Decimal = Field(default=Decimal("0.00"), ge=0)
    due_date: datetime | None = None


class CreditSalePaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_date: datetime
    reference: str | None = Field(default=None, max_length=100)


class CreditSalePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credit_sale_id: int
    amount: Decimal
    payment_date: datetime
    reference: str | None
    user_id: int
    created_at: datetime


class CreditSaleResponse(BaseModel):
    id: int
    business_id: int
    customer_id: int
    sale_id: int
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: Literal["unpaid", "partially_paid", "paid", "overdue"]
    due_date: datetime | None
    user_id: int
    created_at: datetime
    payments: list[CreditSalePaymentResponse]
