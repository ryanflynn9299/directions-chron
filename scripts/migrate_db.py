import sqlite3
import os

# Locate the database relative to the script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'traffic_data.db')

def migrate():
    """
    Migrates the existing traffic_data.db to include the new columns 
    (route_group_id, job_id, alias) and retroactively computes route_group_id 
    for all existing rows to preserve historical queryability.
    """
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Exiting.")
        return

    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Add Columns (SQLite requires doing this one by one)
        print("Adding new columns...")
        
        # We use a TRY-CATCH block per column just in case the script is run twice
        try:
            cursor.execute("ALTER TABLE traffic_data ADD COLUMN route_group_id VARCHAR")
            print(" - Added route_group_id")
        except sqlite3.OperationalError:
            print(" - route_group_id already exists")
            
        try:
            cursor.execute("ALTER TABLE traffic_data ADD COLUMN job_id VARCHAR")
            print(" - Added job_id")
        except sqlite3.OperationalError:
            print(" - job_id already exists")

        try:
            cursor.execute("ALTER TABLE traffic_data ADD COLUMN alias VARCHAR")
            print(" - Added alias")
        except sqlite3.OperationalError:
            print(" - alias already exists")

        # 2. Compute and retroactive-fill route_group_id
        print("Updating historical rows with computed route_group_id...")
        
        # Fetch all existing rows
        cursor.execute("SELECT id, origin, destination FROM traffic_data")
        rows = cursor.fetchall()
        
        update_count = 0
        for row_id, origin, destination in rows:
            # Replicate the Python logic: "|".join(sorted([origin, destination]))
            route_group_id = "|".join(sorted([origin, destination]))
            
            cursor.execute(
                "UPDATE traffic_data SET route_group_id = ? WHERE id = ?",
                (route_group_id, row_id)
            )
            update_count += 1
            
        print(f"Successfully migrated {update_count} existing rows.")
        
        # Optionally add indices as defined by SQLAlchemy models to speed up lookup
        try:
            cursor.execute("CREATE INDEX ix_traffic_data_route_group_id ON traffic_data (route_group_id)")
            cursor.execute("CREATE INDEX ix_traffic_data_job_id ON traffic_data (job_id)")
            cursor.execute("CREATE INDEX ix_traffic_data_alias ON traffic_data (alias)")
            print("Created indices for new columns.")
        except sqlite3.OperationalError:
            print("Indices already exist.")

        # 3. Create Saved Routes table (Phase 7)
        print("Ensuring saved_routes table exists...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_routes (
                alias VARCHAR PRIMARY KEY,
                source VARCHAR NOT NULL,
                destinations_json VARCHAR NOT NULL,
                bidirectional INTEGER DEFAULT 1
            )
        ''')
        try:
            cursor.execute("CREATE INDEX ix_saved_routes_alias ON saved_routes (alias)")
        except sqlite3.OperationalError:
            pass


        conn.commit()
        print("Database migration completed successfully.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
