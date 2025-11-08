"""
Database Index Optimization Script
Adds performance-critical indexes to improve query speed
"""
from sqlalchemy import create_engine, text
from app.config import settings
import sys

def add_indexes():
    """Add critical indexes for performance optimization"""
    
    # Get database URL
    fallback_url = settings.database_url or "sqlite:///./marketplace.db"
    supabase_url_val = getattr(settings, "supabase_database_url", None)
    supabase_url = supabase_url_val if isinstance(supabase_url_val, str) else None
    use_supabase = bool(getattr(settings, "use_supabase", False) and isinstance(supabase_url, str) and len(supabase_url) > 0)
    selected_url = supabase_url if use_supabase and supabase_url is not None else fallback_url
    
    engine = create_engine(selected_url)
    
    print("Adding database indexes for performance optimization...")
    
    indexes = [
        # Products - most queried table
        ("idx_products_approval_status", "CREATE INDEX IF NOT EXISTS idx_products_approval_status ON products(approval_status)"),
        ("idx_products_is_active", "CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active)"),
        ("idx_products_is_featured", "CREATE INDEX IF NOT EXISTS idx_products_is_featured ON products(is_featured)"),
        ("idx_products_created_at", "CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at DESC)"),
        ("idx_products_rating", "CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating DESC)"),
        ("idx_products_price", "CREATE INDEX IF NOT EXISTS idx_products_price ON products(price)"),
        ("idx_products_view_count", "CREATE INDEX IF NOT EXISTS idx_products_view_count ON products(view_count DESC)"),
        ("idx_products_seller_id", "CREATE INDEX IF NOT EXISTS idx_products_seller_id ON products(seller_id)"),
        ("idx_products_category_id", "CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id)"),
        
        # Orders - critical for order processing
        ("idx_orders_user_id", "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)"),
        ("idx_orders_status", "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)"),
        ("idx_orders_payment_status", "CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status)"),
        ("idx_orders_created_at", "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC)"),
        
        # Order Items - for order details lookup
        ("idx_order_items_order_id", "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)"),
        ("idx_order_items_product_id", "CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id)"),
        
        # Reviews - for product rating calculations
        ("idx_reviews_product_id", "CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id)"),
        ("idx_reviews_user_id", "CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id)"),
        ("idx_reviews_is_approved", "CREATE INDEX IF NOT EXISTS idx_reviews_is_approved ON reviews(is_approved)"),
        ("idx_reviews_created_at", "CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at DESC)"),
        
        # Cart Items - for cart operations
        ("idx_cart_items_user_id", "CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON cart_items(user_id)"),
        ("idx_cart_items_product_id", "CREATE INDEX IF NOT EXISTS idx_cart_items_product_id ON cart_items(product_id)"),
        
        # Returns - for return processing
        ("idx_returns_user_id", "CREATE INDEX IF NOT EXISTS idx_returns_user_id ON returns(user_id)"),
        ("idx_returns_order_id", "CREATE INDEX IF NOT EXISTS idx_returns_order_id ON returns(order_id)"),
        ("idx_returns_status", "CREATE INDEX IF NOT EXISTS idx_returns_status ON returns(status)"),
        ("idx_returns_created_at", "CREATE INDEX IF NOT EXISTS idx_returns_created_at ON returns(created_at DESC)"),
        
        # Notifications - for user notifications
        ("idx_notifications_user_id", "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)"),
        ("idx_notifications_is_read", "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)"),
        ("idx_notifications_created_at", "CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC)"),
        
        # Sellers - for seller queries
        ("idx_sellers_user_id", "CREATE INDEX IF NOT EXISTS idx_sellers_user_id ON sellers(user_id)"),
        ("idx_sellers_is_verified", "CREATE INDEX IF NOT EXISTS idx_sellers_is_verified ON sellers(is_verified)"),
        ("idx_sellers_rating", "CREATE INDEX IF NOT EXISTS idx_sellers_rating ON sellers(rating DESC)"),
        
        # Categories - for category filtering
        ("idx_categories_parent_id", "CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id)"),
        ("idx_categories_is_active", "CREATE INDEX IF NOT EXISTS idx_categories_is_active ON categories(is_active)"),
        
        # Composite indexes for common queries
        ("idx_products_active_approved", "CREATE INDEX IF NOT EXISTS idx_products_active_approved ON products(is_active, approval_status)"),
        ("idx_products_category_active", "CREATE INDEX IF NOT EXISTS idx_products_category_active ON products(category_id, is_active, approval_status)"),
        ("idx_orders_user_status", "CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)"),
    ]
    
    success_count = 0
    failed_count = 0
    
    with engine.connect() as conn:
        for idx_name, idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
                print(f"✓ Created index: {idx_name}")
                success_count += 1
            except Exception as e:
                print(f"✗ Failed to create index {idx_name}: {str(e)}")
                failed_count += 1
    
    print(f"\n{'='*60}")
    print(f"Index creation complete!")
    print(f"Successfully created: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"{'='*60}")
    
    return success_count, failed_count

if __name__ == "__main__":
    try:
        success, failed = add_indexes()
        sys.exit(0 if failed == 0 else 1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
