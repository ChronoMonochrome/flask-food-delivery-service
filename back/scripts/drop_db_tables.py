# drop_db_tables.py
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import inspect

# Ensure the application root is in the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

load_dotenv() # Load environment variables from .env file

from app import create_app
from app.models import db, MainCategory, Category, Product, Addon, Recommendation, ProductAddon, ProductRecommendation
from app.logger import logger

def truncate_all_tables():
    app = create_app()
    db.init_app(app)

    with app.app_context():
        logger.warning("!!! WARNING: Attempting to TRUNCATE ALL database tables. All data will be LOST and auto-increment counters reset. !!!")
        try:
            # Get a list of all table names from the metadata
            # It's important to truncate tables in an order that respects foreign key constraints
            # or to use CASCADE if your database supports it and you desire it.
            # For simplicity, we'll get them in reverse order of definition or alphabetically
            # and try to truncate. If there are complex FKs, you might need a specific order
            # or to disable FK checks temporarily.

            # Get all mapped classes
            all_models = [MainCategory,Category, Product, Addon, Recommendation, ProductAddon, ProductRecommendation]
            
            # Sort models based on dependencies for safer truncation if not using CASCADE
            # This simple sorting might not cover all complex dependency graphs.
            # A more robust solution might involve inspecting foreign keys directly or
            # disabling/re-enabling foreign key checks.
            # For this example, a reverse alphabetical sort of table names is a common simple approach
            # or listing them explicitly from dependent to independent.
            
            # Example: Explicit order from dependent to independent (or for cascading delete)
            # Adjust this order based on your actual foreign key relationships.
            # Tables with foreign keys should generally be truncated *before* the tables they reference,
            # OR you need to handle CASCADE (which TRUNCATE often doesn't do by default like DELETE)
            # or temporarily disable foreign key checks.

            # A common safe order for truncation is: join tables, then children, then parents.
            tables_to_truncate = [
                ProductAddon.__tablename__,
                ProductRecommendation.__tablename__,
                Product.__tablename__,
                Addon.__tablename__,
                Recommendation.__tablename__,
                Category.__tablename__,
                MainCategory.__tablename__,
            ]
            
            # If your database supports TRUNCATE ... CASCADE, it's generally cleaner.
            # PostgreSQL example: `TRUNCATE TABLE table_name RESTART IDENTITY CASCADE;`
            # MySQL example (requires setting FK checks off):
            # `SET FOREIGN_KEY_CHECKS = 0;`
            # `TRUNCATE TABLE table_name;`
            # `SET FOREIGN_KEY_CHECKS = 1;`

            connection = db.engine.connect()
            trans = connection.begin() # Start a transaction for atomicity

            # For SQLite (default in Flask-SQLAlchemy for quick setups), TRUNCATE is not a real command.
            # DELETE from table_name; is effectively used, and for resetting PKs, you need to
            # DELETE from sqlite_sequence WHERE name='table_name';

            # Let's add a check for the database dialect to handle common cases
            dialect_name = db.engine.dialect.name
            
            if dialect_name == 'postgresql':
                logger.info("Using PostgreSQL specific TRUNCATE with RESTART IDENTITY CASCADE.")
                for table_name in tables_to_truncate:
                    sql = f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"
                    connection.execute(db.text(sql))
                    logger.info(f"Truncated table: {table_name}")
            elif dialect_name == 'mysql':
                logger.info("Using MySQL specific TRUNCATE with foreign key checks toggling.")
                connection.execute(db.text("SET FOREIGN_KEY_CHECKS = 0;"))
                for table_name in tables_to_truncate:
                    sql = f"TRUNCATE TABLE {table_name};"
                    connection.execute(db.text(sql))
                    logger.info(f"Truncated table: {table_name}")
                connection.execute(db.text("SET FOREIGN_KEY_CHECKS = 1;"))
            else: # Generic fallback for other DBs (like SQLite which doesn't have TRUNCATE) or non-cascading
                logger.info(f"Using generic DELETE statement for dialect: {dialect_name}")
                # Important: For generic DELETE, order is crucial to avoid foreign key errors.
                # Process tables with foreign keys first (e.g., join tables, then children, then parents).
                # The `tables_to_truncate` list is already ordered.
                for table_name in tables_to_truncate:
                    sql = f"DELETE FROM {table_name};"
                    connection.execute(db.text(sql))
                    logger.info(f"Deleted all rows from table: {table_name}")
                    
                    # For SQLite, manually reset auto-increment if applicable
                    if dialect_name == 'sqlite':
                        inspector = inspect(db.engine)
                        # Check if table has an auto-incrementing primary key
                        pk_columns = inspector.get_primary_keys(table_name)
                        if any(col for col in inspector.get_columns(table_name) if col['name'] in pk_columns and col.get('autoincrement')):
                             reset_sql = f"DELETE FROM sqlite_sequence WHERE name='{table_name}';"
                             connection.execute(db.text(reset_sql))
                             logger.info(f"Reset auto-increment for SQLite table: {table_name}")
            
            trans.commit()
            logger.info("Successfully truncated all database tables.")
        except Exception as e:
            if trans.is_active: # Check if transaction is still active before rollback
                trans.rollback()
            logger.error(f"Error truncating tables: {e}", exc_info=True)
            sys.exit(1) # Exit with error code
        finally:
            connection.close() # Ensure the connection is closed
            db.session.remove() # Clean up session resources

if __name__ == '__main__':
    truncate_all_tables()
