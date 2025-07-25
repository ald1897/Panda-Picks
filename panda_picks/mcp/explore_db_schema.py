import sqlite3

def explore_database_schema(db_path="database/nfl_data.db"):
    """
    Explore and display the schema of the SQLite database including tables and columns.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"Database contains {len(tables)} tables:")

        # For each table, get column info
        for table_name in [table[0] for table in tables]:
            print(f"\n📊 Table: {table_name}")

            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            print("Columns:")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                pk_str = "🔑 PRIMARY KEY" if pk else ""
                null_str = "NOT NULL" if not_null else "NULL allowed"
                print(f"  - {col_name} ({col_type}) {pk_str} {null_str}")

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            print(f"Total rows: {row_count}")

            # Get sample data (first 3 rows)
            if row_count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample_rows = cursor.fetchall()
                print("Sample data (first 3 rows):")
                for row in sample_rows:
                    print(f"  {row}")

        conn.close()
        return True
    except Exception as e:
        print(f"Error exploring database: {e}")
        return False

if __name__ == "__main__":
    explore_database_schema()
