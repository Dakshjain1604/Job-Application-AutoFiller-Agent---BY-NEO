"""
Database schemas and setup for AutoCareer application.
All data stored locally for privacy and security.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import os


class Database:
    """Local SQLite database manager for AutoCareer."""
    
    def __init__(self, db_path: str = "./backend/data/autocareer.db"):
        """Initialize database connection and create tables."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create all required database tables."""
        
        # User Profile table - stores resume data and embeddings metadata
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                resume_text TEXT NOT NULL,
                skills TEXT,
                experience TEXT,
                education TEXT,
                links TEXT,
                vector_db_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Jobs table - stores scraped job postings
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                description TEXT,
                requirements TEXT,
                url TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                fit_score REAL,
                fit_rationale TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analyzed_at TIMESTAMP,
                status TEXT DEFAULT 'discovered'
            )
        """)
        
        # Application Drafts table - stores generated cover letters
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                cover_letter TEXT,
                custom_answers TEXT,
                company_context TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                edited_at TIMESTAMP,
                status TEXT DEFAULT 'draft',
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (profile_id) REFERENCES profiles(id)
            )
        """)
        
        # Application Logs table - immutable audit trail
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                draft_id INTEGER,
                job_url TEXT NOT NULL,
                company TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                draft_content TEXT,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (profile_id) REFERENCES profiles(id),
                FOREIGN KEY (draft_id) REFERENCES drafts(id)
            )
        """)
        
        # Credentials table - encrypted local storage for LinkedIn/Greenhouse
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT UNIQUE NOT NULL,
                username TEXT,
                encrypted_password TEXT,
                cookies TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Application Queue table - tracks submission queue
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                draft_id INTEGER NOT NULL,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                scheduled_at TIMESTAMP,
                submitted_at TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (profile_id) REFERENCES profiles(id),
                FOREIGN KEY (draft_id) REFERENCES drafts(id)
            )
        """)
        
        self.conn.commit()
    
    # Profile operations
    def insert_profile(self, name: str, email: str, resume_text: str, 
                      skills: str = None, experience: str = None, 
                      education: str = None, links: str = None,
                      vector_db_id: str = None) -> int:
        """Insert or update user profile."""
        self.cursor.execute("""
            INSERT INTO profiles (name, email, resume_text, skills, experience, education, links, vector_db_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, resume_text, skills, experience, education, links, vector_db_id))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_profile(self, profile_id: int = 1) -> Optional[Dict]:
        """Retrieve profile by ID."""
        self.cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    # Job operations
    def insert_job(self, title: str, company: str, url: str, source: str,
                   location: str = None, salary_min: int = None, 
                   salary_max: int = None, description: str = None,
                   requirements: str = None) -> int:
        """Insert scraped job posting."""
        try:
            self.cursor.execute("""
                INSERT INTO jobs (title, company, location, salary_min, salary_max, 
                                description, requirements, url, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, company, location, salary_min, salary_max, 
                  description, requirements, url, source))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Job URL already exists
            self.cursor.execute("SELECT id FROM jobs WHERE url = ?", (url,))
            return self.cursor.fetchone()[0]
    
    def update_job_analysis(self, job_id: int, fit_score: float, 
                           fit_rationale: str, status: str = 'analyzed'):
        """Update job with fit score and analysis."""
        self.cursor.execute("""
            UPDATE jobs 
            SET fit_score = ?, fit_rationale = ?, status = ?, analyzed_at = ?
            WHERE id = ?
        """, (fit_score, fit_rationale, status, datetime.now(), job_id))
        self.conn.commit()
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        """Retrieve job by ID."""
        self.cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_jobs(self, status: str = None, limit: int = 50) -> List[Dict]:
        """Retrieve jobs with optional status filter."""
        if status:
            self.cursor.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY fit_score DESC, scraped_at DESC LIMIT ?",
                (status, limit)
            )
        else:
            self.cursor.execute(
                "SELECT * FROM jobs ORDER BY fit_score DESC, scraped_at DESC LIMIT ?",
                (limit,)
            )
        return [dict(row) for row in self.cursor.fetchall()]
    
    # Draft operations
    def insert_draft(self, job_id: int, profile_id: int, cover_letter: str,
                    custom_answers: str = None, company_context: str = None) -> int:
        """Insert generated application draft."""
        self.cursor.execute("""
            INSERT INTO drafts (job_id, profile_id, cover_letter, custom_answers, company_context)
            VALUES (?, ?, ?, ?, ?)
        """, (job_id, profile_id, cover_letter, custom_answers, company_context))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_draft(self, draft_id: int, cover_letter: str = None, 
                    custom_answers: str = None, status: str = None):
        """Update draft content or status."""
        updates = []
        values = []
        if cover_letter:
            updates.append("cover_letter = ?")
            values.append(cover_letter)
        if custom_answers:
            updates.append("custom_answers = ?")
            values.append(custom_answers)
        if status:
            updates.append("status = ?")
            values.append(status)
        
        if updates:
            updates.append("edited_at = ?")
            values.append(datetime.now())
            values.append(draft_id)
            
            query = f"UPDATE drafts SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, values)
            self.conn.commit()
    
    def get_draft(self, draft_id: int) -> Optional[Dict]:
        """Retrieve draft by ID."""
        self.cursor.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_draft_by_job(self, job_id: int) -> Optional[Dict]:
        """Retrieve draft by job ID."""
        self.cursor.execute(
            "SELECT * FROM drafts WHERE job_id = ? ORDER BY generated_at DESC LIMIT 1",
            (job_id,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    # Application log operations (immutable)
    def log_application(self, job_id: int, profile_id: int, job_url: str,
                       company: str, action: str, status: str,
                       draft_id: int = None, draft_content: str = None,
                       error_message: str = None) -> int:
        """Log application action (immutable audit trail)."""
        self.cursor.execute("""
            INSERT INTO application_logs 
            (job_id, profile_id, draft_id, job_url, company, action, status, draft_content, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, profile_id, draft_id, job_url, company, action, status, draft_content, error_message))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_application_logs(self, limit: int = 100) -> List[Dict]:
        """Retrieve application logs."""
        self.cursor.execute(
            "SELECT * FROM application_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in self.cursor.fetchall()]
    
    # Queue operations
    def add_to_queue(self, job_id: int, profile_id: int, draft_id: int,
                    priority: int = 0) -> int:
        """Add application to submission queue."""
        self.cursor.execute("""
            INSERT INTO queue (job_id, profile_id, draft_id, priority)
            VALUES (?, ?, ?, ?)
        """, (job_id, profile_id, draft_id, priority))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_queue(self, status: str = 'pending') -> List[Dict]:
        """Retrieve queue items."""
        self.cursor.execute("""
            SELECT q.*, j.title, j.company, j.url, d.cover_letter
            FROM queue q
            JOIN jobs j ON q.job_id = j.id
            JOIN drafts d ON q.draft_id = d.id
            WHERE q.status = ?
            ORDER BY q.priority DESC, q.id ASC
        """, (status,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def update_queue_status(self, queue_id: int, status: str):
        """Update queue item status."""
        timestamp_field = "submitted_at" if status == "submitted" else None
        if timestamp_field:
            self.cursor.execute(
                f"UPDATE queue SET status = ?, {timestamp_field} = ? WHERE id = ?",
                (status, datetime.now(), queue_id)
            )
        else:
            self.cursor.execute(
                "UPDATE queue SET status = ? WHERE id = ?",
                (status, queue_id)
            )
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()


# Singleton instance
_db_instance = None

def get_db() -> Database:
    """Get database singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
