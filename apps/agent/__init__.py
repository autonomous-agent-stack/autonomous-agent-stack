"""
Agent application package.

This package contains the business surface for the dedicated sub-agent
product with yt-dlp capabilities and Linux/Mac failover support.
"""

from .lead_capture import LeadCaptureService, Lead, create_lead_from_request

__all__ = ['LeadCaptureService', 'Lead', 'create_lead_from_request']
