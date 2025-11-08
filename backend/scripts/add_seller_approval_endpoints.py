"""
Script to add seller approval endpoints to admin.py

This adds two endpoints:
1. GET /admin/sellers/pending - List pending sellers (is_verified=False)
2. PUT /admin/sellers/{seller_id}/approve - Approve a seller
"""

endpoint_code = '''
@router.get("/sellers/pending", response_model=Dict[str, Any])
def get_pending_sellers(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending sellers (not yet verified)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    skip = (page - 1) * per_page
    query = db.query(crud.models.Seller).filter(crud.models.Seller.is_verified == False)
    total = query.count()
    sellers = query.order_by(crud.models.Seller.created_at.desc()).offset(skip).limit(per_page).all()
    
    data = [
        {
            "id": s.id,
            "store_name": s.store_name,
            "store_description": s.store_description,
            "store_slug": s.store_slug,
            "user_id": s.user_id,
            "user_email": s.user.email if s.user else None,
            "user_name": s.user.full_name if s.user else None,
            "is_verified": s.is_verified,
            "rating": s.rating,
            "total_sales": s.total_sales,
            "balance": float(s.balance),
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in sellers
    ]
    return {"items": data, "total": total, "page": page, "per_page": per_page}


@router.put("/sellers/{seller_id}/approve")
def approve_seller(
    seller_id: int,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Approve a seller (set is_verified=True)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    seller = db.query(crud.models.Seller).filter(crud.models.Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    seller.is_verified = True
    db.commit()
    db.refresh(seller)
    
    return {
        "message": "Seller approved successfully",
        "seller_id": seller.id,
        "store_name": seller.store_name,
        "is_verified": seller.is_verified
    }
'''

print("Add the following code to app/routers/admin.py at the end (before the last line):")
print(endpoint_code)
print("\nDone! Now update the frontend to add API calls and UI.")
