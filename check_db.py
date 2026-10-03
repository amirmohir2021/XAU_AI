import sqlite3

db = r"data\xau_ai_memory.db"
conn = sqlite3.connect(db)

print("TABLES:")
print(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())

print("\nSIGNALS COLUMNS:")
for row in conn.execute("PRAGMA table_info(signals)").fetchall():
    print(row)

conn.close()
