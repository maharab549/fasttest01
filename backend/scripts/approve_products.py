import sqlite3, shutil, os, sys
from datetime import datetime

DB_PATH = 'marketplace.db'
BACKUP_DIR = os.path.join('..', 'db_backups')

def backup_db(db_path):
    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs(BACKUP_DIR, exist_ok=True)
    basename = os.path.basename(db_path)
    dest = os.path.join(BACKUP_DIR, f"{ts}_{basename}")
    shutil.copy2(db_path, dest)
    return dest


def main():
    if not os.path.exists(DB_PATH):
        print('ERROR: DB not found at', DB_PATH)
        sys.exit(2)

    print('Backing up DB...')
    b = backup_db(DB_PATH)
    print('Backup created at', b)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Update products to approved and active
    print('Updating products to approval_status="approved" and is_active=1')
    c.execute("UPDATE products SET approval_status='approved', is_active=1 WHERE approval_status!='approved' OR is_active=0")
    updated = c.rowcount
    conn.commit()

    print(f'Rows updated: {updated}')

    # Verification
    def q(sql):
        c.execute(sql)
        return c.fetchone()[0]

    print('total_products=', q('select count(*) from products'))
    print("approved_and_active=", q("select count(*) from products where is_active=1 and approval_status='approved'"))
    print("pending=", q("select count(*) from products where approval_status='pending'"))
    print('inactive=', q('select count(*) from products where is_active=0'))

    print('\nSample (5):')
    c.execute('select id,title,slug,price,is_active,approval_status,images from products limit 5')
    rows = c.fetchall()
    import json
    for r in rows:
        pid, title, slug, price, is_active, approval_status, images = r
        try:
            imgs = json.loads(images) if images else []
        except Exception:
            imgs = images
        print(f"- id={pid} title={title!r} price={price} active={is_active} status={approval_status} images_count={len(imgs) if isinstance(imgs, list) else 'N/A'}")

    conn.close()

if __name__ == '__main__':
    main()
