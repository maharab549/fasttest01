#!/usr/bin/env python
"""Inspect the actual FastAPI app routes to see what's really registered"""

from app.main import app

print("=== CHECKING FastAPI APP ROUTES ===\n")

# Find all payout-info routes
payout_routes = []
for route in app.routes:
    path = getattr(route, 'path', None)
    if path and "payout-info" in path:
        payout_routes.append(route)
        methods = getattr(route, 'methods', None)
        endpoint = getattr(route, 'endpoint', None)
        print(f"Path: {path}")
        print(f"Methods: {methods}")
        print(f"Endpoint: {endpoint}")
        print(f"Route class: {type(route).__name__}")
        print()

if not payout_routes:
    print("✗ NO PAYOUT-INFO ROUTES FOUND IN APP!")
    print("\nSearching for seller routes...")
    for route in app.routes:
        path = getattr(route, 'path', None)
        if path and "/seller/" in path:
            methods = getattr(route, 'methods', None)
            print(f"{path} -> {methods}")
else:
    print(f"✓ Found {len(payout_routes)} route(s)")

# Check if there are any duplicate routes with the same path
print("\n\n=== CHECKING FOR DUPLICATE ROUTES ===")
paths_seen = {}
for route in app.routes:
    path = getattr(route, 'path', None)
    if path:
        if path not in paths_seen:
            paths_seen[path] = []
        methods = getattr(route, 'methods', None)
        paths_seen[path].append(methods)

for path, methods_list in sorted(paths_seen.items()):
    if len(methods_list) > 1 and "/seller/" in path:
        print(f"\n⚠️ DUPLICATE: {path}")
        for i, methods in enumerate(methods_list):
            print(f"   #{i+1}: {methods}")
