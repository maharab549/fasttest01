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
    sms, reviews, ws_messages
)
from .ws_redis import bridge
import os
from datetime import datetime

# ----------------------------------------------------------------
#  Database initialization
# ----------------------------------------------------------------
models.Base.metadata.create_all(bind=engine)

# ----------------------------------------------------------------
#  FastAPI app creation
# ----------------------------------------------------------------
app = FastAPI(
    title="Marketplace API",
    description="A comprehensive marketplace API with authentication, product, cart, and order systems",
    version="1.1.1",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ----------------------------------------------------------------
#  Security & middleware
# ----------------------------------------------------------------

# Enforce HTTPS redirect (only in production)
if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)

# Allow only your trusted domains
# ✅ FIXED CORS CONFIG (Render + Netlify compatible)
from fastapi.middleware.cors import CORSMiddleware
#from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Trust Render/Netlify proxy headers
#app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Force HTTPS only in production
if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)

# ✅ Allow both production and preview Netlify URLs
origins = [
    "https://megamartcom.netlify.app",
    "https://agent-68e40a8b6477a43674ce2f57--megamartcom.netlify.app",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Restrict allowed hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.vercel.app", "*.onrender.com", "megamartcom.netlify.app"]
)

# ----------------------------------------------------------------
#  Static files setup
# ----------------------------------------------------------------
uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ----------------------------------------------------------------
#  Routers
# ----------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(seller.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(user_stats.router, prefix="/api/v1")
app.include_router(favorites.router, prefix="/api/v1")
app.include_router(sms.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(ws_messages.router)

# ----------------------------------------------------------------
#  Redis Bridge
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
#  Core endpoints
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
    """Simple endpoint to test Netlify ↔ FastAPI connectivity"""
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
#  Exception handlers
# ----------------------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# ----------------------------------------------------------------
#  Entry point
# ----------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
