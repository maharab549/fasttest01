"""
Test Product Endpoints
"""
import pytest
from fastapi import status

def test_get_products(client, test_product):
    """Test getting products list"""
    response = client.get("/api/products")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) > 0

def test_get_product_by_id(client, test_product):
    """Test getting a specific product"""
    response = client.get(f"/api/products/{test_product.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_product.id
    assert data["title"] == test_product.title

def test_get_product_by_slug(client, test_product):
    """Test getting product by slug"""
    response = client.get(f"/api/products/slug/{test_product.slug}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["slug"] == test_product.slug

def test_create_product_as_seller(client, seller_headers, test_category):
    """Test creating a product as seller"""
    response = client.post(
        "/api/products",
        json={
            "category_id": test_category.id,
            "title": "New Test Product",
            "slug": "new-test-product",
            "description": "A new test product",
            "short_description": "New product",
            "price": 149.99,
            "sku": "NEW-TEST-001",
            "inventory_count": 20
        },
        headers=seller_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "New Test Product"
    assert data["price"] == 149.99

def test_create_product_as_non_seller(client, auth_headers, test_category):
    """Test creating product as non-seller (should fail)"""
    response = client.post(
        "/api/products",
        json={
            "category_id": test_category.id,
            "title": "Product",
            "slug": "product",
            "description": "Product",
            "price": 99.99,
            "sku": "SKU-001"
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_filter_products_by_category(client, test_product):
    """Test filtering products by category"""
    response = client.get(f"/api/products?category_id={test_product.category_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(p["category_id"] == test_product.category_id for p in data)

def test_search_products(client, test_product):
    """Test product search"""
    response = client.get(f"/api/products?search={test_product.title[:4]}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) > 0
