import sqlite3
import os
import shutil
from datetime import datetime
import json

DB_PATH = 'marketplace.db'
BACKUP_DIR = os.path.join('..', 'db_backups')
UPLOADS_DIR = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'uploads', 'products')


def backup_db(db_path):
    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs(BACKUP_DIR, exist_ok=True)
    basename = os.path.basename(db_path)
    dest = os.path.join(BACKUP_DIR, f"{ts}_{basename}")
    shutil.copy2(db_path, dest)
    return dest


def parse_images_field(val):
    if not val:
        return []
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    # fallback: extract quoted substrings or split
    if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
        # try simple split
        parts = [p.strip().strip('\"\'') for p in val.strip('[]').split(',') if p.strip()]
        return parts
    # last fallback: treat as single path string
    if isinstance(val, str):
        return [val]
    return []


def collect_existing_files(upload_dir):
    files = set()
    if not os.path.isdir(upload_dir):
        return files
    for root, _, filenames in os.walk(upload_dir):
        for fn in filenames:
            files.add(fn)
    return files


def find_tables_with_product_id(conn):
    c = conn.cursor()
    c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    tables = []
    for name, sql in c.fetchall():
        # simple detection: look for 'product_id' in table SQL
        if 'product_id' in (sql or ''):
            tables.append(name)
    return tables


def main():
    if not os.path.exists(DB_PATH):
        print('DB not found:', DB_PATH)
        return
    print('Backing up DB...')
    b = backup_db(DB_PATH)
    print('Backup saved to', b)

    existing_basenames = collect_existing_files(UPLOADS_DIR)
    print('Upload products dir:', UPLOADS_DIR, 'found_files=', len(existing_basenames))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT id, images FROM products')
    rows = c.fetchall()
    missing_ids = []
    for pid, images_raw in rows:
        imgs = parse_images_field(images_raw)
        basenames = [os.path.basename(i) for i in imgs if isinstance(i, str) and i.strip()]
        if not basenames:
            # treat as missing
            missing_ids.append(pid)
            continue
        found_any = False
        for bname in basenames:
            if bname in existing_basenames:
                found_any = True
                break
        if not found_any:
            missing_ids.append(pid)

    print('Products missing images (count)=', len(missing_ids))
    if len(missing_ids) == 0:
        print('Nothing to delete.')
        conn.close()
        return

    # Confirm: proceed to delete
    print('Deleting products and related rows for product_ids:', missing_ids[:50])

    # Find tables that reference product_id and delete rows
    tables = find_tables_with_product_id(conn)
    print('Tables referencing product_id (detected):', tables)

    # Delete from child tables first
    for t in tables:
        try:
            q = f"DELETE FROM {t} WHERE product_id IN ({','.join('?' for _ in missing_ids)})"
            c.execute(q, missing_ids)
            print(f'Deleted from {t}:', c.rowcount)
        except Exception as e:
            print('Skipping delete from', t, 'error:', e)

    # Delete from products
    q = f"DELETE FROM products WHERE id IN ({','.join('?' for _ in missing_ids)})"
    c.execute(q, missing_ids)
    print('Deleted from products:', c.rowcount)

    conn.commit()

    # Final verification
    c.execute('SELECT count(*) FROM products')
    print('Remaining products count:', c.fetchone()[0])

    conn.close()


if __name__ == '__main__':
    main()
