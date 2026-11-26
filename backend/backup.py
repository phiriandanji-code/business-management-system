
import json
import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db
from .permissions import require_business_role


router = APIRouter(tags=["Business Backup and Restore"])

BACKUP_ROOT = Path(__file__).resolve().parent.parent / "business_backups"

# Only these business-specific tables are included.
# Global users and business memberships are deliberately excluded.

TABLES = [
    "products",
    "customers",
    "suppliers",
    "sales",
    "purchases",
    "borrowed_loans",
    "customer_loans",
    "expenses",
    "stock_movements",
    "supplier_credits",
    "credit_sales",
    "purchase_items",
    "sale_items",
    "supplier_credit_payments",
    "borrowed_loan_repayments",
    "customer_loan_repayments",
    "credit_sale_payments",
]

DIRECT_TABLES = [
    "products",
    "customers",
    "suppliers",
    "sales",
    "purchases",
    "borrowed_loans",
    "customer_loans",
    "expenses",
    "stock_movements",
    "supplier_credits",
    "credit_sales",
]

CHILD_QUERIES = {
    "purchase_items": """
        SELECT * FROM purchase_items
        WHERE purchase_id IN (
            SELECT id FROM purchases WHERE business_id = :business_id
        )
    """,
    "sale_items": """
        SELECT * FROM sale_items
        WHERE sale_id IN (
            SELECT id FROM sales WHERE business_id = :business_id
        )
    """,
    "supplier_credit_payments": """
        SELECT * FROM supplier_credit_payments
        WHERE credit_id IN (
            SELECT id FROM supplier_credits WHERE business_id = :business_id
        )
    """,
    "borrowed_loan_repayments": """
        SELECT * FROM borrowed_loan_repayments
        WHERE loan_id IN (
            SELECT id FROM borrowed_loans WHERE business_id = :business_id
        )
    """,
    "customer_loan_repayments": """
        SELECT * FROM customer_loan_repayments
        WHERE loan_id IN (
            SELECT id FROM customer_loans WHERE business_id = :business_id
        )
    """,
    "credit_sale_payments": """
        SELECT * FROM credit_sale_payments
        WHERE credit_sale_id IN (
            SELECT id FROM credit_sales WHERE business_id = :business_id
        )
    """,
}

DELETE_ORDER = [
    ("borrowed_loan_repayments", "loan_id", "borrowed_loans"),
    ("customer_loan_repayments", "loan_id", "customer_loans"),
    ("credit_sale_payments", "credit_sale_id", "credit_sales"),
    ("supplier_credit_payments", "credit_id", "supplier_credits"),
    ("purchase_items", "purchase_id", "purchases"),
    ("sale_items", "sale_id", "sales"),
]

PARENT_DELETE_ORDER = [
    "credit_sales",
    "supplier_credits",
    "stock_movements",
    "expenses",
    "customer_loans",
    "borrowed_loans",
    "purchases",
    "sales",
    "suppliers",
    "customers",
    "products",
]

INSERT_ORDER = [
    "products",
    "customers",
    "suppliers",
    "sales",
    "purchases",
    "borrowed_loans",
    "customer_loans",
    "expenses",
    "stock_movements",
    "supplier_credits",
    "credit_sales",
    "purchase_items",
    "sale_items",
    "supplier_credit_payments",
    "borrowed_loan_repayments",
    "customer_loan_repayments",
    "credit_sale_payments",
]


def backup_folder(business_id: int) -> Path:
    return BACKUP_ROOT / f"business_{business_id}"


def get_backup_path(business_id: int, backup_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", backup_id):
        raise HTTPException(status_code=404, detail="Backup not found.")

    path = backup_folder(business_id) / f"{backup_id}.json"

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Backup not found.")

    return path


def collect_business_data(db: Session, business_id: int) -> dict:
    business = db.execute(
        text("SELECT * FROM businesses WHERE id = :business_id"),
        {"business_id": business_id}
    ).mappings().first()

    if business is None:
        raise HTTPException(status_code=404, detail="Business not found.")

    tables = {}

    for table in DIRECT_TABLES:
        rows = db.execute(
            text(f"SELECT * FROM {table} WHERE business_id = :business_id"),
            {"business_id": business_id}
        ).mappings().all()

        tables[table] = [dict(row) for row in rows]

    for table, query in CHILD_QUERIES.items():
        rows = db.execute(
            text(query),
            {"business_id": business_id}
        ).mappings().all()

        tables[table] = [dict(row) for row in rows]

    return {
        "schema_version": 1,
        "business_id": business_id,
        "business": dict(business),
        "tables": tables,
    }


def create_backup_file(
    db: Session,
    business_id: int,
    backup_type: str = "manual"
) -> dict:
    backup_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()

    payload = collect_business_data(db, business_id)
    payload["backup_id"] = backup_id
    payload["created_at"] = created_at
    payload["backup_type"] = backup_type

    folder = backup_folder(business_id)
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / f"{backup_id}.json"
    temporary_path = folder / f"{backup_id}.tmp"

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

        os.replace(temporary_path, path)

    except OSError:
        if temporary_path.exists():
            temporary_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Unable to save the backup file."
        )

    return {
        "backup_id": backup_id,
        "created_at": created_at,
        "backup_type": backup_type,
        "file_name": path.name,
        "size_bytes": path.stat().st_size,
    }


def table_columns(db: Session, table: str) -> set:
    rows = db.execute(
        text(f"PRAGMA table_info({table})")
    ).mappings().all()

    return {row["name"] for row in rows}


def validate_backup(
    db: Session,
    payload: dict,
    business_id: int,
    backup_id: str
) -> None:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid backup file.")

    if payload.get("schema_version") != 1:
        raise HTTPException(
            status_code=400,
            detail="Unsupported backup version."
        )

    if payload.get("business_id") != business_id:
        raise HTTPException(
            status_code=400,
            detail="This backup belongs to a different business."
        )

    if payload.get("backup_id") != backup_id:
        raise HTTPException(status_code=400, detail="Invalid backup identity.")

    business = payload.get("business")
    tables = payload.get("tables")

    if not isinstance(business, dict) or not isinstance(tables, dict):
        raise HTTPException(status_code=400, detail="Invalid backup structure.")

    if business.get("id") != business_id:
        raise HTTPException(status_code=400, detail="Invalid business record.")

    if set(business) != table_columns(db, "businesses"):
        raise HTTPException(
            status_code=400,
            detail="Business profile structure does not match."
        )

    if set(tables) != set(TABLES):
        raise HTTPException(
            status_code=400,
            detail="Backup is missing required business data."
        )

    for table in TABLES:
        rows = tables[table]

        if not isinstance(rows, list):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid records in {table}."
            )

        expected_columns = table_columns(db, table)

        for row in rows:
            if not isinstance(row, dict) or set(row) != expected_columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid record structure in {table}."
                )

            if table in DIRECT_TABLES and row.get("business_id") != business_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"A record in {table} belongs to another business."
                )

    # Check that all user references still exist.
    existing_users = {
        row[0] for row in db.execute(
            text("SELECT id FROM users")
        ).all()
    }

    for table in TABLES:
        for row in tables[table]:
            user_id = row.get("user_id")

            if user_id is not None and user_id not in existing_users:
                raise HTTPException(
                    status_code=400,
                    detail="A user linked to this backup no longer exists."
                )

    # Validate relationships between records in the backup.
    ids = {
        table: {row["id"] for row in tables[table]}
        for table in TABLES
    }

    references = [
        ("stock_movements", "product_id", "products"),
        ("sale_items", "sale_id", "sales"),
        ("sale_items", "product_id", "products"),
        ("purchase_items", "purchase_id", "purchases"),
        ("purchase_items", "product_id", "products"),
        ("supplier_credits", "purchase_id", "purchases"),
        ("supplier_credits", "supplier_id", "suppliers"),
        ("supplier_credit_payments", "credit_id", "supplier_credits"),
        ("borrowed_loan_repayments", "loan_id", "borrowed_loans"),
        ("customer_loan_repayments", "loan_id", "customer_loans"),
        ("credit_sale_payments", "credit_sale_id", "credit_sales"),
        ("customer_loans", "customer_id", "customers"),
        ("credit_sales", "customer_id", "customers"),
        ("credit_sales", "sale_id", "sales"),
        ("purchases", "supplier_id", "suppliers"),
    ]

    for child_table, column, parent_table in references:
        for row in tables[child_table]:
            reference_id = row.get(column)

            if reference_id is not None and reference_id not in ids[parent_table]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid relationship in {child_table}."
                )

    # Ensure the target business still exists.
    exists = db.execute(
        text("SELECT id FROM businesses WHERE id = :business_id"),
        {"business_id": business_id}
    ).first()

    if exists is None:
        raise HTTPException(status_code=404, detail="Business not found.")


def delete_current_business_records(
    db: Session,
    business_id: int
) -> None:
    parameters = {"business_id": business_id}

    for child_table, foreign_key, parent_table in DELETE_ORDER:
        db.execute(
            text(
                f"DELETE FROM {child_table} "
                f"WHERE {foreign_key} IN "
                f"(SELECT id FROM {parent_table} "
                f"WHERE business_id = :business_id)"
            ),
            parameters
        )

    for table in PARENT_DELETE_ORDER:
        db.execute(
            text(f"DELETE FROM {table} WHERE business_id = :business_id"),
            parameters
        )


def insert_backup_records(
    db: Session,
    tables: dict
) -> None:
    for table in INSERT_ORDER:
        rows = tables[table]

        if not rows:
            continue

        columns = list(rows[0].keys())

        column_sql = ", ".join(columns)
        value_sql = ", ".join(f":{column}" for column in columns)

        query = text(
            f"INSERT INTO {table} ({column_sql}) VALUES ({value_sql})"
        )

        for row in rows:
            db.execute(query, row)


@router.post("/businesses/{business_id}/backups", status_code=201)
def create_business_backup(
    business_id: int,
    membership=Depends(require_business_role("owner")),
    db: Session = Depends(get_db)
):
    return create_backup_file(db, business_id)


@router.get("/businesses/{business_id}/backups")
def list_business_backups(
    business_id: int,
    membership=Depends(require_business_role("owner"))
):
    folder = backup_folder(business_id)

    if not folder.exists():
        return []

    backups = []

    for path in folder.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as file:
                payload = json.load(file)

            backups.append({
                "backup_id": payload.get("backup_id"),
                "created_at": payload.get("created_at"),
                "backup_type": payload.get("backup_type", "manual"),
                "file_name": path.name,
                "size_bytes": path.stat().st_size,
            })

        except (OSError, ValueError):
            continue

    return sorted(
        backups,
        key=lambda item: item.get("created_at") or "",
        reverse=True
    )


@router.get("/businesses/{business_id}/backups/{backup_id}/download")
def download_business_backup(
    business_id: int,
    backup_id: str,
    membership=Depends(require_business_role("owner"))
):
    path = get_backup_path(business_id, backup_id)

    return FileResponse(
        path=str(path),
        media_type="application/json",
        filename=f"business_{business_id}_{backup_id}.json"
    )


@router.post("/businesses/{business_id}/backups/{backup_id}/restore")
def restore_business_backup(
    business_id: int,
    backup_id: str,
    membership=Depends(require_business_role("owner")),
    db: Session = Depends(get_db)
):
    path = get_backup_path(business_id, backup_id)

    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

    except (OSError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Unable to read the selected backup."
        )

    validate_backup(db, payload, business_id, backup_id)

    safety_backup = create_backup_file(
        db,
        business_id,
        backup_type="pre_restore_safety"
    )

    try:
        delete_current_business_records(db, business_id)

        business_data = payload["business"]
        update_columns = [
            column for column in business_data
            if column != "id"
        ]

        assignments = ", ".join(
            f"{column} = :{column}" for column in update_columns
        )

        db.execute(
            text(
                f"UPDATE businesses SET {assignments} "
                "WHERE id = :id"
            ),
            business_data
        )

        insert_backup_records(db, payload["tables"])

        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Restore failed. The database changes were rolled back. "
                "The safety backup was retained."
            )
        )

    return {
        "message": "Business backup restored successfully.",
        "business_id": business_id,
        "safety_backup_id": safety_backup["backup_id"],
    }
