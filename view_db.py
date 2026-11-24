import sqlite3

db = sqlite3.connect("donors.db")
db.row_factory = sqlite3.Row
print("Tables:", [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")])

rows = db.execute("SELECT * FROM donors ORDER BY id").fetchall()
print("Total donors stored:", len(rows), "\n")
for r in rows:
    d = dict(r)
    d["pin_hash"] = d["pin_hash"][:25] + "..."
    d["available"] = "Yes" if d["available"] else "No"
    print("-" * 50)
    for k, v in d.items():
        print(f"{k:<14}: {v}")
print("-" * 50)