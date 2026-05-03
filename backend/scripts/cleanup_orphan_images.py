import os
import sqlite3
import shutil
from datetime import datetime
import json

DB_PATH = 'marketplace.db'
UPLOADS_PRODUCTS_DIR = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'uploads', 'products')
BACKUP_ROOT = os.path.join('..', 'db_backups')
MOVED_LIST_FILE = os.path.join(os.path.dirname(__file__), 'moved_orphan_images.txt')


def gather_referenced_basenames(conn):
    refs = set()
    c = conn.cursor()
    # products.images
    try:
        c.execute('SELECT images FROM products')
        for (images_raw,) in c.fetchall():
            if not images_raw:
                continue
            try:
                parsed = json.loads(images_raw)
                if isinstance(parsed, list):
                    for v in parsed:
                        if isinstance(v, str):
                            refs.add(os.path.basename(v))
                    continue
            except Exception:
                pass
            # fallback: treat as single string or comma list
            if isinstance(images_raw, str):
                parts = [p.strip() for p in images_raw.strip('[]').split(',') if p.strip()]
                for p in parts:
                    refs.add(os.path.basename(p.strip('\"\'')))
    except Exception:
        pass

    # product_images table if present
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_images'")
        if c.fetchone():
            c.execute('SELECT file_path FROM product_images')
            for (fp,) in c.fetchall():
                if not fp:
                    continue
                refs.add(os.path.basename(fp))
    except Exception:
        pass

    return refs


def main():
    if not os.path.exists(DB_PATH):
        print('DB not found:', DB_PATH)
        return
    if not os.path.isdir(UPLOADS_PRODUCTS_DIR):
        print('Uploads products dir not found:', UPLOADS_PRODUCTS_DIR)
        return

    conn = sqlite3.connect(DB_PATH)
    referenced = gather_referenced_basenames(conn)
    conn.close()

    all_files = []
    for root, _, files in os.walk(UPLOADS_PRODUCTS_DIR):
        for f in files:
            all_files.append((root, f))

    orphan_files = []
    for root, fname in all_files:
        if fname not in referenced:
            orphan_files.append(os.path.join(root, fname))

    print('Total files in uploads/products:', len(all_files))
    print('Referenced image basenames from DB:', len(referenced))
    print('Orphan files to move:', len(orphan_files))

    if not orphan_files:
        print('No orphan files found. Done.')
        return

    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    dest_dir = os.path.join(BACKUP_ROOT, f'orphan_images_{ts}')
    os.makedirs(dest_dir, exist_ok=True)

    moved = []
    for fp in orphan_files:
        try:
            rel = os.path.relpath(fp, UPLOADS_PRODUCTS_DIR)
            target = os.path.join(dest_dir, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(fp, target)
            moved.append((fp, target))
        except Exception as e:
            print('Failed to move', fp, 'error:', e)

    # write moved list
    with open(MOVED_LIST_FILE, 'w', encoding='utf-8') as fh:
        for src, dst in moved:
            fh.write(f"{src} -> {dst}\n")

    print('Moved', len(moved), 'files to', dest_dir)
    print('Moved list saved to', MOVED_LIST_FILE)


if __name__ == '__main__':
    main()
