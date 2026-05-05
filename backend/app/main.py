from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .config import settings
from .database import engine
from . import models
from . import db_migrations
from .media_paths import resolve_media_file
from .routers import (
    auth, products, cart, orders, categories, seller, admin,
    payments, messages, notifications, user_stats, favorites,
    sms, reviews, ws_messages, chatbot, returns, loyalty, health, variants, product_variants,
    banners
)
from .ws_redis import bridge
from .security_middleware import (
    RateLimitMiddleware, 
    RequestLoggingMiddleware, 
    SecurityHeadersMiddleware
)
import os
from datetime import datetime

# ----------------------------------------------------------------
# Database initialization
# ----------------------------------------------------------------
models.Base.metadata.create_all(bind=engine)

# ----------------------------------------------------------------
# FastAPI app creation
# ----------------------------------------------------------------
app = FastAPI(
    title="MegaMart API",
    description="A comprehensive MegaMart API with authentication, product, cart, and order systems",
    version="1.1.1",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ----------------------------------------------------------------
# Security & middleware
# ----------------------------------------------------------------

# Add security headers middleware (OWASP recommended headers)
app.add_middleware(SecurityHeadersMiddleware)

# Add request logging middleware for security monitoring
app.add_middleware(RequestLoggingMiddleware)

# Add rate limiting middleware - DISABLED for development
# app.add_middleware(RateLimitMiddleware, requests_per_minute=300, requests_per_hour=5000)

api_base = (settings.api_base_url or "").lower()
should_force_https = (not settings.debug) and api_base.startswith("https://")

if should_force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

# ----------------------------------------------------------------
# CORS configuration (important for Netlify frontend)
# ----------------------------------------------------------------
frontend_origins = [
    "https://megamartcom.netlify.app",
    "https://agent-68e40a8b6477a43674ce2f57--megamartcom.netlify.app",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://192.168.56.1:5173"
]

# Configure CORS. Use an explicit allowlist even in development so credentialed
# requests receive a specific Access-Control-Allow-Origin header (browsers
# reject "*" when Access-Control-Allow-Credentials is true).
# Merge any configured origins (env) with the hardcoded frontend list and a
# safe default. Use dict.fromkeys to preserve order and de-duplicate.
env_origins = settings.cors_origins or []
merged = env_origins + frontend_origins + ["http://localhost:5173"]
cors_allowlist = list(dict.fromkeys(merged))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowlist,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "10.0.2.2",
        "0.0.0.0",
        "192.168.56.1",
        # TestClient uses host 'testserver' during pytest runs
        "testserver",
        "*.vercel.app",
        "*.onrender.com",
        "megamartcom.netlify.app"
    ]
)

# ----------------------------------------------------------------
# Static files setup
# ----------------------------------------------------------------
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)

# Serve uploaded files with explicit headers so browsers don't cache during development.
@app.get("/uploads/{file_path:path}")
def serve_uploads(file_path: str):
    full_path = resolve_media_file(f"/uploads/{file_path}")
    if not full_path:
        raise HTTPException(status_code=404, detail="File not found")
    # Use FileResponse to serve the file and set Cache-Control header for dev
    from fastapi.responses import FileResponse
    return FileResponse(str(full_path), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})

# ----------------------------------------------------------------
# Include routers
# ----------------------------------------------------------------
routers = [
    auth, products, cart, orders, categories, seller, admin,
    payments, messages, notifications, user_stats, favorites,
    sms, reviews, chatbot, returns, loyalty, health, variants, product_variants,
    banners
]

for router in routers:
    # Only include routers under /api/v1 to avoid duplicate route registration and route conflicts
    app.include_router(router.router, prefix="/api/v1")

# WebSocket router
app.include_router(ws_messages.router)

# Debug: Print all registered routes at startup
def print_routes(app):
    print("\n=== FastAPI Registered Routes ===")
    for route in app.routes:
        print(f"{route.path} -> {getattr(route, 'endpoint', None)}")
    print("=== END ROUTES ===\n")

print_routes(app)

# ----------------------------------------------------------------
# Redis Bridge
# ----------------------------------------------------------------
@app.on_event("startup")
async def startup_events():
    # Lightweight, idempotent DB migrations for local SQLite/dev
    try:
        print("Running DB migrations...")
        db_migrations.run_all(engine)
        print("[OK] DB migrations completed")
    except Exception as e:
        print(f"[WARNING] DB migrations error (non-fatal): {e}")
    # Initialize Redis bridge (best-effort)
    #try:
    #    print("Initializing Redis bridge...")
    #    await bridge.init()
    #    print("[OK] Redis bridge initialized")
    #except Exception as e:
    #    print(f"[WARNING] Redis bridge error (non-fatal): {e}")

@app.on_event("shutdown")
async def shutdown_events():
    try:
        await bridge.close()
    except Exception:
        pass

# ----------------------------------------------------------------
# Core endpoints
# ----------------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "message": "Welcome to MegaMart API (Render Version)",
        "version": "1.1.1",
        "docs": "/api/docs",
        "redoc": "/api/redoc"
    }

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "message": "MegaMart API is running securely"}


# Backwards-compatible aliases for older clients/scripts that use /api/*
@app.get("/api/health")
def health_check_alias():
    return health_check()

@app.get("/api/v1/test_frontend")
async def test_frontend(request: Request):
    client_host = request.client.host if request.client else "unknown"
    scheme = request.url.scheme
    return {
        "status": "success",
        "message": "Frontend ↔ Backend connection OK",
        "client_ip": client_host,
        "protocol": scheme,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/api/test_frontend")
async def test_frontend_alias(request: Request):
    return await test_frontend(request)

# ----------------------------------------------------------------
# Exception handlers
# ----------------------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Preserve original HTTPException status codes (e.g., 401/403) instead of converting to 500."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import traceback
    print("=" * 80)
    print(f"UNHANDLED EXCEPTION on {request.method} {request.url.path}:")
    print(traceback.format_exc())
    print("=" * 80)
    return JSONResponse(
        status_code=500, 
        content={"detail": "Internal server error", "error": str(exc), "type": type(exc).__name__}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    import traceback
    print("=" * 80)
    print("500 INTERNAL SERVER ERROR:")
    print(traceback.format_exc())
    print("=" * 80)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "error": str(exc)})

# ----------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # Render provides a dynamic port, fallback to 8000 locally
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.debug
    )
