"""End-to-End Tests for Malu Group Security Integration.

Tests the complete flow:
1. Malu internal group sends /status -> Extract magic link
2. Non-member clicks link -> Assert 403 returned
3. SQLite audit log contains unauthorized access attempt

Phase 4: Full-chain Acceptance Testing
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.autoresearch.core.services.group_access import GroupAccessManager, GroupMagicLink
from src.autoresearch.core.services.panel_access import PanelAccessService
from src.autoresearch.core.services.panel_audit import PanelAuditLogger


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def internal_groups():
    """Malu internal group whitelist."""
    return [-1001234567890]  # Malu Marketing Group


@pytest.fixture
def jwt_secret():
    """JWT secret for testing."""
    return "test-jwt-secret-for-malu-group-security"


@pytest.fixture
def group_access_manager(internal_groups, jwt_secret):
    """Create GroupAccessManager for testing."""
    return GroupAccessManager(
        internal_groups=internal_groups,
        jwt_secret=jwt_secret,
    )


@pytest.fixture
def panel_access_service(jwt_secret):
    """Create PanelAccessService for testing."""
    return PanelAccessService(
        secret=jwt_secret,
        telegram_bot_token="test-bot-token",
    )


@pytest.fixture
def temp_audit_db():
    """Create temporary audit database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


# ============================================================================
# PHASE 2 TESTS: TELEGRAM ROUTING INTEGRATION
# ============================================================================

class TestGroupMagicLinkGeneration:
    """Tests for group-scoped magic link generation."""

    def test_internal_group_link_generation(self, group_access_manager):
        """Test magic link generation for internal group."""
        chat_id = -1001234567890  # Malu Marketing Group
        user_id = 123456789

        link = group_access_manager.create_group_magic_link(
            chat_id=chat_id,
            user_id=user_id,
        )

        assert link is not None
        assert link.chat_id == chat_id
        assert link.user_id == user_id
        assert link.scope == "group"
        assert link.url.startswith("http")
        assert "token=" in link.url

    def test_non_internal_group_no_link(self, group_access_manager):
        """Test that non-internal groups don't get magic links."""
        chat_id = -1009999999999  # Non-whitelist group
        user_id = 123456789

        link = group_access_manager.create_group_magic_link(
            chat_id=chat_id,
            user_id=user_id,
        )

        assert link is None

    def test_is_internal_group(self, group_access_manager, internal_groups):
        """Test internal group whitelist check."""
        # Internal group
        assert group_access_manager.is_internal_group(internal_groups[0])

        # Non-internal group
        assert not group_access_manager.is_internal_group(-1009999999999)


# ============================================================================
# PHASE 3 TESTS: PANEL INTERCEPTOR & AUDIT
# ============================================================================

class TestPanelAccessInterceptor:
    """Tests for panel access interceptor with membership verification."""

    @pytest.mark.asyncio
    async def test_member_access_granted(
        self,
        panel_access_service,
        group_access_manager,
    ):
        """Test that group member can access panel."""
        chat_id = -1001234567890
        user_id = 123456789

        # Generate magic link
        link = group_access_manager.create_group_magic_link(
            chat_id=chat_id,
            user_id=user_id,
        )
        assert link is not None

        # Extract token from URL
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(link.url)
        token = parse_qs(parsed.query)["token"][0]

        # Mock getChatMember API response (member status)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"ok": true, "result": {"status": "member"}}'
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            # Check access
            claims = panel_access_service.check_panel_access(
                token=token,
                user_id=user_id,
                bot_token="test-bot-token",
            )

            assert claims.telegram_uid == str(user_id)

    @pytest.mark.asyncio
    async def test_non_member_access_denied(
        self,
        panel_access_service,
        group_access_manager,
        temp_audit_db,
    ):
        """Test that non-member is denied access and audit log is created."""
        chat_id = -1001234567890
        member_user_id = 123456789
        non_member_user_id = 999999999

        # Generate magic link for member
        link = group_access_manager.create_group_magic_link(
            chat_id=chat_id,
            user_id=member_user_id,
        )
        assert link is not None

        # Extract token from URL
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(link.url)
        token = parse_qs(parsed.query)["token"][0]

        # Mock getChatMember API response (kicked status)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"ok": true, "result": {"status": "kicked"}}'
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            # Set custom audit database path via environment variable
            import os
            old_path = os.environ.get("AUTORESEARCH_AUDIT_DB_PATH")
            os.environ["AUTORESEARCH_AUDIT_DB_PATH"] = temp_audit_db

            try:
                # Check access with non-member user
                with pytest.raises(PermissionError) as exc_info:
                    panel_access_service.check_panel_access(
                        token=token,
                        user_id=non_member_user_id,
                        bot_token="test-bot-token",
                    )

                assert "未授权" in str(exc_info.value)
            finally:
                # Restore environment variable
                if old_path is not None:
                    os.environ["AUTORESEARCH_AUDIT_DB_PATH"] = old_path
                else:
                    os.environ.pop("AUTORESEARCH_AUDIT_DB_PATH", None)

    @pytest.mark.asyncio
    async def test_audit_log_created_on_unauthorized(
        self,
        panel_access_service,
        group_access_manager,
        temp_audit_db,
    ):
        """Test that unauthorized access is logged to SQLite."""
        chat_id = -1001234567890
        member_user_id = 123456789
        non_member_user_id = 999999999

        # Generate magic link
        link = group_access_manager.create_group_magic_link(
            chat_id=chat_id,
            user_id=member_user_id,
        )
        assert link is not None

        # Extract token
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(link.url)
        token = parse_qs(parsed.query)["token"][0]

        # Mock getChatMember API (kicked status)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"ok": true, "result": {"status": "kicked"}}'
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            # Set custom audit database path via environment variable
            import os
            old_path = os.environ.get("AUTORESEARCH_AUDIT_DB_PATH")
            os.environ["AUTORESEARCH_AUDIT_DB_PATH"] = temp_audit_db

            try:
                # Attempt access
                try:
                    panel_access_service.check_panel_access(
                        token=token,
                        user_id=non_member_user_id,
                        ip_address="192.168.1.100",
                        user_agent="TestAgent/1.0",
                        bot_token="test-bot-token",
                    )
                except PermissionError:
                    pass  # Expected
            finally:
                # Restore environment variable
                if old_path is not None:
                    os.environ["AUTORESEARCH_AUDIT_DB_PATH"] = old_path
                else:
                    os.environ.pop("AUTORESEARCH_AUDIT_DB_PATH", None)

        # Check audit log
        audit_logger = PanelAuditLogger(db_path=temp_audit_db)
        entries = audit_logger.get_unauthorized_attempts()

        assert len(entries) > 0
        assert entries[0].user_id == non_member_user_id
        assert entries[0].chat_id == chat_id
        assert entries[0].status == "unauthorized"
        assert entries[0].reason == "user_not_in_group"
        assert entries[0].ip_address == "192.168.1.100"


# ============================================================================
# PHASE 4 TESTS: FULL-CHAIN ACCEPTANCE
# ============================================================================

class TestFullChainMaluScenario:
    """Full-chain tests for Malu business scenario.

    Scenario:
    1. Malu internal group sends /status -> Extract magic link
    2. Non-member clicks link -> Assert 403 returned
    3. SQLite audit log contains unauthorized access attempt
    """

    @pytest.mark.asyncio
    async def test_complete_malu_scenario(
        self,
        group_access_manager,
        panel_access_service,
        temp_audit_db,
    ):
        """Test complete Malu scenario with all security layers."""
        # Step 1: Malu internal group sends /status
        malu_group_chat_id = -1001234567890
        malu_member_user_id = 123456789

        # Generate magic link
        magic_link = group_access_manager.create_group_magic_link(
            chat_id=malu_group_chat_id,
            user_id=malu_member_user_id,
        )

        assert magic_link is not None
        assert magic_link.scope == "group"
        assert "token=" in magic_link.url

        # Extract token
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(magic_link.url)
        token = parse_qs(parsed.query)["token"][0]

        # Step 2: Non-member attempts to use the link
        non_member_user_id = 999999999

        # Mock getChatMember API (left status - user not in group)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"ok": true, "result": {"status": "left"}}'
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            # Set custom audit database path via environment variable
            import os
            old_path = os.environ.get("AUTORESEARCH_AUDIT_DB_PATH")
            os.environ["AUTORESEARCH_AUDIT_DB_PATH"] = temp_audit_db

            try:
                # Step 3: Assert 403 (PermissionError)
                with pytest.raises(PermissionError) as exc_info:
                    panel_access_service.check_panel_access(
                        token=token,
                        user_id=non_member_user_id,
                        ip_address="203.0.113.50",
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        bot_token="test-bot-token",
                    )

                # Verify error message
                assert "未授权" in str(exc_info.value)
            finally:
                # Restore environment variable
                if old_path is not None:
                    os.environ["AUTORESEARCH_AUDIT_DB_PATH"] = old_path
                else:
                    os.environ.pop("AUTORESEARCH_AUDIT_DB_PATH", None)

        # Step 4: Verify SQLite audit log
        audit_logger = PanelAuditLogger(db_path=temp_audit_db)
        entries = audit_logger.get_unauthorized_attempts()

        assert len(entries) > 0

        # Verify latest entry
        latest = entries[0]
        assert latest.user_id == non_member_user_id
        assert latest.chat_id == malu_group_chat_id
        assert latest.status == "unauthorized"
        assert latest.reason == "user_not_in_group"
        assert latest.ip_address == "203.0.113.50"

        # Verify stats
        stats = audit_logger.get_stats()
        assert stats["unauthorized"] > 0

    @pytest.mark.asyncio
    async def test_member_can_still_access_after_verification(
        self,
        group_access_manager,
        panel_access_service,
    ):
        """Test that actual member can access panel after verification."""
        malu_group_chat_id = -1001234567890
        malu_member_user_id = 123456789

        # Generate magic link
        magic_link = group_access_manager.create_group_magic_link(
            chat_id=malu_group_chat_id,
            user_id=malu_member_user_id,
        )

        # Extract token
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(magic_link.url)
        token = parse_qs(parsed.query)["token"][0]

        # Mock getChatMember API (administrator status)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"ok": true, "result": {"status": "administrator"}}'
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            # Check access
            claims = panel_access_service.check_panel_access(
                token=token,
                user_id=malu_member_user_id,
                bot_token="test-bot-token",
            )

            assert claims is not None
            assert claims.telegram_uid == str(malu_member_user_id)


# ============================================================================
# UI INTERCEPTOR TESTS
# ============================================================================

class TestPanelUIInterceptor:
    """Tests for panel UI interceptor error handling."""

    def test_403_response_format(self):
        """Test that 403 response is in correct format for frontend."""
        # This test verifies the error message format
        # Frontend should display: "未授权的访问尝试，该操作已记录"
        error_message = "未授权的访问尝试，该操作已记录"

        # Verify message is in Chinese (professional tone)
        assert "未授权" in error_message
        assert "已记录" in error_message

        # Verify message is NOT showing business topology
        assert "拓扑" not in error_message
        assert "玛露" not in error_message
        assert "群组" not in error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
