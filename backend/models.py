
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer, String, DateTime, Boolean,
    ForeignKey, UniqueConstraint, CheckConstraint,
    Numeric, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    business_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    phone: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    address: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    full_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class BusinessMembership(Base):
    __tablename__ = "business_memberships"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "business_id",
            name="uq_user_business"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"), nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "sku",
            name="uq_business_product_sku"
        ),
        CheckConstraint(
            "cost_price >= 0",
            name="ck_product_cost_price"
        ),
        CheckConstraint(
            "selling_price >= 0",
            name="ck_product_selling_price"
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_product_stock"
        ),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_product_low_stock"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"), nullable=False, index=True
    )

    sku: Mapped[str] = mapped_column(
        String(60), nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    selling_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    stock_quantity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    low_stock_threshold: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_stock_movement_quantity"
        ),
        CheckConstraint(
            "movement_type IN ('add', 'remove')",
            name="ck_stock_movement_type"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"), nullable=False, index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    movement_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    stock_before: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    stock_after: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    reason: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class Sale(Base):
    __tablename__ = "sales"

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0",
            name="ck_sale_total_amount"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"), nullable=False, index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_sale_item_quantity"
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_sale_item_unit_price"
        ),
        CheckConstraint(
            "cost_price >= 0",
            name="ck_sale_item_cost_price"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"), nullable=False, index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )

    product_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    sku: Mapped[str] = mapped_column(
        String(60), nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )


class Customer(Base):
    __tablename__ = "customers"

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "phone",
            name="uq_business_customer_phone"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    full_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    phone: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    address: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class Supplier(Base):
    __tablename__ = "suppliers"

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "phone",
            name="uq_business_supplier_phone"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    company_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    contact_person: Mapped[str | None] = mapped_column(
        String(150), nullable=True
    )

    phone: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    address: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )



class Purchase(Base):
    __tablename__ = "purchases"

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0",
            name="ck_purchase_total_amount"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"),
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    items: Mapped[list["PurchaseItem"]] = relationship(
        "PurchaseItem",
        back_populates="purchase",
        cascade="all, delete-orphan"
    )

    supplier_credit: Mapped["SupplierCredit | None"] = relationship(
        "SupplierCredit",
        back_populates="purchase",
        uselist=False
    )


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_purchase_item_quantity"
        ),
        CheckConstraint(
            "unit_cost >= 0",
            name="ck_purchase_item_unit_cost"
        ),
        CheckConstraint(
            "line_total >= 0",
            name="ck_purchase_item_line_total"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchases.id"),
        nullable=False,
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    purchase: Mapped["Purchase"] = relationship(
        "Purchase",
        back_populates="items"
    )


# =========================================
# =========================================

class SupplierCredit(Base):
    __tablename__ = "supplier_credits"

    __table_args__ = (
        UniqueConstraint(
            "purchase_id",
            name="uq_supplier_credit_purchase"
        ),
        CheckConstraint(
            "amount_paid >= 0",
            name="ck_supplier_credit_amount_paid"
        ),
        CheckConstraint(
            "balance_due >= 0",
            name="ck_supplier_credit_balance"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchases.id"),
        nullable=False,
        index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"),
        nullable=False,
        index=True
    )

    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=0,
        nullable=False
    )

    balance_due: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="unpaid",
        nullable=False
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    purchase: Mapped["Purchase"] = relationship(
        "Purchase",
        back_populates="supplier_credit"
    )

    payments: Mapped[list["SupplierCreditPayment"]] = relationship(
        "SupplierCreditPayment",
        back_populates="credit",
        cascade="all, delete-orphan"
    )


class SupplierCreditPayment(Base):
    __tablename__ = "supplier_credit_payments"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_supplier_credit_payment_amount"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    credit_id: Mapped[int] = mapped_column(
        ForeignKey("supplier_credits.id"),
        nullable=False,
        index=True
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    credit: Mapped["SupplierCredit"] = relationship(
        "SupplierCredit",
        back_populates="payments"
    )


# =========================================
# EXPENSES
# =========================================

class Expense(Base):
    __tablename__ = "expenses"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_expense_amount"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    description: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

# =========================================
# =========================================
# =========================================
# BORROWED LOANS
# =========================================

class BorrowedLoan(Base):
    __tablename__ = "borrowed_loans"

    __table_args__ = (
        CheckConstraint(
            "principal_amount > 0",
            name="ck_borrowed_loan_principal"
        ),
        CheckConstraint(
            "interest_rate >= 0",
            name="ck_borrowed_loan_interest"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    lender_name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    principal_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False
    )

    interest_type: Mapped[str] = mapped_column(
        String(20), default="flat", nullable=False
    )
    issue_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )

    notes: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    repayments: Mapped[list["BorrowedLoanRepayment"]] = relationship(
        "BorrowedLoanRepayment",
        back_populates="loan",
        cascade="all, delete-orphan"
    )


class BorrowedLoanRepayment(Base):
    __tablename__ = "borrowed_loan_repayments"

    __table_args__ = (
        CheckConstraint(
            "principal_paid >= 0",
            name="ck_borrowed_repayment_principal"
        ),
        CheckConstraint(
            "interest_paid >= 0",
            name="ck_borrowed_repayment_interest"
        ),
        CheckConstraint(
            "principal_paid + interest_paid > 0",
            name="ck_borrowed_repayment_total"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    loan_id: Mapped[int] = mapped_column(
        ForeignKey("borrowed_loans.id"),
        nullable=False,
        index=True
    )

    principal_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    interest_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    loan: Mapped["BorrowedLoan"] = relationship(
        "BorrowedLoan",
        back_populates="repayments"
    )


# =========================================
# CUSTOMER LOANS
# =========================================

class CustomerLoan(Base):
    __tablename__ = "customer_loans"

    __table_args__ = (
        CheckConstraint(
            "principal_amount > 0",
            name="ck_customer_loan_principal"
        ),
        CheckConstraint(
            "interest_rate >= 0",
            name="ck_customer_loan_interest"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    principal_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=False
    )

    interest_type: Mapped[str] = mapped_column(
        String(20), default="flat", nullable=False
    )

    issue_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )

    notes: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    repayments: Mapped[list["CustomerLoanRepayment"]] = relationship(
        "CustomerLoanRepayment",
        back_populates="loan",
        cascade="all, delete-orphan"
    )


class CustomerLoanRepayment(Base):
    __tablename__ = "customer_loan_repayments"

    __table_args__ = (
        CheckConstraint(
            "principal_paid >= 0",
            name="ck_customer_repayment_principal"
        ),
        CheckConstraint(
            "interest_paid >= 0",
            name="ck_customer_repayment_interest"
        ),
        CheckConstraint(
            "principal_paid + interest_paid > 0",
            name="ck_customer_repayment_total"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    loan_id: Mapped[int] = mapped_column(
        ForeignKey("customer_loans.id"),
        nullable=False,
        index=True
    )

    principal_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    interest_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    loan: Mapped["CustomerLoan"] = relationship(
        "CustomerLoan",
        back_populates="repayments"
    )

# =========================================
# CUSTOMER CREDIT SALES
# =========================================

class CreditSale(Base):
    __tablename__ = "credit_sales"

    __table_args__ = (
        CheckConstraint(
            "total_amount > 0",
            name="ck_credit_sale_total"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"),
        nullable=False,
        unique=True,
        index=True
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=0,
        nullable=False
    )

    balance_due: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="unpaid",
        nullable=False
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    payments: Mapped[list["CreditSalePayment"]] = relationship(
        "CreditSalePayment",
        back_populates="credit_sale",
        cascade="all, delete-orphan"
    )


class CreditSalePayment(Base):
    __tablename__ = "credit_sale_payments"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_credit_sale_payment_amount"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    credit_sale_id: Mapped[int] = mapped_column(
        ForeignKey("credit_sales.id"),
        nullable=False,
        index=True
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    credit_sale: Mapped["CreditSale"] = relationship(
        "CreditSale",
        back_populates="payments"
    )
