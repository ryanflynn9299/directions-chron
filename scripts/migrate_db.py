import sqlite3
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Locate the database relative to the script location or environment variable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(SCRIPT_DIR, '..', 'data', 'traffic_data.db'))

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a specific table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns

def migrate():
    """
    Migrates the existing traffic_data.db to include the new columns 
    (route_group_id, job_id, alias) and retroactively computes route_group_id 
    for all existing rows to preserve historical queryability.
    """
    db_abs_path = os.path.abspath(DB_PATH)
    if not os.path.exists(db_abs_path):
        logger.error(f"Database not found at {db_abs_path}. Exiting.")
        return

    logger.info(f"Connecting to database at {db_abs_path}...")
    
    # Check file and directory permissions
    if not os.access(db_abs_path, os.W_OK):
        logger.error(f"Write permission denied for database file at {db_abs_path}. Please check file permissions.")
        return
        
    db_dir = os.path.dirname(db_abs_path)
    if not os.access(db_dir, os.W_OK):
        logger.warning(f"Write permission denied for database directory {db_dir}. SQLite may fail to create a journal/WAL file if needed.")

    conn = sqlite3.connect(db_abs_path)
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traffic_data'")
        if not cursor.fetchone():
            logger.error("Table 'traffic_data' does not exist in the database. Cannot migrate.")
            return

        # 1. Add Columns
        logger.info("Checking and adding missing columns...")
        
        columns_to_add = {
            "route_group_id": "VARCHAR",
            "job_id": "VARCHAR",
            "alias": "VARCHAR"
        }

        for col_name, col_type in columns_to_add.items():
            if not column_exists(cursor, "traffic_data", col_name):
                logger.info(f"Attempting to add column '{col_name}' of type {col_type}...")
                cursor.execute(f"ALTER TABLE traffic_data ADD COLUMN {col_name} {col_type}")
                logger.info(f"Successfully added column '{col_name}'.")
            else:
                logger.info(f"Column '{col_name}' already exists. Skipping.")

        # Commit column additions before attempting updates
        conn.commit()

        # 2. Compute and retroactive-fill route_group_id
        logger.info("Updating historical rows with computed route_group_id...")
        
        # Verify the column was actually added before trying to update it
        if not column_exists(cursor, "traffic_data", "route_group_id"):
            raise RuntimeError("route_group_id column was not found even after attempted addition.")

        # Fetch all existing rows
        cursor.execute("SELECT id, origin, destination, route_group_id FROM traffic_data")
        rows = cursor.fetchall()
        
        update_count = 0
        for row_id, origin, destination, current_route_group_id in rows:
            # Replicate the Python logic: "|".join(sorted([origin, destination]))
            expected_route_group_id = "|".join(sorted([origin, destination]))
            
            # Only update if null or different
            if current_route_group_id != expected_route_group_id:
                cursor.execute(
                    "UPDATE traffic_data SET route_group_id = ? WHERE id = ?",
                    (expected_route_group_id, row_id)
                )
                update_count += 1
            
        logger.info(f"Successfully migrated {update_count} existing rows to have the correct route_group_id.")
        
        # 3. Handle Indices
        logger.info("Creating indices if they do not exist...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_traffic_data_route_group_id ON traffic_data (route_group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_traffic_data_job_id ON traffic_data (job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_traffic_data_alias ON traffic_data (alias)")
        logger.info("Indices verified/created.")

        # 4. Create Saved Routes table (Phase 7)
        logger.info("Ensuring saved_routes table exists...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_routes (
                alias VARCHAR PRIMARY KEY,
                source VARCHAR NOT NULL,
                destinations_json VARCHAR NOT NULL,
                bidirectional INTEGER DEFAULT 1
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_saved_routes_alias ON saved_routes (alias)")

        # 5. Create Destination Batches table
        logger.info("Ensuring destination_batches table exists...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS destination_batches (
                alias VARCHAR PRIMARY KEY,
                destinations_json VARCHAR NOT NULL
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_destination_batches_alias ON destination_batches (alias)")

        conn.commit()
        logger.info("Database migration completed successfully.")

    except sqlite3.OperationalError as e:
        logger.error(f"SQLite Operational Error during migration: {e}")
        conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Migration failed with an unexpected error: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
