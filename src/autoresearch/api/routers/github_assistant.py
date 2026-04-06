from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_github_assistant_service
from autoresearch.github_assistant.models import (
    GitHubAssistantDoctorRead,
    GitHubAssistantExecutionRunRead,
    GitHubAssistantHealthRead,
    GitHubAssistantIssueRequest,
    GitHubAssistantPullRequestRequest,
    GitHubAssistantPullRequestReviewRunRead,
    GitHubAssistantReleasePlanRequest,
    GitHubAssistantReleasePlanRunRead,
    GitHubAssistantTriageRunRead,
    ScheduleSummary,
)
from autoresearch.github_assistant.service import GitHubAssistantService


router = APIRouter(prefix="/api/v1/github-assistant", tags=["github-assistant"])


@router.get("/health", response_model=GitHubAssistantHealthRead)
def github_assistant_health(
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantHealthRead:
    return service.health_report()


@router.get("/doctor", response_model=GitHubAssistantDoctorRead)
def github_assistant_doctor(
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantDoctorRead:
    return service.doctor_report()


@router.post("/triage", response_model=GitHubAssistantTriageRunRead)
def triage_github_issue(
    payload: GitHubAssistantIssueRequest,
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantTriageRunRead:
    try:
        run_dir, triage = service.triage(payload.repo, payload.issue_number)
    except Exception as exc:
        raise _assistant_http_exception(exc) from exc
    return GitHubAssistantTriageRunRead(
        run_dir=str(run_dir),
        summary=service.read_summary(run_dir),
        triage=triage,
    )


@router.post("/execute", response_model=GitHubAssistantExecutionRunRead)
def execute_github_issue(
    payload: GitHubAssistantIssueRequest,
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantExecutionRunRead:
    try:
        run_dir = service.execute(payload.repo, payload.issue_number)
    except Exception as exc:
        raise _assistant_http_exception(exc) from exc
    return GitHubAssistantExecutionRunRead(
        run_dir=str(run_dir),
        summary=service.read_summary(run_dir),
    )


@router.post("/review-pr", response_model=GitHubAssistantPullRequestReviewRunRead)
def review_github_pull_request(
    payload: GitHubAssistantPullRequestRequest,
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantPullRequestReviewRunRead:
    try:
        run_dir, review = service.review_pr(payload.repo, payload.pr_number)
    except Exception as exc:
        raise _assistant_http_exception(exc) from exc
    return GitHubAssistantPullRequestReviewRunRead(
        run_dir=str(run_dir),
        summary=service.read_summary(run_dir),
        review=review,
    )


@router.post("/release-plan", response_model=GitHubAssistantReleasePlanRunRead)
def build_github_release_plan(
    payload: GitHubAssistantReleasePlanRequest,
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantReleasePlanRunRead:
    try:
        run_dir, release_plan = service.release_plan(
            payload.repo,
            version=payload.version,
            limit=payload.limit,
        )
    except Exception as exc:
        raise _assistant_http_exception(exc) from exc
    return GitHubAssistantReleasePlanRunRead(
        run_dir=str(run_dir),
        summary=service.read_summary(run_dir),
        release_plan=release_plan,
    )


@router.post("/schedule/run", response_model=ScheduleSummary)
def run_github_assistant_schedule(
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> ScheduleSummary:
    try:
        return service.schedule_run()
    except Exception as exc:
        raise _assistant_http_exception(exc) from exc


def _assistant_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc).strip("'"))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
