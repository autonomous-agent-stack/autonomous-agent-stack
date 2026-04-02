"""
Tests for agent landing page backend functionality.

This module tests the lead capture service for the dedicated yt-dlp sub-agent
product with Linux/Mac failover capability.
"""

import pytest
import tempfile
import os
from datetime import datetime

from apps.agent.lead_capture import (
    LeadCaptureService,
    Lead,
    create_lead_from_request
)


class TestLeadCaptureService:
    """Test suite for LeadCaptureService."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def service(self, temp_db):
        """Create a lead capture service with temporary database."""
        return LeadCaptureService(db_path=temp_db)
    
    def test_service_initialization(self, temp_db):
        """Test that service initializes correctly."""
        service = LeadCaptureService(db_path=temp_db)
        assert service.db_path == temp_db
        assert os.path.exists(temp_db)
    
    def test_capture_valid_lead(self, service):
        """Test capturing a valid lead."""
        lead = Lead(
            id=None,
            email='test@example.com',
            name='Test User',
            use_case='Automated video downloading',
            primary_platform='linux',
            interested_in_beta=True,
            created_at=datetime.utcnow().isoformat()
        )
        
        result = service.capture_lead(lead)
        
        assert result['success'] is True
        assert result['lead_id'] is not None
        assert result['message'] == 'Lead captured successfully'
    
    def test_capture_duplicate_email(self, service):
        """Test that duplicate emails are rejected."""
        lead = Lead(
            id=None,
            email='duplicate@example.com',
            name='First User',
            use_case='Use case 1',
            primary_platform='linux',
            interested_in_beta=True,
            created_at=datetime.utcnow().isoformat()
        )
        
        # First capture should succeed
        result1 = service.capture_lead(lead)
        assert result1['success'] is True
        
        # Second capture with same email should fail
        lead2 = Lead(
            id=None,
            email='duplicate@example.com',
            name='Second User',
            use_case='Use case 2',
            primary_platform='mac',
            interested_in_beta=False,
            created_at=datetime.utcnow().isoformat()
        )
        result2 = service.capture_lead(lead2)
        assert result2['success'] is False
        assert 'already registered' in result2['error']
    
    def test_capture_lead_invalid_email(self, service):
        """Test that invalid emails are rejected."""
        lead = Lead(
            id=None,
            email='not-an-email',
            name='Test User',
            use_case='Some use case',
            primary_platform='linux',
            interested_in_beta=True,
            created_at=datetime.utcnow().isoformat()
        )
        
        with pytest.raises(ValueError, match='Valid email'):
            service.capture_lead(lead)
    
    def test_capture_lead_missing_name(self, service):
        """Test that missing name is rejected."""
        lead = Lead(
            id=None,
            email='test@example.com',
            name='',
            use_case='Some use case',
            primary_platform='linux',
            interested_in_beta=True,
            created_at=datetime.utcnow().isoformat()
        )
        
        with pytest.raises(ValueError, match='Name is required'):
            service.capture_lead(lead)
    
    def test_capture_lead_invalid_platform(self, service):
        """Test that invalid platform is rejected."""
        lead = Lead(
            id=None,
            email='test@example.com',
            name='Test User',
            use_case='Some use case',
            primary_platform='windows',  # Invalid
            interested_in_beta=True,
            created_at=datetime.utcnow().isoformat()
        )
        
        with pytest.raises(ValueError, match='Primary platform'):
            service.capture_lead(lead)
    
    def test_get_lead(self, service):
        """Test retrieving a lead by email."""
        lead = Lead(
            id=None,
            email='retrieve@example.com',
            name='Retrieve Test',
            use_case='Testing retrieval',
            primary_platform='linux',
            interested_in_beta=True,
            created_at=datetime.utcnow().isoformat()
        )
        
        service.capture_lead(lead)
        
        retrieved = service.get_lead('retrieve@example.com')
        
        assert retrieved is not None
        assert retrieved['email'] == 'retrieve@example.com'
        assert retrieved['name'] == 'Retrieve Test'
        assert retrieved['use_case'] == 'Testing retrieval'
        assert retrieved['primary_platform'] == 'linux'
        assert retrieved['interested_in_beta'] is True
    
    def test_get_lead_not_found(self, service):
        """Test retrieving a non-existent lead."""
        retrieved = service.get_lead('nonexistent@example.com')
        assert retrieved is None
    
    def test_get_all_leads(self, service):
        """Test retrieving all leads."""
        # Create multiple leads
        for i in range(5):
            lead = Lead(
                id=None,
                email=f'user{i}@example.com',
                name=f'User {i}',
                use_case=f'Use case {i}',
                primary_platform='linux' if i % 2 == 0 else 'mac',
                interested_in_beta=(i % 2 == 0),
                created_at=datetime.utcnow().isoformat()
            )
            service.capture_lead(lead)
        
        leads = service.get_all_leads()
        
        assert len(leads) == 5
        # Should be ordered by created_at DESC
        assert leads[0]['email'] == 'user4@example.com'
    
    def test_get_all_leads_limit(self, service):
        """Test that lead retrieval respects limit."""
        # Create multiple leads
        for i in range(10):
            lead = Lead(
                id=None,
                email=f'limit{i}@example.com',
                name=f'User {i}',
                use_case=f'Use case {i}',
                primary_platform='linux',
                interested_in_beta=True,
                created_at=datetime.utcnow().isoformat()
            )
            service.capture_lead(lead)
        
        leads = service.get_all_leads(limit=3)
        assert len(leads) == 3
    
    def test_get_statistics(self, service):
        """Test retrieving lead statistics."""
        # Create leads with different platforms
        for i in range(6):
            lead = Lead(
                id=None,
                email=f'stats{i}@example.com',
                name=f'User {i}',
                use_case=f'Use case {i}',
                primary_platform='linux' if i < 4 else 'mac',
                interested_in_beta=(i % 2 == 0),
                created_at=datetime.utcnow().isoformat()
            )
            service.capture_lead(lead)
        
        stats = service.get_statistics()
        
        assert stats['total_leads'] == 6
        assert stats['platform_breakdown']['linux'] == 4
        assert stats['platform_breakdown']['mac'] == 2
        assert stats['beta_interest_count'] == 3  # i=0,2,4
    
    def test_export_leads_json(self, service):
        """Test exporting leads as JSON."""
        lead = Lead(
            id=None,
            email='export@example.com',
            name='Export Test',
            use_case='Testing export',
            primary_platform='linux',
            interested_in_beta=True,
            created_at=datetime.utcnow().isoformat()
        )
        service.capture_lead(lead)
        
        export = service.export_leads(format='json')
        
        assert 'export@example.com' in export
        assert 'Export Test' in export
        assert export.startswith('[')
    
    def test_export_leads_csv(self, service):
        """Test exporting leads as CSV."""
        lead = Lead(
            id=None,
            email='csv@example.com',
            name='CSV Test',
            use_case='Testing CSV export',
            primary_platform='mac',
            interested_in_beta=False,
            created_at=datetime.utcnow().isoformat()
        )
        service.capture_lead(lead)
        
        export = service.export_leads(format='csv')
        
        assert 'csv@example.com' in export
        assert 'CSV Test' in export
        assert 'email' in export  # Header should be present
    
    def test_export_leads_invalid_format(self, service):
        """Test that invalid export format raises error."""
        with pytest.raises(ValueError, match='Unsupported format'):
            service.export_leads(format='xml')


class TestCreateLeadFromRequest:
    """Test suite for create_lead_from_request function."""
    
    def test_create_lead_with_all_fields(self):
        """Test creating a lead with all fields."""
        request_data = {
            'email': '  REQuest@Example.COM  ',
            'name': '  Test User  ',
            'use_case': '  Automated downloads  ',
            'primary_platform': 'mac',
            'interested_in_beta': True,
            'notes': 'Some notes'
        }
        
        lead = create_lead_from_request(request_data)
        
        assert lead.email == 'request@example.com'  # Lowercased and stripped
        assert lead.name == 'Test User'
        assert lead.use_case == 'Automated downloads'
        assert lead.primary_platform == 'mac'
        assert lead.interested_in_beta is True
        assert lead.notes == 'Some notes'
        assert lead.created_at is not None
    
    def test_create_lead_with_defaults(self):
        """Test creating a lead with default values."""
        request_data = {
            'email': 'default@example.com',
            'name': 'Default User',
            'use_case': 'Default use case'
        }
        
        lead = create_lead_from_request(request_data)
        
        assert lead.primary_platform == 'linux'  # Default
        assert lead.interested_in_beta is False  # Default
        assert lead.notes is None


class TestLeadDataClass:
    """Test suite for Lead dataclass."""
    
    def test_lead_creation(self):
        """Test creating a Lead instance."""
        lead = Lead(
            id=1,
            email='test@example.com',
            name='Test User',
            use_case='Testing',
            primary_platform='linux',
            interested_in_beta=True,
            created_at='2024-01-01T00:00:00',
            notes='Test notes'
        )
        
        assert lead.id == 1
        assert lead.email == 'test@example.com'
        assert lead.name == 'Test User'
        assert lead.use_case == 'Testing'
        assert lead.primary_platform == 'linux'
        assert lead.interested_in_beta is True
        assert lead.created_at == '2024-01-01T00:00:00'
        assert lead.notes == 'Test notes'
    
    def test_lead_with_none_id(self):
        """Test that Lead can have None id."""
        lead = Lead(
            id=None,
            email='test@example.com',
            name='Test',
            use_case='Test case',
            primary_platform='linux',
            interested_in_beta=False,
            created_at=datetime.utcnow().isoformat()
        )
        
        assert lead.id is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
