from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, auth, models
from typing import cast
from ..database import get_db

router = APIRouter(prefix="/cart", tags=["cart"])


# Support both trailing and non-trailing clash to avoid browser CORS issues on redirects
@router.get("/", response_model=List[schemas.CartItem])
@router.get("", response_model=List[schemas.CartItem])
def get_cart(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get current user's cart items"""
    cart_items = crud.get_cart_items(db=db, user_id=current_user.id)
    return cart_items


@router.post("/items", response_model=schemas.CartItem)
def add_to_cart(
    cart_item: schemas.CartItemCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Add item to cart"""
    # Check if product exists
    product = crud.get_product(db=db, product_id=cart_item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product is active
    product_typed = cast(models.Product, product)
    # Help type checker: explicitly cast SQLAlchemy-mapped attributes to Python types
    is_active = cast(bool, product_typed.is_active)
    if is_active is False:
        raise HTTPException(status_code=400, detail="Product is not available")
    
    # If variant_id is provided, validate it
    if cart_item.variant_id:
        variant = db.query(models.ProductVariant).filter(
            models.ProductVariant.id == cart_item.variant_id,
            models.ProductVariant.product_id == cart_item.product_id,
            models.ProductVariant.is_active == True
        ).first()
        
        if not variant:
            raise HTTPException(status_code=404, detail="Product variant not found")
        
        # Check variant inventory - use getattr to safely access
        variant_inventory = getattr(variant, 'inventory_count', 0)
        if variant_inventory is None:
            variant_inventory = 0
        if cart_item.quantity > variant_inventory:
            raise HTTPException(
                status_code=400,
                detail=f"Only {variant_inventory} items available for this variant"
            )
    else:
        # Check product inventory (no variant)
        inventory = cast(int, product_typed.inventory_count)
        if cart_item.quantity > inventory:
            raise HTTPException(
                status_code=400,
                detail=f"Only {inventory} items available in stock"
            )
    
    return crud.add_to_cart(
        db=db,
        user_id=current_user.id,
        product_id=cart_item.product_id,
        quantity=cart_item.quantity,
        variant_id=cart_item.variant_id
    )


@router.put("/items/{product_id}", response_model=schemas.CartItem)
def update_cart_item(
    product_id: int,
    quantity: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Update cart item quantity"""
    # Check if product exists
    product = crud.get_product(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check inventory if increasing quantity
    product_typed = cast(models.Product, product)
    inventory = cast(int, product_typed.inventory_count)
    if quantity > 0 and quantity > inventory:
        raise HTTPException(
            status_code=400,
            detail=f"Only {inventory} items available in stock"
        )
    
    cart_item = crud.update_cart_item(
        db=db,
        user_id=current_user.id,
        product_id=product_id,
        quantity=quantity
    )
    
    if cart_item is None and quantity > 0:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    return cart_item


@router.delete("/items/{product_id}", response_model=schemas.MessageResponse)
def remove_from_cart(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Remove item from cart"""
    success = crud.remove_from_cart(
        db=db,
        user_id=current_user.id,
        product_id=product_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    return {"message": "Item removed from cart", "success": True}


@router.delete("/", response_model=schemas.MessageResponse)
@router.delete("", response_model=schemas.MessageResponse)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Clear all items from cart"""
    crud.clear_cart(db=db, user_id=current_user.id)
    return {"message": "Cart cleared", "success": True}


@router.get("/count")
def get_cart_count(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get total number of items in cart"""
    cart_items = crud.get_cart_items(db=db, user_id=current_user.id)
    total_items = sum(item.quantity for item in cart_items)
    return {"count": total_items}


@router.get("/total")
def get_cart_total(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get cart total amount"""
    cart_items = crud.get_cart_items(db=db, user_id=current_user.id)
    total_amount = sum(item.quantity * item.product.price for item in cart_items if item.product)
    total_items = sum(item.quantity for item in cart_items)
    
    return {
        "total_amount": total_amount,
        "total_items": total_items,
        "currency": "USD"
    }

