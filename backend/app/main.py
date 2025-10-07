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

# ------------------- Database -------------------
models.Base.metadata.create_all(bind=engine)

# ------------------- App -------------------
app = FastAPI(
    title="Marketplace API",
    description="Marketplace API with authentication, products, cart, and orders",
    version="1.1.1",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ------------------- Middleware -------------------

# HTTPS redirect (production only)
if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS for Netlify + localhost
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

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.vercel.app", "*.onrender.com", "megamartcom.netlify.app"]
)

# ------------------- Static files -------------------
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ------------------- Routers -------------------
routers = [
    auth, products, cart, orders, categories, seller, admin,
    payments, messages, notifications, user_stats, favorites,
    sms, reviews, ws_messages
]
for r in routers:
    app.include_router(r.router, prefix="/api/v1")

# ------------------- Redis Bridge -------------------
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

# ------------------- Core endpoints -------------------
@app.get("/")
def read_root():
    return {"message": "Welcome to Marketplace API", "version": "1.1.1"}

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "message": "API running securely"}

@app.get("/api/v1/test_frontend")
async def test_frontend(request: Request):
    return {
        "status": "success",
        "message": "Frontend ↔ Backend connection OK",
        "client_ip": request.client.host,
        "protocol": request.url.scheme,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# ------------------- Exception handlers -------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# ------------------- Entry point -------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
