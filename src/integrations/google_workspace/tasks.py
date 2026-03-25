"""Google Tasks API Client.

Provides tools for managing Google Tasks.
"""

from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .oauth import OAuthManager


class GoogleTasksClient:
    """Client for Google Tasks API operations.

    Provides the following tools:
    - list_google_tasks: List tasks from a task list
    - create_google_task: Create a new task
    """

    def __init__(self, oauth_manager: OAuthManager | None = None) -> None:
        self.oauth_manager = oauth_manager or OAuthManager()
        self._service = None

    @property
    def service(self):
        """Lazy-load Google Tasks service."""
        if self._service is None:
            credentials = self.oauth_manager.get_credentials()
            self._service = build("tasks", "v1", credentials=credentials)
        return self._service

    def list_google_tasks(
        self,
        task_list_id: str = "@default",
        max_results: int = 100,
        show_completed: bool = False,
    ) -> dict[str, Any]:
        """List Google Tasks from a task list.

        Args:
            task_list_id: Task list ID (default: "@default")
            max_results: Maximum number of tasks to return
            show_completed: Whether to include completed tasks

        Returns:
            List of tasks
        """
        try:
            tasks_result = (
                self.service.tasks()
                .list(
                    tasklist=task_list_id,
                    maxResults=max_results,
                    showCompleted=show_completed,
                )
                .execute()
            )

            tasks = tasks_result.get("items", [])
            return {
                "status": "success",
                "count": len(tasks),
                "tasks": [
                    {
                        "id": task["id"],
                        "title": task["title"],
                        "notes": task.get("notes"),
                        "status": task.get("status"),
                        "due": task.get("due"),
                        "completed": task.get("completed"),
                    }
                    for task in tasks
                ],
            }
        except HttpError as error:
            return {
                "status": "error",
                "error": str(error),
                "error_code": error.status_code,
            }

    def create_google_task(
        self,
        title: str,
        task_list_id: str = "@default",
        notes: str | None = None,
        due: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Google Task.

        Args:
            title: Task title
            task_list_id: Task list ID (default: "@default")
            notes: Task notes/description (optional)
            due: Due date in RFC 3339 format (optional)

        Returns:
            Created task data
        """
        task = {
            "title": title,
        }

        if notes:
            task["notes"] = notes
        if due:
            task["due"] = due

        try:
            created_task = (
                self.service.tasks()
                .insert(tasklist=task_list_id, body=task)
                .execute()
            )
            return {
                "status": "success",
                "task_id": created_task["id"],
                "title": created_task["title"],
                "notes": created_task.get("notes"),
                "due": created_task.get("due"),
                "self_link": created_task["selfLink"],
            }
        except HttpError as error:
            return {
                "status": "error",
                "error": str(error),
                "error_code": error.status_code,
            }

    def list_task_lists(self) -> dict[str, Any]:
        """List all Google Task lists.

        Returns:
            List of task lists
        """
        try:
            task_lists_result = self.service.tasklists().list().execute()
            task_lists = task_lists_result.get("items", [])

            return {
                "status": "success",
                "count": len(task_lists),
                "task_lists": [
                    {
                        "id": task_list["id"],
                        "title": task_list["title"],
                        "updated": task_list["updated"],
                    }
                    for task_list in task_lists
                ],
            }
        except HttpError as error:
            return {
                "status": "error",
                "error": str(error),
                "error_code": error.status_code,
            }
