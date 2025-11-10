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
from .security_middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware, RateLimitMiddleware
import os
from datetime import datetime
from sqlalchemy import text
import traceback

# ----------------------------------------------------------------
# Database initialization
# ----------------------------------------------------------------
try:
    models.Base.metadata.create_all(bind=engine)
except Exception as e:
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
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
# app.add_middleware(RateLimitMiddleware, requests_per_minute=300, requests_per_hour=5000)

if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)

# ----------------------------------------------------------------
# CORS configuration
# ----------------------------------------------------------------
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://megamartcom.netlify.app")
if settings.debug:
    allow_origins = ["*"]
else:
    allow_origins = [FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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
    app.include_router(router.router, prefix="/api/v1")

# WebSocket router
app.include_router(ws_messages.router)

# ----------------------------------------------------------------
# Redis Bridge
# ----------------------------------------------------------------
@app.on_event("startup")
async def startup_events():
    try:
        print("Running DB migrations...")
        db_migrations.run_all(engine)
        print("[OK] DB migrations completed")
    except Exception as e:
        print(f"[WARNING] DB migrations error (non-fatal): {e}")

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

# ----------------------------------------------------------------
# Exception handlers with CORS headers
# ----------------------------------------------------------------
def cors_headers(request: Request):
    origin = request.headers.get("origin", FRONTEND_URL)
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
    }

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"},
        headers=cors_headers(request)
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=cors_headers(request)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"UNHANDLED EXCEPTION on {request.method} {request.url.path}:")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc), "type": type(exc).__name__},
        headers=cors_headers(request)
    )

# ----------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.debug
    )
