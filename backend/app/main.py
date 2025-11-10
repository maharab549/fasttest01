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
from .routers import (
    auth, products, cart, orders, categories, seller, admin,
    payments, messages, notifications, user_stats, favorites,
    sms, reviews, ws_messages, chatbot, returns, loyalty, health, variants, product_variants
)
from .ws_redis import bridge
from .security_middleware import (
    RateLimitMiddleware, 
    RequestLoggingMiddleware, 
    SecurityHeadersMiddleware
)
import os
from datetime import datetime
from sqlalchemy import text

# ----------------------------------------------------------------
# Database initialization
# ----------------------------------------------------------------
try:
    # Creating tables at import time can cause the app to crash on startup
    # if the configured database is unreachable (e.g., Supabase network issues).
    # Wrap in a try/except so the process can start and surface logs for
    # debugging instead of failing silently with an import-time traceback.
    models.Base.metadata.create_all(bind=engine)
except Exception as e:
    import traceback
    print("[WARNING] Could not initialize database schema at import time:")
    print(traceback.format_exc())
    print("[WARNING] Continuing startup; the database may be unavailable.\n")

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

if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)

# ----------------------------------------------------------------
# CORS configuration (important for Netlify frontend)
# ----------------------------------------------------------------
# Default hard-coded frontend origins (used as fallback when no env-provided list)
frontend_origins = [
    "https://megamartcom.netlify.app",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://192.168.56.1:5173"
]

# Determine effective allowlist: prefer settings.cors_origins (from env/.env),
# fall back to the built-in `frontend_origins` when not set. In debug mode allow all.
if settings.debug:
    effective_origins = ["*"]
else:
    # settings.cors_origins is a List[str], possibly empty
    effective_origins = settings.cors_origins if settings.cors_origins else frontend_origins
# Log the effective CORS origins for easier debugging in deployment logs
print(f"[CORS] Effective allow-origins: {effective_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=effective_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------
# Static files setup
# ----------------------------------------------------------------
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ----------------------------------------------------------------
# Include routers
# ----------------------------------------------------------------
routers = [
    auth, products, cart, orders, categories, seller, admin,
    payments, messages, notifications, user_stats, favorites,
    sms, reviews, chatbot, returns, loyalty, health, variants, product_variants
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

@app.get("/api/v1/debug/image-test/{product_id}")
def debug_image_test(product_id: int):
    """Test endpoint to verify image file exists and is accessible"""
    import os
    from pathlib import Path
    
    image_path = f"uploads/products/product_{product_id}.png"
    full_path = Path(image_path)
    
    return {
        "product_id": product_id,
        "image_path": image_path,
        "file_exists": full_path.exists(),
        "file_size": full_path.stat().st_size if full_path.exists() else None,
        "absolute_path": str(full_path.absolute()),
        "image_url": f"/uploads/products/product_{product_id}.png"
    }


# Debug endpoint to check database connectivity. Only enabled when debug mode is on.
@app.get("/api/v1/debug/db_status")
def debug_db_status():
    """Return a quick DB connectivity check. Only available when settings.debug == True."""
    from fastapi import HTTPException
    import traceback

    if not settings.debug:
        raise HTTPException(status_code=403, detail="Debug endpoint disabled")

    try:
        with engine.connect() as conn:
            # Run a minimal query to validate connectivity
            result = conn.execute(text("SELECT 1"))
            scalar = result.scalar()
        return {"db": "ok", "result": scalar}
    except Exception as e:
        tb = traceback.format_exc()
        # Include CORS headers so frontend can read this error during debugging
        headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true"}
        return JSONResponse(status_code=500, content={"db": "error", "error": str(e), "trace": tb}, headers=headers)

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
    # Ensure CORS headers are present even for internal errors so the frontend
    # receives the JSON body instead of the browser blocking it.
    origin = request.headers.get("origin")
    allow_origin = origin if origin else "*"
    headers = {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Credentials": "true",
    }
    return JSONResponse(
        status_code=500, 
        content={"detail": "Internal server error", "error": str(exc), "type": type(exc).__name__},
        headers=headers
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    import traceback
    print("=" * 80)
    print("500 INTERNAL SERVER ERROR:")
    print(traceback.format_exc())
    print("=" * 80)
    origin = request.headers.get("origin")
    allow_origin = origin if origin else "*"
    headers = {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Credentials": "true",
    }
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "error": str(exc)}, headers=headers)

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
