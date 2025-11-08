from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app import models, auth
import io

client = TestClient(app)
DB = SessionLocal()

username = 'tc_seller'
password = 'password123'

# ensure user and seller
user = DB.query(models.User).filter(models.User.username==username).first()
if not user:
    user = models.User(username=username, email='tc_seller@example.com', full_name='TC Seller', hashed_password=auth.get_password_hash(password), is_seller=True, is_active=True)
    DB.add(user)
    DB.commit()
    DB.refresh(user)
    print('Created user', user.id)
else:
    if not user.is_seller:
        user.is_seller = True
        DB.commit()
        DB.refresh(user)
DB_seller = DB.query(models.Seller).filter(models.Seller.user_id==user.id).first()
if not DB_seller:
    seller = models.Seller(user_id=user.id, store_name='TC Store', store_description='x', store_slug=f'tc-store-{user.id}')
    DB.add(seller)
    DB.commit()
    DB.refresh(seller)
    print('Created seller profile', seller.id)

# create token
token = auth.create_access_token({"sub": username})
headers = {"Authorization": f"Bearer {token}"}

# fake image
fake_image = io.BytesIO(b"\xff\xd8\xff\xdb" + b"0"*1024 + b"\xff\xd9")
files = {"file": ("tc_test.jpg", fake_image, "image/jpeg")}
params = {"product_id": 3}

print('Posting with TestClient...')
resp = client.post('/api/v1/products/upload-image', files=files, params=params, headers=headers)
print('status_code:', resp.status_code)
try:
    print('json:', resp.json())
except Exception:
    print('text:', resp.text)

# inspect DB
images = DB.query(models.ProductImage).order_by(models.ProductImage.id.desc()).limit(5).all()
print('Latest ProductImage rows:')
for im in images:
    print(im.id, im.product_id, im.image_url)

p = DB.query(models.Product).filter(models.Product.id==3).first()
print('Product 3 images:', p.images)
DB.close()
