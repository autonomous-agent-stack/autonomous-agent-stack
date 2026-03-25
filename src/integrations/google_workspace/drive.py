"""Google Drive API Client.

Provides tools for uploading and managing files in Google Drive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

from .oauth import OAuthManager


class GoogleDriveClient:
    """Client for Google Drive API operations.

    Provides the following tools:
    - upload_to_drive: Upload a file to Google Drive
    - list_drive_files: List files in Google Drive
    """

    def __init__(self, oauth_manager: OAuthManager | None = None) -> None:
        self.oauth_manager = oauth_manager or OAuthManager()
        self._service = None

    @property
    def service(self):
        """Lazy-load Google Drive service."""
        if self._service is None:
            credentials = self.oauth_manager.get_credentials()
            self._service = build("drive", "v3", credentials=credentials)
        return self._service

    def upload_to_drive(
        self,
        file_path: str | None = None,
        file_stream: BinaryIO | None = None,
        filename: str | None = None,
        mime_type: str | None = None,
        parent_folder_id: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Upload a file to Google Drive.

        Args:
            file_path: Local file path (mutually exclusive with file_stream)
            file_stream: Binary file stream (mutually exclusive with file_path)
            filename: Name for the uploaded file (required if using file_stream)
            mime_type: MIME type of the file (auto-detected if not provided)
            parent_folder_id: ID of parent folder (optional)
            description: File description (optional)

        Returns:
            Uploaded file metadata

        Raises:
            ValueError: If neither file_path nor file_stream is provided
        """
        if not file_path and not file_stream:
            raise ValueError("Either file_path or file_stream must be provided")

        if file_path:
            path = Path(file_path)
            if not path.exists():
                return {
                    "status": "error",
                    "error": f"File not found: {file_path}",
                }

            filename = filename or path.name
            media = MediaFileUpload(
                str(path),
                mimetype=mime_type,
                resumable=True,
            )
        else:
            if not filename:
                raise ValueError("filename is required when using file_stream")
            media = MediaIoBaseUpload(
                file_stream,
                mimetype=mime_type,
                resumable=True,
            )

        file_metadata = {"name": filename}
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]
        if description:
            file_metadata["description"] = description

        try:
            uploaded_file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, mimeType, size, webViewLink, createdTime",
                )
                .execute()
            )

            return {
                "status": "success",
                "file_id": uploaded_file["id"],
                "name": uploaded_file["name"],
                "mime_type": uploaded_file["mimeType"],
                "size": uploaded_file.get("size"),
                "web_view_link": uploaded_file["webViewLink"],
                "created_time": uploaded_file["createdTime"],
            }
        except HttpError as error:
            return {
                "status": "error",
                "error": str(error),
                "error_code": error.status_code,
            }

    def list_drive_files(
        self,
        query: str | None = None,
        page_size: int = 100,
        order_by: str = "createdTime desc",
    ) -> dict[str, Any]:
        """List files in Google Drive.

        Args:
            query: Search query (e.g., "name contains 'report'")
            page_size: Number of files to return
            order_by: Sort order (e.g., "createdTime desc", "name")

        Returns:
            List of files
        """
        try:
            files_result = (
                self.service.files()
                .list(
                    pageSize=page_size,
                    q=query,
                    orderBy=order_by,
                    fields="files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)",
                )
                .execute()
            )

            files = files_result.get("files", [])
            return {
                "status": "success",
                "count": len(files),
                "files": [
                    {
                        "id": file["id"],
                        "name": file["name"],
                        "mime_type": file["mimeType"],
                        "size": file.get("size"),
                        "created_time": file.get("createdTime"),
                        "modified_time": file.get("modifiedTime"),
                        "web_view_link": file.get("webViewLink"),
                    }
                    for file in files
                ],
            }
        except HttpError as error:
            return {
                "status": "error",
                "error": str(error),
                "error_code": error.status_code,
            }

    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder
            parent_folder_id: ID of parent folder (optional)

        Returns:
            Created folder metadata
        """
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            folder_metadata["parents"] = [parent_folder_id]

        try:
            folder = (
                self.service.files()
                .create(
                    body=folder_metadata,
                    fields="id, name, webViewLink",
                )
                .execute()
            )

            return {
                "status": "success",
                "folder_id": folder["id"],
                "name": folder["name"],
                "web_view_link": folder["webViewLink"],
            }
        except HttpError as error:
            return {
                "status": "error",
                "error": str(error),
                "error_code": error.status_code,
            }
