"""OAuth 2.0 Manager for Google Workspace APIs.

Handles authentication and token management for Google services.
All credentials are loaded from environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    Credentials = None
    InstalledAppFlow = None
    Request = None
    _GOOGLE_AUTH_IMPORT_ERROR = exc
else:
    _GOOGLE_AUTH_IMPORT_ERROR = None


class OAuthManager:
    """Manages OAuth 2.0 authentication for Google Workspace APIs.

    Credentials are loaded from environment variables:
    - GOOGLE_CLIENT_ID: OAuth client ID
    - GOOGLE_CLIENT_SECRET: OAuth client secret
    - GOOGLE_REDIRECT_URI: Redirect URI (default: http://localhost)

    Tokens are cached in ~/.config/autoresearch/google_token.json
    """

    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/tasks",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def __init__(self) -> None:
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Google OAuth credentials not found. "
                "Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
            )

        self.token_path = Path.home() / ".config" / "autoresearch" / "google_token.json"
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

    def get_credentials(self) -> Credentials:
        """Get valid OAuth 2.0 credentials.

        Returns:
            Credentials object for Google API calls.

        Raises:
            ValueError: If credentials are invalid or missing.
        """
        if Credentials is None or InstalledAppFlow is None or Request is None:
            raise RuntimeError(
                "Google OAuth dependencies are missing. Install with: "
                "`pip install google-auth google-auth-oauthlib`"
            ) from _GOOGLE_AUTH_IMPORT_ERROR

        creds = None

        # Load existing token if available
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), self.SCOPES)

        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Create credentials dict from environment variables
                client_config = {
                    "installed": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uris": [self.redirect_uri],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }

                flow = InstalledAppFlow.from_client_config(client_config, self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(self.token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return creds

    def revoke_credentials(self) -> None:
        """Revoke OAuth credentials and delete cached token."""
        if self.token_path.exists():
            self.token_path.unlink()
