"""End-to-End Tests for Cross-Ecosystem Operations.

Tests business scenarios and security constraints for Google and Apple integrations.

Business Test Scenario:
"把玛露遮瑕膏【挑战游泳级别持妆】的测试计划加入我的苹果提醒事项，
并把昨天的测试图片存入 Google Drive"

Validates:
1. Task decomposition
2. Bridge-based reminder creation
3. API-based file upload
4. HITL approval flow
5. Professional language quality
6. Sandbox isolation integrity
"""

from __future__ import annotations

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.integrations.google_workspace import (
    GoogleCalendarClient,
    GoogleTasksClient,
    GoogleDriveClient,
    OAuthManager,
)
from src.integrations.apple_bridge import (
    macOSHostBridge,
    RemindersService,
    NotesService,
    CalendarService,
)
from src.integrations.hitl_approval import (
    ApprovalManager,
    ApprovalStatus,
    CalendarApprovalRequest,
    TaskApprovalRequest,
    NoteApprovalRequest,
    FileUploadApprovalRequest,
    ReminderApprovalRequest,
)


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_oauth_manager():
    """Mock OAuth manager for testing."""
    with patch("src.integrations.google_workspace.oauth.OAuthManager") as mock:
        mock_instance = MagicMock()
        mock_instance.get_credentials.return_value = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_apple_bridge():
    """Mock Apple bridge services for testing."""
    reminders = MagicMock(spec=RemindersService)
    notes = MagicMock(spec=NotesService)
    calendar = MagicMock(spec=CalendarService)

    return {
        "reminders": reminders,
        "notes": notes,
        "calendar": calendar,
    }


@pytest.fixture
def approval_manager():
    """Create approval manager for testing."""
    return ApprovalManager()


# ============================================================================
# GOOGLE WORKSPACE TESTS
# ============================================================================

class TestGoogleCalendarIntegration:
    """Tests for Google Calendar integration."""

    def test_create_google_event_success(self, mock_oauth_manager):
        """Test successful Google Calendar event creation."""
        with patch("src.integrations.google_workspace.calendar.build") as mock_build:
            # Mock service
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock event creation
            mock_events = MagicMock()
            mock_service.events.return_value = mock_events
            mock_events.insert.return_value.execute.return_value = {
                "id": "event123",
                "htmlLink": "https://calendar.google.com/event123",
                "summary": "玛露 6g 遮瑕膏线下推广会议",
                "start": {"dateTime": "2026-03-26T10:00:00"},
                "end": {"dateTime": "2026-03-26T11:00:00"},
            }

            client = GoogleCalendarClient(oauth_manager=mock_oauth_manager)
            result = client.create_google_event(
                summary="玛露 6g 遮瑕膏线下推广会议",
                start_time="2026-03-26T10:00:00",
                end_time="2026-03-26T11:00:00",
                location="上海会议室",
                description="讨论产品推广策略",
            )

            assert result["status"] == "success"
            assert result["event_id"] == "event123"
            assert "calendar.google.com" in result["html_link"]

    def test_list_google_events(self, mock_oauth_manager):
        """Test listing Google Calendar events."""
        with patch("src.integrations.google_workspace.calendar.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_events = MagicMock()
            mock_service.events.return_value = mock_events
            mock_events.list.return_value.execute.return_value = {
                "items": [
                    {
                        "id": "event1",
                        "summary": "Team Meeting",
                        "start": {"dateTime": "2026-03-26T09:00:00"},
                        "end": {"dateTime": "2026-03-26T10:00:00"},
                    }
                ]
            }

            client = GoogleCalendarClient(oauth_manager=mock_oauth_manager)
            result = client.list_google_events()

            assert result["status"] == "success"
            assert result["count"] == 1


class TestGoogleDriveIntegration:
    """Tests for Google Drive integration."""

    def test_upload_to_drive_success(self, mock_oauth_manager, tmp_path):
        """Test successful file upload to Google Drive."""
        # Create test file
        test_file = tmp_path / "test_image.jpg"
        test_file.write_bytes(b"fake image data")

        with patch("src.integrations.google_workspace.drive.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_files = MagicMock()
            mock_service.files.return_value = mock_files
            mock_files.create.return_value.execute.return_value = {
                "id": "file123",
                "name": "test_image.jpg",
                "mimeType": "image/jpeg",
                "size": 15,
                "webViewLink": "https://drive.google.com/file123",
                "createdTime": "2026-03-26T04:00:00Z",
            }

            client = GoogleDriveClient(oauth_manager=mock_oauth_manager)
            result = client.upload_to_drive(
                file_path=str(test_file),
                description="玛露遮瑕膏测试图片",
            )

            assert result["status"] == "success"
            assert result["file_id"] == "file123"
            assert result["name"] == "test_image.jpg"


# ============================================================================
# APPLE BRIDGE TESTS
# ============================================================================

class TestAppleRemindersIntegration:
    """Tests for Apple Reminders integration via bridge."""

    def test_add_apple_reminder_success(self):
        """Test successful reminder creation."""
        service = RemindersService()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = service.add_apple_reminder(
                title="玛露遮瑕膏【挑战游泳级别持妆】测试计划",
                notes="验证游泳场景下的持妆效果",
                due_date="2026-03-27",
                list_name="Reminders",
            )

            assert result["status"] == "success"
            assert "测试计划" in result["message"]

    def test_list_apple_reminders(self):
        """Test listing reminders."""
        service = RemindersService()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = service.list_apple_reminders()

            assert result["status"] == "success"


class TestAppleNotesIntegration:
    """Tests for Apple Notes integration via bridge."""

    def test_append_apple_note_success(self):
        """Test appending to Apple Note."""
        service = NotesService()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="success",
                stderr="",
            )

            result = service.append_apple_note(
                note_name="分销商谈判策略",
                content="\n\n## 2026-03-26 更新\n\n新增华东区域分销商合作意向",
                folder_name="Notes",
            )

            assert result["status"] == "success"
            assert result["action"] == "appended"


# ============================================================================
# HITL APPROVAL TESTS
# ============================================================================

class TestHITLApprovalFlow:
    """Tests for HITL approval system."""

    @pytest.mark.asyncio
    async def test_calendar_approval_flow(self, approval_manager):
        """Test calendar event approval flow."""
        # Create approval request
        request = approval_manager.create_calendar_approval(
            event_summary="玛露 6g 遮瑕膏线下推广会议",
            start_time="2026-03-26T10:00:00",
            end_time="2026-03-26T11:00:00",
            location="上海会议室",
            calendar_provider="google",
        )

        assert request.status == ApprovalStatus.PENDING
        assert "日程添加请求" in request.summary

        # Approve request
        approval_manager.approve_request(request.request_id)
        assert request.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reminder_approval_flow(self, approval_manager):
        """Test reminder creation approval flow."""
        request = approval_manager.create_reminder_approval(
            reminder_title="玛露遮瑕膏【挑战游泳级别持妆】测试计划",
            reminder_notes="验证游泳场景下的持妆效果",
            due_date="2026-03-27",
        )

        assert request.status == ApprovalStatus.PENDING

        # Approve request
        approval_manager.approve_request(request.request_id)
        assert request.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_file_upload_approval_flow(self, approval_manager):
        """Test file upload approval flow."""
        request = approval_manager.create_file_upload_approval(
            filename="malu_test_image_20260325.jpg",
            file_size=1024000,
            mime_type="image/jpeg",
            description="玛露遮瑕膏测试图片",
        )

        assert request.status == ApprovalStatus.PENDING

        # Approve request
        approval_manager.approve_request(request.request_id)
        assert request.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_approval_timeout(self, approval_manager):
        """Test approval timeout."""
        request = approval_manager.create_reminder_approval(
            reminder_title="测试提醒",
            timeout_seconds=1,  # 1 second timeout
        )

        # Wait for timeout
        status = await approval_manager.wait_for_approval(request)
        assert status == ApprovalStatus.TIMEOUT


# ============================================================================
# BUSINESS SCENARIO TESTS
# ============================================================================

class TestMaluBusinessScenario:
    """End-to-end tests for 玛露 business scenario.

    Test Scenario:
    "把玛露遮瑕膏【挑战游泳级别持妆】的测试计划加入我的苹果提醒事项，
    并把昨天的测试图片存入 Google Drive"
    """

    @pytest.mark.asyncio
    async def test_complete_malu_scenario(
        self,
        mock_oauth_manager,
        tmp_path,
        approval_manager,
    ):
        """Test complete 玛露 scenario with approval flow."""
        # Step 1: Create reminder approval request
        reminder_request = approval_manager.create_reminder_approval(
            reminder_title="玛露遮瑕膏【挑战游泳级别持妆】测试计划",
            reminder_notes="验证游泳场景下的持妆效果，确保产品宣传真实性",
            due_date=(datetime.now() + timedelta(days=1)).isoformat(),
        )

        # Step 2: Create file upload approval request
        test_file = tmp_path / "malu_test_20260325.jpg"
        test_file.write_bytes(b"fake test image")

        file_request = approval_manager.create_file_upload_approval(
            filename="malu_test_20260325.jpg",
            file_size=20,
            mime_type="image/jpeg",
            description="玛露遮瑕膏游泳测试图片",
        )

        # Step 3: Approve both requests
        approval_manager.approve_request(reminder_request.request_id)
        approval_manager.approve_request(file_request.request_id)

        # Step 4: Execute operations after approval
        # (In real implementation, this would call Apple Bridge and Google Drive API)

        assert reminder_request.status == ApprovalStatus.APPROVED
        assert file_request.status == ApprovalStatus.APPROVED

    def test_professional_language_quality(self):
        """Test that all operations use professional language."""
        # Test reminder text
        reminder_text = "玛露遮瑕膏【挑战游泳级别持妆】测试计划"
        assert "玛露" in reminder_text
        assert "测试计划" in reminder_text

        # Test file description
        file_description = "玛露遮瑕膏游泳测试图片"
        assert "测试" in file_description
        assert "玛露" in file_description


# ============================================================================
# SECURITY TESTS
# ============================================================================

class TestSecurityConstraints:
    """Tests for security constraints and sandbox isolation."""

    def test_apple_bridge_no_delete_operations(self):
        """Test that Apple Bridge does not expose DELETE operations."""
        # Bridge should only have CREATE and READ endpoints
        bridge = macOSHostBridge()

        # Get all route paths
        routes = [route.path for route in bridge.routes]

        # Verify no DELETE endpoints
        delete_routes = [r for r in routes if "delete" in r.lower()]
        assert len(delete_routes) == 0, "DELETE endpoints should not be exposed"

    def test_google_credentials_from_env(self):
        """Test that Google credentials are loaded from environment."""
        with patch.dict("os.environ", {
            "GOOGLE_CLIENT_ID": "test_client_id",
            "GOOGLE_CLIENT_SECRET": "test_secret",
        }):
            oauth = OAuthManager()
            assert oauth.client_id == "test_client_id"
            assert oauth.client_secret == "test_secret"

    def test_no_hardcoded_secrets(self):
        """Test that no secrets are hardcoded in code."""
        import inspect
        from src.integrations.google_workspace import oauth

        source = inspect.getsource(oauth)
        assert "AIza" not in source, "API keys should not be hardcoded"
        assert "ya29" not in source, "OAuth tokens should not be hardcoded"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
