from app.database import SessionLocal
from app import crud, models


def main():
    db = SessionLocal()
    product_id = 3
    try:
        # Create a ProductImage record pointing to a sample uploads path
        db_image = crud.create_product_image(db=db, product_id=product_id, image_url="/uploads/products/test_upload.jpg", alt_text="test upload", is_primary=False, sort_order=0)
        print(f"Created ProductImage: id={db_image.id}, product_id={db_image.product_id}, image_url={db_image.image_url}")

        # Append the new image ID to the product.images list
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if not product:
            print(f"Product {product_id} not found")
            return

        existing_images = product.images if isinstance(product.images, list) else []
        cleaned_images = []
        for image in existing_images:
            try:
                cleaned_images.append(int(image))
            except Exception:
                # ignore non-numeric entries (e.g. data URIs)
                continue

        updated_images = cleaned_images + [db_image.id]
        crud.update_product_images(db=db, product_id=product_id, images=updated_images)

        product_after = db.query(models.Product).filter(models.Product.id == product_id).first()
        print(f"Product {product_id} images after update: {product_after.images}")
    except Exception as e:
        db.rollback()
        print("Error:", e)
    finally:
        db.close()


if __name__ == '__main__':
    main()
