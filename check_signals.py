import sqlite3

db = r"data\xau_ai_memory.db"
conn = sqlite3.connect(db)

print("SIGNAL COUNT:")
print(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0])

print("\nLAST 10 SIGNALS:")
rows = conn.execute("""
    SELECT id, signal_time, direction, entry, stop_loss, tp1, tp2,
           confirmations, alignment, result, result_r
    FROM signals
    ORDER BY id DESC
    LIMIT 10
""").fetchall()

for row in rows:
    print(row)

conn.close()
