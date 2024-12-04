import psycopg
from psycopg import sql
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
SUPERUSER_DB = "postgres"
SUPERUSER_USER = "postgres"
SUPERUSER_PASSWORD = "1Tommy12341!"  # Consider using environment variables for security
SUPERUSER_HOST = "localhost"
SUPERUSER_PORT = "5432"

DB_NAME = "my_database"
DB_USER = "app_user"

# List of tables in reverse order to handle dependencies
TABLES = [ 
    "TemporaryEnrichmentData",
    "TemporaryDischarge",
    "AuditLog",
    "Review",
    "DischargeProvider",
    "ProviderEpic",
    "EpicHospital",
    "EpicInsurance",
    "PatientInsurance",
    "Discharge",
    "Epic",
    "RawDataIngested",
    "ProviderProviderType",
    "Provider",
    "ProviderType",
    "Insurance",
    "PatientEmail",
    "PatientPhone",
    "PatientAddress",
    "Patient",
    "AppUser",
    "Hospital",
    "ImportType",
    "EnrichmentTypes",
    "RawDataIngestedAudit",
    "TemporaryEnrichmentDataAudit",
    "TemporaryDischargeAudit"
]


def drop_tables():
    """Drop all tables in the target database."""
    try:
        # Connect to the target database using context manager
        with psycopg.connect(
            dbname=DB_NAME,
            user=SUPERUSER_USER,
            password=SUPERUSER_PASSWORD,
            host=SUPERUSER_HOST,
            port=SUPERUSER_PORT
        ) as connection:
            with connection.cursor() as cursor:
                # Drop tables in the specified order with CASCADE
                for table in TABLES:
                    cursor.execute(
                        sql.SQL("DROP TABLE IF EXISTS {table} CASCADE;").format(
                            table=sql.Identifier(table)
                        )
                    )
                    logging.info(f"Dropped table '{table}'.")
        logging.info("All tables dropped successfully.")
    except Exception as e:
        logging.error(f"Error dropping tables: {e}")
        sys.exit(1)

def drop_database_and_role():
    """Drop the target database and role."""
    try:
        # Connect to superuser database using context manager
        with psycopg.connect(
            dbname=SUPERUSER_DB,
            user=SUPERUSER_USER,
            password=SUPERUSER_PASSWORD,
            host=SUPERUSER_HOST,
            port=SUPERUSER_PORT
        ) as connection:
            # Enable autocommit mode for dropping databases and roles
            connection.autocommit = True
            with connection.cursor() as cursor:
                # Terminate all connections to the target database
                cursor.execute(
                    sql.SQL("""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = {dbname}
                          AND pid <> pg_backend_pid();
                    """).format(
                        dbname=sql.Literal(DB_NAME)
                    )
                )
                logging.info(f"Terminated all connections to database '{DB_NAME}'.")

                # Check if the database exists
                cursor.execute(
                    sql.SQL("SELECT 1 FROM pg_database WHERE datname = {dbname};").format(
                        dbname=sql.Literal(DB_NAME)
                    )
                )
                if cursor.fetchone():
                    logging.info(f"Database '{DB_NAME}' exists. Dropping...")
                    cursor.execute(
                        sql.SQL("DROP DATABASE {dbname};").format(
                            dbname=sql.Identifier(DB_NAME)
                        )
                    )
                    logging.info(f"Database '{DB_NAME}' dropped successfully.")
                else:
                    logging.info(f"Database '{DB_NAME}' does not exist.")

                # Check if the role exists
                cursor.execute(
                    sql.SQL("SELECT 1 FROM pg_roles WHERE rolname = {rolname};").format(
                        rolname=sql.Literal(DB_USER)
                    )
                )
                if cursor.fetchone():
                    logging.info(f"Role '{DB_USER}' exists. Dropping...")
                    cursor.execute(
                        sql.SQL("DROP ROLE {rolname};").format(
                            rolname=sql.Identifier(DB_USER)
                        )
                    )
                    logging.info(f"Role '{DB_USER}' dropped successfully.")
                else:
                    logging.info(f"Role '{DB_USER}' does not exist.")
    except Exception as e:
        logging.error(f"Error dropping database or role: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logging.info("Step 1: Dropping tables...")
    drop_tables()

    logging.info("Step 2: Dropping database and role...")
    drop_database_and_role()

    logging.info("Teardown complete!")
