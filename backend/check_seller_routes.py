#!/usr/bin/env python
"""Check if the seller router has the payout-info routes registered"""

from app.routers import seller

print("=== CHECKING SELLER ROUTER ===\n")

# Get all routes
routes = seller.router.routes

print("Registered routes in seller router:")
for route in routes:
    path = getattr(route, 'path', None)
    methods = getattr(route, 'methods', None)
    endpoint = getattr(route, 'endpoint', None).__name__ if hasattr(getattr(route, 'endpoint', None), '__name__') else getattr(route, 'endpoint', None)
    
    if path and "payout" in path:
        print(f"\n✓ FOUND: {path}")
        print(f"  Methods: {methods}")
        print(f"  Endpoint: {endpoint}")

# List all routes
print("\n\nALL ROUTES IN SELLER ROUTER:")
for route in routes:
    path = getattr(route, 'path', None)
    methods = getattr(route, 'methods', None)
    if path:
        print(f"{path} -> {methods}")
