from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/products/")
def get_products():
    return {
        "data": {
            "items": [
                {
                    "id": 1,
                    "title": "Wireless Bluetooth Headphones",
                    "price": 79.99,
                    "images": ["https://via.placeholder.com/300x300?text=Headphones"],
                    "rating": 4.5,
                    "review_count": 123,
                    "slug": "wireless-bluetooth-headphones"
                },
                {
                    "id": 2,
                    "title": "Smart Fitness Watch",
                    "price": 199.99,
                    "images": ["https://via.placeholder.com/300x300?text=Watch"],
                    "rating": 4.8,
                    "review_count": 89,
                    "slug": "smart-fitness-watch"
                }
            ],
            "total": 8,
            "page": 1,
            "per_page": 20,
            "pages": 1
        }
    }

@app.get("/api/v1/health")
def health():
    return {"status": "healthy", "message": "Test API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
