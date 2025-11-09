#!/usr/bin/env python
"""Check if seller router is registered multiple times"""

from app.main import app
from app.routers import seller

print("=== CHECKING SELLER ROUTER REGISTRATION ===\n")

seller_routes = []
for route in app.routes:
    path = getattr(route, 'path', None)
    if path and "/seller/" in path:
        endpoint = getattr(route, 'endpoint', None)
        endpoint_name = getattr(endpoint, '__name__', str(endpoint))
        seller_routes.append({
            'path': path,
            'methods': getattr(route, 'methods', None),
            'endpoint_name': endpoint_name,
            'endpoint_id': id(endpoint)
        })

# Group by endpoint name
from collections import defaultdict
by_endpoint = defaultdict(list)
for route in seller_routes:
    by_endpoint[route['endpoint_name']].append(route)

print("Routes with duplicate endpoints:")
for endpoint_name, routes in by_endpoint.items():
    if len(routes) > 1:
        print(f"\n{endpoint_name}: {len(routes)} times")
        for route in routes:
            print(f"  {route['path']} -> {route['methods']}")

# Check for duplicate routes
print("\n\nAll seller routes:")
seen_combos = {}
for route in seller_routes:
    combo = (route['path'], tuple(sorted(route['methods'])))
    if combo in seen_combos:
        print(f"\n⚠️ DUPLICATE: {combo}")
        print(f"  First: {seen_combos[combo]}")
        print(f"  Current: {route}")
    else:
        seen_combos[combo] = route
        print(f"{route['path']} -> {route['methods']}")
