from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import (
    get_github_assistant_service,
    get_github_assistant_service_registry,
)
from autoresearch.github_assistant.models import (
    GitHubAssistantDoctorRead,
    GitHubAssistantExecutionRunRead,
    GitHubAssistantHealthRead,
    GitHubAssistantIssueRequest,
    GitHubAssistantProfileStatusRead,
    GitHubAssistantProfilesRead,
    GitHubAssistantPullRequestRequest,
    GitHubAssistantPullRequestReviewRunRead,
    GitHubAssistantReleasePlanRequest,
    GitHubAssistantReleasePlanRunRead,
    GitHubAssistantTriageRunRead,
    GitHubAssistantYouTubePublishRequest,
    GitHubAssistantYouTubePublishRunRead,
    ScheduleSummary,
)
from autoresearch.github_assistant.service import GitHubAssistantService, GitHubAssistantServiceRegistry


router = APIRouter(prefix="/api/v1/github-assistant", tags=["github assistant"])


def _detail_from_exception(exc: Exception) -> str:
    if isinstance(exc, KeyError) and exc.args:
        return str(exc.args[0])
    return str(exc).strip() or exc.__class__.__name__


def _github_assistant_http_exception(exc: Exception) -> HTTPException:
    detail = _detail_from_exception(exc)
    lowered = detail.lower()

    if isinstance(exc, KeyError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, FileNotFoundError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, ValueError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, RuntimeError) and any(
        token in lowered
        for token in (
            "gh auth",
            "not logged",
            "authentication",
            "token",
            "login failed",
        )
    ):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        detail = (
            "GitHub auth unavailable. Run `gh auth login` with the configured GitHub login, "
            "then rerun `./assistant doctor` or `GET /api/v1/github-assistant/doctor`. "
            f"Original error: {detail}"
        )
    elif isinstance(exc, RuntimeError):
        status_code = status.HTTP_502_BAD_GATEWAY
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=detail)


def _run_read_fields(service: GitHubAssistantService, *, run_dir: str, artifacts: list[str], summary) -> dict[str, object]:
    return {
        "profile_id": service.profile.id,
        "profile_display_name": service.profile.display_name,
        "run_dir": run_dir,
        "artifacts": artifacts,
        "summary": summary,
    }


@router.get("/profiles", response_model=GitHubAssistantProfilesRead)
def list_github_assistant_profiles(
    registry: GitHubAssistantServiceRegistry = Depends(get_github_assistant_service_registry),
) -> GitHubAssistantProfilesRead:
    default_profile = registry.default_profile_id()
    profiles = []
    for profile in registry.list_profiles():
        health = registry.get(profile.id).health_report()
        profiles.append(
            GitHubAssistantProfileStatusRead(
                profile_id=profile.id,
                profile_display_name=profile.display_name,
                default_profile=profile.id == default_profile,
                github_host=health.github_host,
                managed_repo_count=health.managed_repo_count,
                status=health.status,
                doctor_ok=health.doctor_ok,
                gh_auth_ok=health.gh_auth_ok,
                expected_github_login=health.expected_github_login,
                active_login=health.active_login,
                checks=health.checks,
            )
        )
    return GitHubAssistantProfilesRead(default_profile=default_profile, profiles=profiles)


@router.get("/health", response_model=GitHubAssistantHealthRead)
def get_github_assistant_health(
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantHealthRead:
    return service.health_report()


@router.get("/doctor", response_model=GitHubAssistantDoctorRead)
def run_github_assistant_doctor(
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
        raise _github_assistant_http_exception(exc) from exc
    return GitHubAssistantTriageRunRead(**_run_read_fields(service, run_dir=str(run_dir), artifacts=service.list_artifacts(run_dir), summary=service.read_summary(run_dir)), triage=triage)


@router.post("/execute", response_model=GitHubAssistantExecutionRunRead)
def execute_github_issue(
    payload: GitHubAssistantIssueRequest,
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantExecutionRunRead:
    try:
        run_dir = service.execute(payload.repo, payload.issue_number)
    except Exception as exc:
        raise _github_assistant_http_exception(exc) from exc
    return GitHubAssistantExecutionRunRead(
        **_run_read_fields(
            service,
            run_dir=str(run_dir),
            artifacts=service.list_artifacts(run_dir),
            summary=service.read_summary(run_dir),
        )
    )


@router.post("/publish-youtube", response_model=GitHubAssistantYouTubePublishRunRead)
def publish_youtube_digest(
    payload: GitHubAssistantYouTubePublishRequest,
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantYouTubePublishRunRead:
    try:
        run_dir, publish = service.publish_youtube(payload)
    except Exception as exc:
        raise _github_assistant_http_exception(exc) from exc
    return GitHubAssistantYouTubePublishRunRead(
        **_run_read_fields(
            service,
            run_dir=str(run_dir),
            artifacts=service.list_artifacts(run_dir),
            summary=service.read_summary(run_dir),
        ),
        publish=publish,
    )


@router.post("/review-pr", response_model=GitHubAssistantPullRequestReviewRunRead)
def review_github_pull_request(
    payload: GitHubAssistantPullRequestRequest,
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> GitHubAssistantPullRequestReviewRunRead:
    try:
        run_dir, review = service.review_pr(payload.repo, payload.pr_number)
    except Exception as exc:
        raise _github_assistant_http_exception(exc) from exc
    return GitHubAssistantPullRequestReviewRunRead(
        **_run_read_fields(
            service,
            run_dir=str(run_dir),
            artifacts=service.list_artifacts(run_dir),
            summary=service.read_summary(run_dir),
        ),
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
        raise _github_assistant_http_exception(exc) from exc
    return GitHubAssistantReleasePlanRunRead(
        **_run_read_fields(
            service,
            run_dir=str(run_dir),
            artifacts=service.list_artifacts(run_dir),
            summary=service.read_summary(run_dir),
        ),
        release_plan=release_plan,
    )


@router.post("/schedule/run", response_model=ScheduleSummary)
def run_github_schedule(
    service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> ScheduleSummary:
    try:
        return service.schedule_run()
    except Exception as exc:
        raise _github_assistant_http_exception(exc) from exc
