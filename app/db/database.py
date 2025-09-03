import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a new database connection."""
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            port=settings.DB_PORT,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize database schema."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create prompt_logs table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_logs (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(255) NOT NULL,
                input_text TEXT NOT NULL,
                classification VARCHAR(50) NOT NULL,
                confidence FLOAT NOT NULL,
                model_version VARCHAR(50) NOT NULL,
                prompt_version VARCHAR(50) NOT NULL,
                raw_response TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create index in a separate statement
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompt_logs_request_id ON prompt_logs(request_id);
        """)
        
        conn.commit()
        cursor.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_db():
    """Get database connection as a dependency."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
