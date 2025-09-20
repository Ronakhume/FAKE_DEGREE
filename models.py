import os
import sqlite3
import hashlib
import datetime
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path="database/certificates.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database with required tables"""
        # Ensure database directory exists
        Path(os.path.dirname(self.db_path)).mkdir(parents=True, exist_ok=True)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create certificates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                certificate_id TEXT UNIQUE NOT NULL,
                student_name TEXT NOT NULL,
                roll_number TEXT NOT NULL,
                marks TEXT,
                institution TEXT,
                course TEXT,
                issue_date TEXT,
                file_hash TEXT UNIQUE,
                file_path TEXT,
                is_verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create users table for admin access
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create fraud_reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fraud_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                certificate_id TEXT,
                fraud_type TEXT NOT NULL,
                confidence_score REAL,
                description TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (certificate_id) REFERENCES certificates (certificate_id)
            )
        ''')
        
        # Create verification_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                certificate_id TEXT,
                action TEXT NOT NULL,
                result TEXT,
                performed_by TEXT,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (certificate_id) REFERENCES certificates (certificate_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_certificate(self, cert_data):
        """Add a new certificate to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO certificates 
                (certificate_id, student_name, roll_number, marks, institution, course, issue_date, file_hash, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cert_data['certificate_id'],
                cert_data['student_name'],
                cert_data['roll_number'],
                cert_data.get('marks', ''),
                cert_data.get('institution', ''),
                cert_data.get('course', ''),
                cert_data.get('issue_date', ''),
                cert_data['file_hash'],
                cert_data['file_path']
            ))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            return None
        finally:
            conn.close()
    
    def get_certificate(self, certificate_id):
        """Get certificate by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM certificates WHERE certificate_id = ?
        ''', (certificate_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, result))
        return None
    
    def check_duplicate_hash(self, file_hash):
        """Check if a file with the same hash already exists"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT certificate_id FROM certificates WHERE file_hash = ?
        ''', (file_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def add_fraud_report(self, certificate_id, fraud_type, confidence_score, description):
        """Add a fraud detection report"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fraud_reports (certificate_id, fraud_type, confidence_score, description)
            VALUES (?, ?, ?, ?)
        ''', (certificate_id, fraud_type, confidence_score, description))
        
        conn.commit()
        conn.close()
        return cursor.lastrowid
    
    def get_all_certificates(self):
        """Get all certificates for admin dashboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.*, 
                   COUNT(f.id) as fraud_reports_count,
                   MAX(f.confidence_score) as max_fraud_score
            FROM certificates c
            LEFT JOIN fraud_reports f ON c.certificate_id = f.certificate_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in results]
    
    def get_fraud_reports(self, certificate_id=None):
        """Get fraud reports, optionally filtered by certificate ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if certificate_id:
            cursor.execute('''
                SELECT * FROM fraud_reports WHERE certificate_id = ?
                ORDER BY detected_at DESC
            ''', (certificate_id,))
        else:
            cursor.execute('''
                SELECT f.*, c.student_name, c.roll_number
                FROM fraud_reports f
                LEFT JOIN certificates c ON f.certificate_id = c.certificate_id
                ORDER BY f.detected_at DESC
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in results]

# Initialize database manager
db_manager = DatabaseManager()