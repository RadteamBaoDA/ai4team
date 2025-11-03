"""
Persistent cache for file hashes using SQLite
"""

import sqlite3
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
from functools import lru_cache
from config.settings import BASE_DIR


# Cache database location
CACHE_DB = BASE_DIR / "logs" / "hash_cache.db"


class HashCache:
    """Persistent hash cache using SQLite"""
    
    def __init__(self, db_path: Path = CACHE_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_hashes (
                    file_path TEXT PRIMARY KEY,
                    file_size INTEGER NOT NULL,
                    modified_time INTEGER NOT NULL,
                    hash_value TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    cached_at TEXT NOT NULL
                )
            """)
            # Create index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_path 
                ON file_hashes(file_path)
            """)
            conn.commit()
        finally:
            conn.close()
    
    def get(self, file_path: Path, file_size: int, modified_ns: int, algorithm: str = 'md5') -> Optional[str]:
        """Get cached hash if file hasn't changed"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT hash_value FROM file_hashes
                WHERE file_path = ? 
                AND file_size = ? 
                AND modified_time = ?
                AND algorithm = ?
            """, (str(file_path.resolve()), file_size, modified_ns, algorithm))
            
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    
    def set(self, file_path: Path, file_size: int, modified_ns: int, hash_value: str, algorithm: str = 'md5'):
        """Store hash in cache"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO file_hashes 
                (file_path, file_size, modified_time, hash_value, algorithm, cached_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(file_path.resolve()),
                file_size,
                modified_ns,
                hash_value,
                algorithm,
                datetime.now().isoformat()
            ))
            conn.commit()
        finally:
            conn.close()
    
    def clear_old_entries(self, days: int = 30):
        """Remove cache entries older than specified days"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                DELETE FROM file_hashes
                WHERE datetime(cached_at) < datetime('now', '-' || ? || ' days')
            """, (days,))
            conn.commit()
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
        finally:
            conn.close()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM file_hashes")
            count = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT 
                    MIN(datetime(cached_at)) as oldest,
                    MAX(datetime(cached_at)) as newest
                FROM file_hashes
            """)
            oldest, newest = cursor.fetchone()
            
            return {
                'total_entries': count,
                'oldest_entry': oldest,
                'newest_entry': newest
            }
        finally:
            conn.close()


# Global cache instance
_hash_cache = None


def get_hash_cache() -> HashCache:
    """Get or create global hash cache instance"""
    global _hash_cache
    if _hash_cache is None:
        _hash_cache = HashCache()
    return _hash_cache
