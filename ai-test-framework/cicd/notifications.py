"""
Notification Manager

Manages test result notifications across platforms.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class NotificationConfig:
    """Configuration for notification platform."""
    platform: str  # slack, discord, teams, email
    webhook_url: Optional[str] = None
    channel: Optional[str] = None
    enabled: bool = True
    on_success: bool = True
    on_failure: bool = True
    on_regression: bool = True


class NotificationManager:
    """
    Manages test result notifications.

    Features:
    - Multi-platform support (Slack, Discord, Teams, Email)
    - Customizable triggers
    - Rich formatting
    - Attachment support
    """

    def __init__(self):
        """Initialize notification manager."""
        self.configs: Dict[str, NotificationConfig] = {}

    def add_config(self, config: NotificationConfig) -> None:
        """
        Add notification configuration.

        Args:
            config: Notification configuration
        """
        self.configs[config.platform] = config

    def send_notification(
        self,
        test_results: Dict[str, Any],
        status: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send test result notifications.

        Args:
            test_results: Test result data
            status: Test status (passed, failed, error)
            message: Custom message (optional)

        Returns:
            Notification results
        """
        results = {}

        for platform, config in self.configs.items():
            if not config.enabled:
                continue

            # Check if should send based on status
            if status == "passed" and not config.on_success:
                continue
            if status == "failed" and not config.on_failure:
                continue
            if "regression" in test_results and not config.on_regression:
                continue

            try:
                if platform == "slack":
                    results[platform] = self._send_slack(test_results, status, config, message)
                elif platform == "discord":
                    results[platform] = self._send_discord(test_results, status, config, message)
                elif platform == "teams":
                    results[platform] = self._send_teams(test_results, status, config, message)
                else:
                    results[platform] = {"status": "unsupported", "message": f"Platform {platform} not supported"}
            except Exception as e:
                results[platform] = {"status": "error", "message": str(e)}

        return results

    def _send_slack(
        self,
        test_results: Dict[str, Any],
        status: str,
        config: NotificationConfig,
        message: Optional[str]
    ) -> Dict[str, Any]:
        """Send Slack notification."""
        import requests

        # Color based on status
        colors = {
            "passed": "#36a64f",
            "failed": "#dc3545",
            "error": "#ffc107",
            "regression": "#ff5722"
        }

        # Build payload
        payload = {
            "attachments": [{
                "color": colors.get(status, "#36a64f"),
                "title": f"Test Results: {status.upper()}",
                "text": message or self._generate_summary(test_results, status),
                "fields": [
                    {
                        "title": "Total Tests",
                        "value": str(test_results.get("total", 0)),
                        "short": True
                    },
                    {
                        "title": "Passed",
                        "value": str(test_results.get("passed", 0)),
                        "short": True
                    },
                    {
                        "title": "Failed",
                        "value": str(test_results.get("failed", 0)),
                        "short": True
                    },
                    {
                        "title": "Duration",
                        "value": f"{test_results.get('duration', 0):.2f}s",
                        "short": True
                    }
                ]
            }]
        }

        # Add coverage if available
        if "coverage" in test_results:
            payload["attachments"][0]["fields"].append({
                "title": "Coverage",
                "value": f"{test_results['coverage']:.1f}%",
                "short": True
            })

        # Add performance regression if detected
        if test_results.get("has_regression"):
            payload["attachments"][0]["fields"].append({
                "title": "⚠️ Performance Regression",
                "value": "Yes",
                "short": True
            })

        response = requests.post(config.webhook_url, json=payload)
        return {"status": "sent" if response.status_code == 200 else "failed", "response": response.text}

    def _send_discord(
        self,
        test_results: Dict[str, Any],
        status: str,
        config: NotificationConfig,
        message: Optional[str]
    ) -> Dict[str, Any]:
        """Send Discord notification."""
        import requests

        # Color based on status
        colors = {
            "passed": 0x36a64f,
            "failed": 0xdc3545,
            "error": 0xffc107,
            "regression": 0xff5722
        }

        # Build payload
        payload = {
            "embeds": [{
                "title": f"Test Results: {status.upper()}",
                "description": message or self._generate_summary(test_results, status),
                "color": colors.get(status, 0x36a64f),
                "fields": [
                    {
                        "name": "Total Tests",
                        "value": str(test_results.get("total", 0)),
                        "inline": True
                    },
                    {
                        "name": "Passed",
                        "value": str(test_results.get("passed", 0)),
                        "inline": True
                    },
                    {
                        "name": "Failed",
                        "value": str(test_results.get("failed", 0)),
                        "inline": True
                    },
                    {
                        "name": "Duration",
                        "value": f"{test_results.get('duration', 0):.2f}s",
                        "inline": True
                    }
                ]
            }]
        }

        # Add coverage if available
        if "coverage" in test_results:
            payload["embeds"][0]["fields"].append({
                "name": "Coverage",
                "value": f"{test_results['coverage']:.1f}%",
                "inline": True
            })

        response = requests.post(config.webhook_url, json=payload)
        return {"status": "sent" if response.status_code == 204 or response.status_code == 200 else "failed", "response": response.text}

    def _send_teams(
        self,
        test_results: Dict[str, Any],
        status: str,
        config: NotificationConfig,
        message: Optional[str]
    ) -> Dict[str, Any]:
        """Send Microsoft Teams notification."""
        import requests

        # Color based on status
        colors = {
            "passed": "00FF00",
            "failed": "FF0000",
            "error": "FFD700",
            "regression": "FF4500"
        }

        # Build payload
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"Test Results: {status.upper()}",
            "themeColor": colors.get(status, "00FF00"),
            "title": f"Test Results: {status.upper()}",
            "text": message or self._generate_summary(test_results, status),
            "sections": [
                {
                    "facts": [
                        {"name": "Total Tests", "value": str(test_results.get("total", 0))},
                        {"name": "Passed", "value": str(test_results.get("passed", 0))},
                        {"name": "Failed", "value": str(test_results.get("failed", 0))},
                        {"name": "Duration", "value": f"{test_results.get('duration', 0):.2f}s"}
                    ]
                }
            ]
        }

        response = requests.post(config.webhook_url, json=payload)
        return {"status": "sent" if response.status_code == 200 else "failed", "response": response.text}

    def _generate_summary(self, test_results: Dict[str, Any], status: str) -> str:
        """Generate summary message."""
        summary = f"Test run {status}\n"
        summary += f"Total: {test_results.get('total', 0)}\n"
        summary += f"Passed: {test_results.get('passed', 0)}\n"
        summary += f"Failed: {test_results.get('failed', 0)}\n"

        if "coverage" in test_results:
            summary += f"Coverage: {test_results['coverage']:.1f}%\n"

        if test_results.get("has_regression"):
            summary += "⚠️ Performance regression detected!"

        return summary

    def load_config(self, config_path: str) -> None:
        """
        Load notification configuration from file.

        Args:
            config_path: Path to config file
        """
        with open(config_path, "r") as f:
            data = json.load(f)

        for platform, config_data in data.items():
            self.configs[platform] = NotificationConfig(
                platform=platform,
                **config_data
            )

    def save_config(self, config_path: str) -> None:
        """
        Save notification configuration to file.

        Args:
            config_path: Path to save config
        """
        data = {}
        for platform, config in self.configs.items():
            data[platform] = {
                "webhook_url": config.webhook_url,
                "channel": config.channel,
                "enabled": config.enabled,
                "on_success": config.on_success,
                "on_failure": config.on_failure,
                "on_regression": config.on_regression
            }

        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)


def send_notification(
    webhook_url: str,
    test_results: Dict[str, Any],
    status: str,
    platform: str = "slack",
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to send notification.

    Args:
        webhook_url: Webhook URL
        test_results: Test results
        status: Test status
        platform: Platform (slack, discord, teams)
        message: Custom message (optional)

    Returns:
        Notification result
    """
    manager = NotificationManager()
    config = NotificationConfig(
        platform=platform,
        webhook_url=webhook_url
    )
    manager.add_config(config)
    return manager.send_notification(test_results, status, message)
