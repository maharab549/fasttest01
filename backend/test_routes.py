#!/usr/bin/env python
"""Test script to check if payout-info routes are registered"""

from app.main import app

print("\n=== CHECKING FOR PAYOUT-INFO ROUTES ===\n")

payout_routes = []
for route in app.routes:
    path = getattr(route, 'path', None)
    if path and "payout-info" in path:
        payout_routes.append(route)
        print(f"✓ Found: {path}")
        print(f"  Methods: {getattr(route, 'methods', 'unknown')}")
        print(f"  Endpoint: {getattr(route, 'endpoint', None)}")
        print()

if not payout_routes:
    print("✗ NO PAYOUT-INFO ROUTES FOUND!")
    print("\n=== ALL ROUTES ===")
    for route in app.routes:
        path = getattr(route, 'path', None)
        methods = getattr(route, 'methods', None)
        endpoint = getattr(route, 'endpoint', 'unknown')
        print(f"{path} {methods} -> {endpoint}")
else:
    print(f"\n✓ Found {len(payout_routes)} payout-info route(s)")
