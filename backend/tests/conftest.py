"""
Pytest Configuration and Fixtures
Provides test database and client setup
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import User, Seller, Category, Product
from app.auth import get_password_hash
import os

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_marketplace.db"

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    # Ensure a clean test database file. If a previous run left the file behind
    # remove it before creating the engine so tests start from a fresh DB.
    db_file = "./test_marketplace.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            # If the file is in use, try to proceed (create_engine will still open),
            # but tests may fail; we keep this best-effort cleanup here.
            pass

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    # Create tables fresh for the test session
    Base.metadata.create_all(bind=engine)
    yield engine
    # Dispose engine connections before dropping and removing file to avoid
    # PermissionError on Windows when the SQLite file is still locked.
    try:
        engine.dispose()
    except Exception:
        pass
    Base.metadata.drop_all(bind=engine)
    # Clean up test database file
    db_file = "./test_marketplace.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            # If removal fails, leave the file; subsequent test runs will attempt
            # best-effort cleanup at startup.
            pass

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session"""
    # Use a connection + transaction per test so we can rollback all changes after
    # the test and keep the database clean between tests.
    connection = test_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Rollback the broader transaction to undo any commits
        try:
            transaction.rollback()
        except Exception:
            pass
        connection.close()

@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_seller=False,
        is_admin=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_admin(test_db):
    """Create a test admin user"""
    admin = User(
        email="admin@example.com",
        username="adminuser",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_seller=False,
        is_admin=True
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin

@pytest.fixture
def test_seller_user(test_db):
    """Create a test seller user"""
    user = User(
        email="seller@example.com",
        username="selleruser",
        full_name="Seller User",
        hashed_password=get_password_hash("sellerpassword123"),
        is_active=True,
        is_seller=True,
        is_admin=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create seller profile
    seller = Seller(
        user_id=user.id,
        store_name="Test Store",
        store_description="A test store",
        store_slug="test-store",
        is_verified=True,
        rating=4.5,
        total_sales=100,
        balance=1000.0
    )
    test_db.add(seller)
    test_db.commit()
    test_db.refresh(seller)
    
    return user

@pytest.fixture
def test_category(test_db):
    """Create a test category"""
    category = Category(
        name="Electronics",
        slug="electronics",
        description="Electronic items",
        is_active=True
    )
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    return category

@pytest.fixture
def test_product(test_db, test_seller_user, test_category):
    """Create a test product"""
    seller = test_db.query(Seller).filter(Seller.user_id == test_seller_user.id).first()
    
    product = Product(
        seller_id=seller.id,
        category_id=test_category.id,
        title="Test Product",
        slug="test-product",
        description="A test product",
        short_description="Test product",
        price=99.99,
        sku="TEST-001",
        inventory_count=10,
        is_active=True,
        is_featured=False,
        approval_status="approved",
        rating=4.0,
        review_count=5,
        view_count=100
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)
    return product

@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers(client, test_admin):
    """Get authentication headers for admin user"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_admin.email,
            "password": "adminpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def seller_headers(client, test_seller_user):
    """Get authentication headers for seller user"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_seller_user.email,
            "password": "sellerpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
