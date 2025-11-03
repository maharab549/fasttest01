from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .config import settings
from .database import engine
from . import models
from .routers import (
    auth, products, cart, orders, categories, seller, admin,
    payments, messages, notifications, user_stats, favorites,
    sms, reviews, ws_messages, chatbot
)
from .ws_redis import bridge
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
    title="Marketplace API",
    description="A comprehensive marketplace API with authentication, product, cart, and order systems",
    version="1.1.1",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ----------------------------------------------------------------
# Security & middleware
# ----------------------------------------------------------------

if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)

# Allow CORS for frontend
origins = [
    "https://megamartcom.netlify.app",
    "https://agent-68e40a8b6477a43674ce2f57--megamartcom.netlify.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://192.168.56.1:5173"  # Added local network IP
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
 )
# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.vercel.app", "*.onrender.com", "megamartcom.netlify.app"]
)

# ----------------------------------------------------------------
# Static files setup
# ----------------------------------------------------------------
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ----------------------------------------------------------------
# Routers
# ----------------------------------------------------------------
routers = [
    auth, products, cart, orders, categories, seller, admin,
    payments, messages, notifications, user_stats, favorites,
    sms, reviews, chatbot
]

for router in routers:
    app.include_router(router.router, prefix="/api/v1")

# Mount websocket routes at root (no versioned prefix)
app.include_router(ws_messages.router)

# ----------------------------------------------------------------
# Redis Bridge
# ----------------------------------------------------------------
@app.on_event("startup")
async def startup_events():
    try:
        await bridge.init()
    except Exception:
        pass

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
        "message": "Welcome to Marketplace API (Render Version)",
        "version": "1.1.1",
        "docs": "/api/docs",
        "redoc": "/api/redoc"
    }

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "message": "Marketplace API is running securely"}

@app.get("/api/v1/test_frontend")
async def test_frontend(request: Request):
    client_host = request.client.host
    scheme = request.url.scheme
    return {
        "status": "success",
        "message": "Frontend ↔ Backend connection OK",
        "client_ip": client_host,
        "protocol": scheme,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# ----------------------------------------------------------------
# Exception handlers
# ----------------------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# ----------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # Use Render-provided port, fallback for local dev
    port = int(os.environ.get("PORT", 8000))

    #  Ensure origins match what your frontend is using
    origins = [
        "https://megamartcom.netlify.app",
        "https://agent-68e40a8b6477a43674ce2f57--megamartcom.netlify.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://192.168.56.1:5173"
    ]
    # Run the app with uvicorn for local development. Middleware is configured
    # once above (so we avoid adding duplicate middleware here).
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.debug
    )

