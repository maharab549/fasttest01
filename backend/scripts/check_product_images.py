import sqlite3, json, os, sys
from collections import Counter

DB_PATH = 'marketplace.db'
# Derive backend directory reliably from this script's location (script lives in backend/scripts)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Also accept the explicit absolute path the user provided (useful if workspace root differs)
USER_PROVIDED_UPLOADS = r'D:\All github project\Final backup working deploy\fasttest01\backend\uploads'

POSSIBLE_UPLOAD_DIRS = [
    # backend-relative locations
    os.path.join(BACKEND_DIR, 'uploads'),
    os.path.join(BACKEND_DIR, 'uploads', 'products'),
    os.path.join(BACKEND_DIR, 'app', 'uploads'),
    os.path.join(BACKEND_DIR, 'app', 'static', 'uploads'),
    # a higher-level uploads folder if present
    os.path.abspath(os.path.join(BACKEND_DIR, '..', 'uploads')),
    # explicit user-provided path (from their message)
    USER_PROVIDED_UPLOADS,
]


def parse_images_field(val):
    if not val:
        return []
    if isinstance(val, (list, tuple)):
        return list(val)
    s = val
    # Try JSON first
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
        # sometimes stored as stringified dict or str
    except Exception:
        pass
    # Fallback: try to extract quoted substrings
    imgs = []
    cur = ''
    in_quote = False
    for ch in s:
        if ch in "'\"":
            in_quote = not in_quote
            if not in_quote and cur:
                imgs.append(cur.strip())
                cur = ''
            continue
        if in_quote:
            cur += ch
    if imgs:
        return imgs
    # Last fallback: split on commas and strip
    parts = [p.strip() for p in s.strip('[]()').split(',') if p.strip()]
    return parts


def collect_existing_files(dirs):
    files = set()
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for root, _, filenames in os.walk(d):
            for fn in filenames:
                files.add(os.path.join(root, fn))
                files.add(fn)  # also by basename
    return files


def main():
    if not os.path.exists(DB_PATH):
        print('ERROR: DB not found at', DB_PATH)
        sys.exit(2)

    print('Checking marketplace DB:', DB_PATH)
    print('Searching for upload dirs (candidates):')
    for d in POSSIBLE_UPLOAD_DIRS:
        print(' -', d, 'exists=' + str(os.path.isdir(d)))

    existing_files = collect_existing_files(POSSIBLE_UPLOAD_DIRS)
    print('Total files found in upload dirs:', len(existing_files))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('select count(*) from products')
    total = c.fetchone()[0]

    c.execute('select id, title, images from products')
    rows = c.fetchall()

    total_with_images = 0
    total_image_entries = 0
    per_product_counts = []
    missing_file_counts = 0
    image_paths_counter = Counter()

    products_with_missing = []
    products_with_images = []

    for pid, title, images_raw in rows:
        imgs = parse_images_field(images_raw)
        # normalize image entries to basenames or paths
        norm = []
        for im in imgs:
            if not isinstance(im, str):
                continue
            im = im.strip()
            if not im:
                continue
            # sometimes stored like '/uploads/abc.jpg' or 'uploads/abc.jpg' or full URL
            basename = os.path.basename(im)
            norm.append((im, basename))
            image_paths_counter[basename] += 1
        cnt = len(norm)
        per_product_counts.append(cnt)
        total_image_entries += cnt
        if cnt > 0:
            total_with_images += 1
            products_with_images.append((pid, title, norm))
            # check file existence (by basename or full path)
            missing = False
            for full, base in norm:
                found = False
                # check by basename and by full relative path
                if base in existing_files:
                    found = True
                elif full in existing_files:
                    found = True
                else:
                    # also check possible relative path under upload dirs
                    for d in POSSIBLE_UPLOAD_DIRS:
                        fp = os.path.join(d, base)
                        if fp in existing_files or os.path.exists(fp):
                            found = True
                            break
                if not found:
                    missing = True
            if missing:
                missing_file_counts += 1
                products_with_missing.append((pid, title, norm))

    avg_images = (total_image_entries / total) if total else 0
    max_images = max(per_product_counts) if per_product_counts else 0

    print('\nSUMMARY:')
    print(' total_products =', total)
    print(' products_with_images =', total_with_images)
    print(' total_image_entries =', total_image_entries)
    print(' average_images_per_product =', round(avg_images, 2))
    print(' max_images_on_one_product =', max_images)
    print(' products_with_missing_image_files =', missing_file_counts)

    print('\nTop 10 most common image basenames:')
    for name, cnt in image_paths_counter.most_common(10):
        print(' ', name, cnt)

    print('\nSample products with images (up to 10):')
    for pid, title, norm in products_with_images[:10]:
        print(f" - id={pid} title={title!r} images_count={len(norm)} first_images={[n[0] for n in norm[:3]]}")

    print('\nSample products missing image files (up to 10):')
    for pid, title, norm in products_with_missing[:10]:
        print(f" - id={pid} title={title!r} images={norm}")

    conn.close()

if __name__ == '__main__':
    main()
