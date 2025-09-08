import sqlite3


def verify_schema():
    conn = sqlite3.connect("data/history.db")
    cursor = conn.cursor()

    print("=== Supplier Documents Schema ===")
    columns = cursor.execute("PRAGMA table_info(supplier_documents)").fetchall()
    for col in columns:
        print(f"{col[1]}: {col[2]} (nullable: {col[3] == 0}, default: {col[4]})")

    print("\n=== Indexes on supplier_documents ===")
    indexes = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='supplier_documents'"
    ).fetchall()
    for idx in indexes:
        print(idx[0])

    print("\n=== Document Status Values ===")
    # Check if we have any data to verify status values
    statuses = cursor.execute(
        "SELECT DISTINCT status FROM supplier_documents"
    ).fetchall()
    if statuses:
        print("Existing statuses:", [s[0] for s in statuses])
    else:
        print("No documents yet - status constraint will be enforced on new records")

    conn.close()


if __name__ == "__main__":
    verify_schema()
