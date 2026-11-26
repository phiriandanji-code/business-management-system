from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models, schemas
from .database import get_db
from .auth import get_current_user
from .permissions import require_business_role


router = APIRouter(tags=["Products and Inventory"])


# -----------------------------------------
# VIEW BUSINESS PRODUCTS
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/products",
    response_model=list[schemas.ProductCatalogResponse]
)
def get_products(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    return db.query(models.Product).filter(
        models.Product.business_id == business_id,
        models.Product.is_active == True
    ).order_by(models.Product.name).all()


# -----------------------------------------
# REGISTER A NEW PRODUCT
# -----------------------------------------

@router.post(
    "/businesses/{business_id}/products",
    response_model=schemas.ProductResponse,
    status_code=201
)
def create_product(
    business_id: int,
    product: schemas.ProductCreate,
    current_user: models.User = Depends(get_current_user),
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    new_product = models.Product(
        business_id=business_id,
        sku=product.sku.strip(),
        name=product.name.strip(),
        description=product.description,
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        stock_quantity=product.stock_quantity,
        low_stock_threshold=product.low_stock_threshold
    )

    try:
        db.add(new_product)
        db.flush()

        if product.stock_quantity > 0:
            opening_movement = models.StockMovement(
                business_id=business_id,
                product_id=new_product.id,
                user_id=current_user.id,
                movement_type="add",
                quantity=product.stock_quantity,
                stock_before=0,
                stock_after=product.stock_quantity,
                reason="Opening stock"
            )

            db.add(opening_movement)

        db.commit()
        db.refresh(new_product)

        return new_product

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This SKU already exists in your business."
        )
# -----------------------------------------
# UPDATE EXISTING PRODUCT
# -----------------------------------------

@router.put(
    "/businesses/{business_id}/products/{product_id}",
    response_model=schemas.ProductResponse
)
def update_product(
    business_id: int,
    product_id: int,
    product_update: schemas.ProductUpdate,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.business_id == business_id,
        models.Product.is_active == True
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    product.sku = product_update.sku.strip()
    product.name = product_update.name.strip()
    product.description = product_update.description
    product.cost_price = product_update.cost_price
    product.selling_price = product_update.selling_price
    product.low_stock_threshold = product_update.low_stock_threshold

    try:
        db.commit()
        db.refresh(product)
        return product

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This SKU already exists in your business."
        )
# -----------------------------------------
# DEACTIVATE PRODUCT
# -----------------------------------------

@router.patch(
    "/businesses/{business_id}/products/{product_id}/deactivate",
    response_model=schemas.ProductResponse
)
def deactivate_product(
    business_id: int,
    product_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.business_id == business_id,
        models.Product.is_active == True
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found or already deactivated."
        )

    product.is_active = False

    db.commit()
    db.refresh(product)

    return product
# -----------------------------------------
# VIEW LOW-STOCK PRODUCTS
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/low-stock-products",
    response_model=list[schemas.ProductCatalogResponse]
)
def get_low_stock_products(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager", "cashier")
    ),
    db: Session = Depends(get_db)
):
    return db.query(models.Product).filter(
        models.Product.business_id == business_id,
        models.Product.is_active == True,
        models.Product.stock_quantity <=
        models.Product.low_stock_threshold
    ).order_by(models.Product.stock_quantity).all()


# -----------------------------------------
# ADJUST PRODUCT STOCK
# -----------------------------------------

@router.post(
    "/businesses/{business_id}/products/{product_id}/stock-adjustments",
    response_model=schemas.StockMovementResponse,
    status_code=201
)
def adjust_stock(
    business_id: int,
    product_id: int,
    adjustment: schemas.StockAdjustmentCreate,
    current_user: models.User = Depends(get_current_user),
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.business_id == business_id,
        models.Product.is_active == True
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    stock_before = product.stock_quantity

    if adjustment.movement_type == "remove":
        if adjustment.quantity > stock_before:
            raise HTTPException(
                status_code=400,
                detail="Insufficient stock available."
            )

        stock_after = stock_before - adjustment.quantity

    else:
        stock_after = stock_before + adjustment.quantity

    movement = models.StockMovement(
        business_id=business_id,
        product_id=product_id,
        user_id=current_user.id,
        movement_type=adjustment.movement_type,
        quantity=adjustment.quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        reason=adjustment.reason.strip()
    )

    product.stock_quantity = stock_after

    db.add(movement)
    db.commit()
    db.refresh(movement)

    return movement
# -----------------------------------------
# VIEW STOCK MOVEMENT HISTORY
# -----------------------------------------

@router.get(
    "/businesses/{business_id}/stock-movements",
    response_model=list[schemas.StockMovementResponse]
)
def get_stock_movements(
    business_id: int,
    membership: models.BusinessMembership = Depends(
        require_business_role("owner", "manager")
    ),
    db: Session = Depends(get_db)
):
    return db.query(models.StockMovement).filter(
        models.StockMovement.business_id == business_id
    ).order_by(
        models.StockMovement.created_at.desc()
    ).all()