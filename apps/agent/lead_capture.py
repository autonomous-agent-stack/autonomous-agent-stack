"""
Lead capture service for dedicated sub-agent landing page.

This module provides backend services for capturing leads interested in
the dedicated yt-dlp sub-agent with Linux/Mac failover capability.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Lead:
    """Represents a captured lead."""
    id: Optional[int]
    email: str
    name: str
    use_case: str
    primary_platform: str  # "linux" or "mac"
    interested_in_beta: bool
    created_at: str
    notes: Optional[str] = None


class LeadCaptureService:
    """
    Service for capturing and managing leads for the yt-dlp sub-agent product.
    
    This service provides functionality to:
    - Capture leads from the landing page
    - Store lead information in a SQLite database
    - Retrieve lead statistics
    - Export leads for follow-up
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the lead capture service.
        
        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            # Use data directory for persistence
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "agent_leads.db")
        
        self.db_path = db_path
        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                use_case TEXT NOT NULL,
                primary_platform TEXT NOT NULL,
                interested_in_beta BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def capture_lead(self, lead: Lead) -> Dict:
        """
        Capture a new lead.
        
        Args:
            lead: Lead object with capture information
            
        Returns:
            Dict with success status and lead ID or error message
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if not lead.email or '@' not in lead.email:
            raise ValueError("Valid email is required")
        if not lead.name:
            raise ValueError("Name is required")
        if not lead.use_case:
            raise ValueError("Use case is required")
        if lead.primary_platform not in ('linux', 'mac'):
            raise ValueError("Primary platform must be 'linux' or 'mac'")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO leads (email, name, use_case, primary_platform, 
                                   interested_in_beta, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                lead.email,
                lead.name,
                lead.use_case,
                lead.primary_platform,
                lead.interested_in_beta,
                lead.created_at or datetime.utcnow().isoformat(),
                lead.notes
            ))
            
            lead_id = cursor.lastrowid
            conn.commit()
            
            return {
                'success': True,
                'lead_id': lead_id,
                'message': 'Lead captured successfully'
            }
        except sqlite3.IntegrityError:
            return {
                'success': False,
                'error': 'Email already registered'
            }
        finally:
            conn.close()
    
    def get_lead(self, email: str) -> Optional[Dict]:
        """
        Retrieve a lead by email.
        
        Args:
            email: Lead email address
            
        Returns:
            Lead dict if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, name, use_case, primary_platform, 
                   interested_in_beta, created_at, notes
            FROM leads
            WHERE email = ?
        ''', (email,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'email': row[1],
                'name': row[2],
                'use_case': row[3],
                'primary_platform': row[4],
                'interested_in_beta': bool(row[5]),
                'created_at': row[6],
                'notes': row[7]
            }
        return None
    
    def get_all_leads(self, limit: int = 100) -> List[Dict]:
        """
        Retrieve all leads.
        
        Args:
            limit: Maximum number of leads to return
            
        Returns:
            List of lead dicts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, name, use_case, primary_platform, 
                   interested_in_beta, created_at, notes
            FROM leads
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'email': row[1],
                'name': row[2],
                'use_case': row[3],
                'primary_platform': row[4],
                'interested_in_beta': bool(row[5]),
                'created_at': row[6],
                'notes': row[7]
            }
            for row in rows
        ]
    
    def get_statistics(self) -> Dict:
        """
        Get lead capture statistics.
        
        Returns:
            Dict with lead statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total leads
        cursor.execute('SELECT COUNT(*) FROM leads')
        total = cursor.fetchone()[0]
        
        # Platform breakdown
        cursor.execute('''
            SELECT primary_platform, COUNT(*) 
            FROM leads 
            GROUP BY primary_platform
        ''')
        platform_stats = dict(cursor.fetchall())
        
        # Beta interest
        cursor.execute('''
            SELECT COUNT(*) FROM leads WHERE interested_in_beta = 1
        ''')
        beta_interested = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_leads': total,
            'platform_breakdown': platform_stats,
            'beta_interest_count': beta_interested
        }
    
    def export_leads(self, format: str = 'json') -> str:
        """
        Export leads for follow-up.
        
        Args:
            format: Export format ('json' or 'csv')
            
        Returns:
            String containing exported data
        """
        leads = self.get_all_leads(limit=1000)
        
        if format == 'json':
            return json.dumps(leads, indent=2)
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if leads:
                writer = csv.DictWriter(output, fieldnames=leads[0].keys())
                writer.writeheader()
                writer.writerows(leads)
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


def create_lead_from_request(request_data: Dict) -> Lead:
    """
    Create a Lead object from request data.
    
    Args:
        request_data: Dict containing lead information
        
    Returns:
        Lead object
    """
    return Lead(
        id=None,
        email=request_data.get('email', '').strip().lower(),
        name=request_data.get('name', '').strip(),
        use_case=request_data.get('use_case', '').strip(),
        primary_platform=request_data.get('primary_platform', 'linux'),
        interested_in_beta=request_data.get('interested_in_beta', False),
        created_at=datetime.utcnow().isoformat(),
        notes=request_data.get('notes')
    )
