"""
Database Manager for GitMiner v3

This module handles SQLite database operations for tracking
search history and downloaded files.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from colorama import Fore

from gitminer.utils import highlight


class DatabaseManager:
    """
    Manages SQLite database operations for search history tracking.
    
    Provides methods for initializing the database, recording searches,
    and querying historical data.
    """

    def __init__(self, database_path: str = "gitminer_history.sqlite"):
        """
        Initialize the database manager.

        Args:
            database_path: Path to the SQLite database file
        """
        self.database_path = Path(database_path)
        self.connection: Optional[sqlite3.Connection] = None
        self._initialize_database()

    def _initialize_database(self) -> None:
        """
        Initialize the database and create tables if they don't exist.
        """
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.connection = sqlite3.connect(
                str(self.database_path),
                check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row
            
            cursor = self.connection.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dork TEXT NOT NULL,
                    searched_at TEXT NOT NULL,
                    results_count INTEGER DEFAULT 0,
                    downloaded_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloaded_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dork TEXT NOT NULL,
                    repository TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    local_path TEXT,
                    item_url TEXT,
                    searched_at TEXT,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    UNIQUE(repository, file_path, dork)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    label TEXT NOT NULL,
                    matched_text TEXT,
                    context TEXT,
                    line_number INTEGER,
                    severity TEXT,
                    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES downloaded_files(id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_dork
                ON search_history(dork)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_files_dork
                ON downloaded_files(dork)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_findings_severity
                ON findings(severity)
            """)
            
            self.connection.commit()
            
            print(highlight(
                f"[+] Database initialized: {self.database_path}",
                Fore.GREEN
            ))
            
        except Exception as error:
            print(highlight(
                f"[!] Error initializing database: {error}",
                Fore.RED
            ))
            raise

    def record_search(
        self,
        dork: str,
        searched_at: str,
        results_count: int = 0,
        downloaded_count: int = 0
    ) -> Optional[int]:
        """
        Record a search operation in the database.

        Args:
            dork: The search query used
            searched_at: ISO timestamp of the search
            results_count: Number of results found
            downloaded_count: Number of files downloaded

        Returns:
            ID of the inserted record, or None if insert failed
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO search_history
                (dork, searched_at, results_count, downloaded_count)
                VALUES (?, ?, ?, ?)
            """, (dork, searched_at, results_count, downloaded_count))
            
            self.connection.commit()
            return cursor.lastrowid
            
        except Exception as error:
            print(highlight(
                f"[!] Error recording search: {error}",
                Fore.RED
            ))
            return None

    def record_downloaded_file(
        self,
        dork: str,
        repository: str,
        file_path: str,
        local_path: Optional[str] = None,
        item_url: Optional[str] = None,
        searched_at: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> Optional[int]:
        """
        Record a downloaded file in the database.

        Args:
            dork: The search query that found this file
            repository: Full repository name
            file_path: Path of the file in the repository
            local_path: Local filesystem path where file was saved
            item_url: URL to the file on GitHub
            searched_at: ISO timestamp of the search
            file_size: Size of the file in bytes

        Returns:
            ID of the inserted record, or None if insert failed
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO downloaded_files
                (dork, repository, file_path, local_path, item_url,
                 searched_at, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                dork, repository, file_path, local_path,
                item_url, searched_at, file_size
            ))
            
            self.connection.commit()
            return cursor.lastrowid
            
        except Exception as error:
            print(highlight(
                f"[!] Error recording downloaded file: {error}",
                Fore.RED
            ))
            return None

    def record_finding(
        self,
        file_id: int,
        label: str,
        matched_text: str,
        context: str,
        line_number: Optional[int],
        severity: str
    ) -> Optional[int]:
        """
        Record a pattern finding in the database.

        Args:
            file_id: ID of the file where finding was discovered
            label: Label/pattern name of the finding
            matched_text: The matched text
            context: Surrounding context
            line_number: Line number where match was found
            severity: Severity level (HIGH, MEDIUM, LOW)

        Returns:
            ID of the inserted record, or None if insert failed
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO findings
                (file_id, label, matched_text, context, line_number, severity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_id, label, matched_text, context, line_number, severity))
            
            self.connection.commit()
            return cursor.lastrowid
            
        except Exception as error:
            print(highlight(
                f"[!] Error recording finding: {error}",
                Fore.RED
            ))
            return None

    def get_search_history(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve search history from the database.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of search history records as dictionaries
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM search_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as error:
            print(highlight(
                f"[!] Error retrieving search history: {error}",
                Fore.RED
            ))
            return []

    def get_downloaded_files(
        self,
        dork: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Retrieve downloaded files from the database.

        Args:
            dork: Optional dork filter
            limit: Maximum number of records to return

        Returns:
            List of downloaded file records as dictionaries
        """
        try:
            cursor = self.connection.cursor()
            
            if dork:
                cursor.execute("""
                    SELECT * FROM downloaded_files
                    WHERE dork = ?
                    ORDER BY downloaded_at DESC
                    LIMIT ?
                """, (dork, limit))
            else:
                cursor.execute("""
                    SELECT * FROM downloaded_files
                    ORDER BY downloaded_at DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as error:
            print(highlight(
                f"[!] Error retrieving downloaded files: {error}",
                Fore.RED
            ))
            return []

    def get_findings_by_severity(
        self,
        severity: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve findings filtered by severity level.

        Args:
            severity: Severity level (HIGH, MEDIUM, LOW)
            limit: Maximum number of records to return

        Returns:
            List of finding records as dictionaries
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT f.*, df.repository, df.file_path, df.local_path
                FROM findings f
                JOIN downloaded_files df ON f.file_id = df.id
                WHERE f.severity = ?
                ORDER BY f.found_at DESC
                LIMIT ?
            """, (severity, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as error:
            print(highlight(
                f"[!] Error retrieving findings: {error}",
                Fore.RED
            ))
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary containing various statistics
        """
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM search_history")
            total_searches = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM downloaded_files")
            total_files = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM findings")
            total_findings = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT severity, COUNT(*) as count
                FROM findings
                GROUP BY severity
            """)
            severity_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                "total_searches": total_searches,
                "total_downloaded_files": total_files,
                "total_findings": total_findings,
                "severity_distribution": severity_counts
            }
            
        except Exception as error:
            print(highlight(
                f"[!] Error retrieving statistics: {error}",
                Fore.RED
            ))
            return {}

    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            print(highlight(
                "[i] Database connection closed",
                Fore.BLUE
            ))

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
