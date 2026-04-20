import sqlite3

DB_PATH = "data/farm.db"

def normalize(path: str) -> str:
    if not path:
        return path
    p = path.replace("\\", "/")

    # If it already looks like a URL path, keep it
    if p.startswith("/uploads/"):
        return p

    # If it starts with uploads/, prefix /
    if p.startswith("uploads/"):
        return "/" + p

    # If uploads/ appears somewhere in the path, cut from there
    idx = p.find("uploads/")
    if idx != -1:
        return "/" + p[idx:]

    # Otherwise keep as-is (could be absolute path)
    return p

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rows = cur.execute("SELECT id, image_path FROM health_checks").fetchall()
    changed = 0

    for row_id, old in rows:
        new = normalize(old)
        if new != old:
            cur.execute("UPDATE health_checks SET image_path=? WHERE id=?", (new, row_id))
            changed += 1

    conn.commit()
    conn.close()
    print(f"✅ Migrated {changed} row(s) in health_checks")

if __name__ == "__main__":
    main()
