import sqlite3, json, sys

DB_PATH = 'marketplace.db'

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
    except Exception as e:
        print('ERROR: cannot open DB', DB_PATH, e)
        sys.exit(2)
    c = conn.cursor()
    def q(sql):
        c.execute(sql)
        return c.fetchone()[0]
    try:
        print('total_products=', q('select count(*) from products'))
        print("approved_and_active=", q("select count(*) from products where is_active=1 and approval_status='approved'"))
        print("pending=", q("select count(*) from products where approval_status='pending'"))
        print('inactive=', q('select count(*) from products where is_active=0'))
        print('\nSamples (limit 5):')
        c.execute('select id,title,slug,price,is_active,approval_status,images from products limit 5')
        rows = c.fetchall()
        for r in rows:
            pid, title, slug, price, is_active, approval_status, images = r
            try:
                imgs = json.loads(images) if images else []
            except Exception:
                imgs = images
            print(f"- id={pid} title={title[:60]!r} price={price} active={is_active} status={approval_status} images_count={len(imgs) if isinstance(imgs, list) else 'N/A'}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
