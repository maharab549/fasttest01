from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .config import settings
from .database import engine
from . import models
from .routers import auth, products, cart, orders, categories, seller, admin, payments, messages, notifications, user_stats, favorites, sms, reviews, ws_messages
from .ws_redis import bridge
import os

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Marketplace API",
    description="A comprehensive marketplace API with user authentication, product management, cart, and order processing",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware: allow only your Netlify frontend and local dev
origins = [
    "https://megamartcom.netlify.app",  # Netlify production frontend
    "http://localhost:5173",             # Local development frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

# Mount static files
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Include routers
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
# Include websocket router (no /api prefix)
app.include_router(ws_messages.router)


@app.on_event("startup")
async def startup_events():
    # Initialize Redis bridge subscriber (if redis configured)
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


@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Welcome to Marketplace API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "redoc": "/api/redoc"
    }


@app.get("/api/v1/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Marketplace API is running"
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
