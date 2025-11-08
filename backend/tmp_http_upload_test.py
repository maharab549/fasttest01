import requests
import io
import time
from app.database import SessionLocal
from app import models
from app import auth
from sqlalchemy.orm import Session

# Wait briefly for server to come up
print('Sleeping 1s to let server start...')
time.sleep(1)

DB = SessionLocal()

# Ensure a test seller user exists (username: test_seller)
username = 'test_seller'
password = 'password123'

def ensure_seller(db: Session):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        user = models.User(
            username=username,
            email='test_seller@example.com',
            full_name='Test Seller',
            hashed_password=auth.get_password_hash(password),
            is_seller=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print('Created user', user.id)
    else:
        # ensure seller flag
        if not user.is_seller:
            user.is_seller = True
            db.commit()
            db.refresh(user)
            print('Updated user to seller')
    # ensure seller profile exists
    seller = db.query(models.Seller).filter(models.Seller.user_id == user.id).first()
    if not seller:
        seller = models.Seller(user_id=user.id, store_name='Test Store', store_description='x', store_slug=f'test-store-{user.id}')
        db.add(seller)
        db.commit()
        db.refresh(seller)
        print('Created seller profile', seller.id)
    return user

user = ensure_seller(DB)
DB.close()

# Create token
token = auth.create_access_token({"sub": username})
print('Token created (first 40 chars):', token[:40])

# Prepare a small fake image bytes
fake_image = io.BytesIO(b"\xff\xd8\xff\xdb" + b"0"*1024 + b"\xff\xd9")
files = {"file": ("test_upload.jpg", fake_image, "image/jpeg")}

url = "http://127.0.0.1:8000/products/upload-image"
params = {"product_id": 3}
headers = {"Authorization": f"Bearer {token}"}

print('POSTing to', url, 'params', params)
resp = requests.post(url, files=files, params=params, headers=headers)
print('Response status:', resp.status_code)
try:
    print('Response JSON:', resp.json())
except Exception:
    print('Response text:', resp.text[:1000])

# Check DB for ProductImage and product.images
DB2 = SessionLocal()
from app import crud
images = DB2.query(models.ProductImage).order_by(models.ProductImage.id.desc()).limit(5).all()
print('Latest ProductImage rows:')
for im in images:
    print(im.id, im.product_id, im.image_url)

p = DB2.query(models.Product).filter(models.Product.id == 3).first()
print('Product 3 images field:', p.images, type(p.images))
DB2.close()
