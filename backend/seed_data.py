#!/usr/bin/env python3
"""
Seed script to populate the database with sample data
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models, crud, schemas, auth
from app.config import settings

def create_sample_data():
    """Create sample data for the marketplace"""
    db = SessionLocal()
    
    try:
        # Create categories
        categories_data = [
            {"name": "Electronics", "slug": "electronics", "description": "Electronic devices and gadgets"},
            {"name": "Clothing", "slug": "clothing", "description": "Fashion and apparel"},
            {"name": "Books", "slug": "books", "description": "Books and literature"},
            {"name": "Home & Garden", "slug": "home-garden", "description": "Home improvement and gardening"},
            {"name": "Sports", "slug": "sports", "description": "Sports and outdoor equipment"},
            {"name": "Toys", "slug": "toys", "description": "Toys and games"},
        ]
        
        for cat_data in categories_data:
            existing_cat = db.query(models.Category).filter(models.Category.slug == cat_data["slug"]).first()
            if not existing_cat:
                category = models.Category(**cat_data)
                db.add(category)
        
        db.commit()
        
        # Create admin user
        admin_data = schemas.UserCreate(
            email="admin@marketplace.com",
            username="admin",
            full_name="Admin User",
            password="admin123",
            is_seller=False
        )
        
        existing_admin = crud.get_user_by_username(db, "admin")
        if not existing_admin:
            admin_user = crud.create_user(db, admin_data)
            admin_user.is_admin = True
            db.commit()
            print("Created admin user: admin / admin123")
        
        # Create sample sellers
        sellers_data = [
            {
                "user": schemas.UserCreate(
                    email="seller1@marketplace.com",
                    username="techstore",
                    full_name="Tech Store Owner",
                    password="seller123",
                    is_seller=True
                ),
                "store": schemas.SellerCreate(
                    store_name="Tech Paradise",
                    store_slug="tech-paradise",
                    store_description="Your one-stop shop for all tech gadgets"
                )
            },
            {
                "user": schemas.UserCreate(
                    email="seller2@marketplace.com",
                    username="fashionista",
                    full_name="Fashion Store Owner",
                    password="seller123",
                    is_seller=True
                ),
                "store": schemas.SellerCreate(
                    store_name="Fashion Hub",
                    store_slug="fashion-hub",
                    store_description="Latest trends in fashion and style"
                )
            },
            {
                "user": schemas.UserCreate(
                    email="seller3@marketplace.com",
                    username="bookworm",
                    full_name="Book Store Owner",
                    password="seller123",
                    is_seller=True
                ),
                "store": schemas.SellerCreate(
                    store_name="Book Haven",
                    store_slug="book-haven",
                    store_description="Discover your next favorite book"
                )
            }
        ]
        
        for seller_data in sellers_data:
            existing_seller = crud.get_user_by_username(db, seller_data["user"].username)
            if not existing_seller:
                seller_user = crud.create_user(db, seller_data["user"])
                seller_profile = crud.create_seller(db, seller_data["store"], seller_user.id)
                print(f"Created seller: {seller_data['user'].username} / seller123")
        
        # Create sample customers
        customers_data = [
            schemas.UserCreate(
                email="customer1@marketplace.com",
                username="customer1",
                full_name="John Doe",
                password="customer123",
                is_seller=False
            ),
            schemas.UserCreate(
                email="customer2@marketplace.com",
                username="customer2",
                full_name="Jane Smith",
                password="customer123",
                is_seller=False
            )
        ]
        
        for customer_data in customers_data:
            existing_customer = crud.get_user_by_username(db, customer_data.username)
            if not existing_customer:
                customer = crud.create_user(db, customer_data)
                print(f"Created customer: {customer_data.username} / customer123")
        
        # Get categories and sellers for products
        electronics_cat = db.query(models.Category).filter(models.Category.slug == "electronics").first()
        clothing_cat = db.query(models.Category).filter(models.Category.slug == "clothing").first()
        books_cat = db.query(models.Category).filter(models.Category.slug == "books").first()
        
        tech_seller = db.query(models.Seller).filter(models.Seller.store_slug == "tech-paradise").first()
        fashion_seller = db.query(models.Seller).filter(models.Seller.store_slug == "fashion-hub").first()
        book_seller = db.query(models.Seller).filter(models.Seller.store_slug == "book-haven").first()
        
        # Create sample products
        products_data = [
            # Electronics
            {
                "title": "Wireless Bluetooth Headphones",
                "slug": "wireless-bluetooth-headphones",
                "description": "High-quality wireless headphones with noise cancellation and 30-hour battery life.",
                "short_description": "Premium wireless headphones with noise cancellation",
                "price": 199.99,
                "compare_price": 249.99,
                "sku": "WBH-001",
                "inventory_count": 50,
                "category_id": electronics_cat.id if electronics_cat else 1,
                "seller_id": tech_seller.id if tech_seller else 1,
                "is_featured": True,
                "images": ["/uploads/headphones.jpg"]
            },
            {
                "title": "Smartphone 128GB",
                "slug": "smartphone-128gb",
                "description": "Latest smartphone with 128GB storage, dual camera, and fast charging.",
                "short_description": "Latest smartphone with 128GB storage",
                "price": 699.99,
                "compare_price": 799.99,
                "sku": "SP-128-001",
                "inventory_count": 25,
                "category_id": electronics_cat.id if electronics_cat else 1,
                "seller_id": tech_seller.id if tech_seller else 1,
                "is_featured": True,
                "images": ["/uploads/smartphone.jpg"]
            },
            {
                "title": "Laptop 15.6 inch",
                "slug": "laptop-15-6-inch",
                "description": "Powerful laptop with Intel i7 processor, 16GB RAM, and 512GB SSD.",
                "short_description": "High-performance laptop for work and gaming",
                "price": 1299.99,
                "sku": "LP-156-001",
                "inventory_count": 15,
                "category_id": electronics_cat.id if electronics_cat else 1,
                "seller_id": tech_seller.id if tech_seller else 1,
                "images": ["/uploads/laptop.jpg"]
            },
            
            # Clothing
            {
                "title": "Cotton T-Shirt",
                "slug": "cotton-t-shirt",
                "description": "Comfortable 100% cotton t-shirt available in multiple colors and sizes.",
                "short_description": "Comfortable 100% cotton t-shirt",
                "price": 24.99,
                "sku": "CT-001",
                "inventory_count": 100,
                "category_id": clothing_cat.id if clothing_cat else 2,
                "seller_id": fashion_seller.id if fashion_seller else 2,
                "is_featured": True,
                "images": ["/uploads/tshirt.jpg"]
            },
            {
                "title": "Denim Jeans",
                "slug": "denim-jeans",
                "description": "Classic denim jeans with perfect fit and premium quality fabric.",
                "short_description": "Classic denim jeans with perfect fit",
                "price": 79.99,
                "compare_price": 99.99,
                "sku": "DJ-001",
                "inventory_count": 75,
                "category_id": clothing_cat.id if clothing_cat else 2,
                "seller_id": fashion_seller.id if fashion_seller else 2,
                "images": ["/uploads/jeans.jpg"]
            },
            {
                "title": "Winter Jacket",
                "slug": "winter-jacket",
                "description": "Warm and stylish winter jacket perfect for cold weather.",
                "short_description": "Warm and stylish winter jacket",
                "price": 149.99,
                "sku": "WJ-001",
                "inventory_count": 30,
                "category_id": clothing_cat.id if clothing_cat else 2,
                "seller_id": fashion_seller.id if fashion_seller else 2,
                "images": ["/uploads/jacket.jpg"]
            },
            
            # Books
            {
                "title": "The Great Gatsby",
                "slug": "the-great-gatsby",
                "description": "Classic American novel by F. Scott Fitzgerald. A timeless story of love and tragedy.",
                "short_description": "Classic American novel by F. Scott Fitzgerald",
                "price": 12.99,
                "sku": "TGG-001",
                "inventory_count": 200,
                "category_id": books_cat.id if books_cat else 3,
                "seller_id": book_seller.id if book_seller else 3,
                "images": ["/uploads/gatsby.jpg"]
            },
            {
                "title": "Python Programming Guide",
                "slug": "python-programming-guide",
                "description": "Comprehensive guide to Python programming for beginners and advanced users.",
                "short_description": "Comprehensive Python programming guide",
                "price": 39.99,
                "sku": "PPG-001",
                "inventory_count": 80,
                "category_id": books_cat.id if books_cat else 3,
                "seller_id": book_seller.id if book_seller else 3,
                "is_featured": True,
                "images": ["/uploads/python-book.jpg"]
            }
        ]
        
        for product_data in products_data:
            existing_product = db.query(models.Product).filter(models.Product.sku == product_data["sku"]).first()
            if not existing_product:
                product = models.Product(**product_data)
                db.add(product)
        
        db.commit()
        print("Sample products created successfully!")
        
        print("\n=== Sample Login Credentials ===")
        print("Admin: admin / admin123")
        print("Sellers:")
        print("  - techstore / seller123 (Tech Paradise)")
        print("  - fashionista / seller123 (Fashion Hub)")
        print("  - bookworm / seller123 (Book Haven)")
        print("Customers:")
        print("  - customer1 / customer123")
        print("  - customer2 / customer123")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Creating sample data for marketplace...")
    create_sample_data()
    print("Sample data creation completed!")

