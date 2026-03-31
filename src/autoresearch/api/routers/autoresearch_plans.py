from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import (
    get_autoresearch_planner_service,
    get_housekeeper_service,
    get_panel_access_service,
    get_telegram_notifier_service,
)
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.housekeeper import HousekeeperService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.autoresearch_planner_contract import (
    AutoResearchPlanRead,
    AutoResearchPlannerRequest,
    UpstreamWatchDecision,
)


router = APIRouter(prefix="/api/v1/autoresearch/plans", tags=["autoresearch-plans"])


@router.post(
    "",
    response_model=AutoResearchPlanRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_autoresearch_plan(
    payload: AutoResearchPlannerRequest,
    service: AutoResearchPlannerService = Depends(get_autoresearch_planner_service),
    housekeeper_service: HousekeeperService = Depends(get_housekeeper_service),
    panel_access_service: PanelAccessService = Depends(get_panel_access_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
) -> AutoResearchPlanRead:
    prepared, _, _ = housekeeper_service.prepare_planner_request(payload, trigger_source="api")
    telegram_uid = _select_plan_notification_uid(payload=prepared, panel_access_service=panel_access_service)
    plan = service.create(prepared.model_copy(update={"telegram_uid": telegram_uid}))
    panel_action_url = None
    notification_sent = False

    if plan.selected_candidate is not None:
        panel_action_url = _build_plan_panel_action_url(
            panel_access_service=panel_access_service,
            plan_id=plan.plan_id,
            telegram_uid=telegram_uid,
        )
        notification_sent = _send_plan_notification(
            notifier=notifier,
            panel_access_service=panel_access_service,
            plan=plan,
            panel_action_url=panel_action_url,
            telegram_uid=telegram_uid,
        )
    notification_sent = _send_upstream_watch_notification(
        notifier=notifier,
        plan=plan,
        telegram_uid=telegram_uid,
    ) or notification_sent
    if plan.selected_candidate is None and not notification_sent and telegram_uid == plan.telegram_uid:
        return plan
    return service.update_delivery(
        plan.plan_id,
        telegram_uid=telegram_uid,
        panel_action_url=panel_action_url,
        notification_sent=notification_sent,
    )


@router.get("", response_model=list[AutoResearchPlanRead])
def list_autoresearch_plans(
    service: AutoResearchPlannerService = Depends(get_autoresearch_planner_service),
) -> list[AutoResearchPlanRead]:
    return service.list()


@router.get("/{plan_id}", response_model=AutoResearchPlanRead)
def get_autoresearch_plan(
    plan_id: str,
    service: AutoResearchPlannerService = Depends(get_autoresearch_planner_service),
) -> AutoResearchPlanRead:
    plan = service.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AutoResearch plan not found")
    return plan


def _select_plan_notification_uid(
    *,
    payload: AutoResearchPlannerRequest,
    panel_access_service: PanelAccessService,
) -> str | None:
    candidate = (payload.telegram_uid or "").strip()
    allowed_uids = panel_access_service.allowed_uids
    if candidate:
        if allowed_uids and candidate not in allowed_uids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="telegram uid is not allowed for panel access",
            )
        return candidate
    if len(allowed_uids) == 1:
        return allowed_uids[0]
    return None


def _build_plan_panel_action_url(
    *,
    panel_access_service: PanelAccessService,
    plan_id: str,
    telegram_uid: str | None,
) -> str:
    return panel_access_service.build_action_url(
        query_params={"planId": plan_id},
        telegram_uid=telegram_uid,
        prefer_mini_app=True,
    )


def _build_plan_notification_markup(
    *,
    panel_access_service: PanelAccessService,
    panel_action_url: str,
) -> dict[str, object] | None:
    markups = _build_plan_notification_markups(
        panel_access_service=panel_access_service,
        panel_action_url=panel_action_url,
    )
    return markups[0] if markups else None


def _build_plan_notification_markups(
    *,
    panel_access_service: PanelAccessService,
    panel_action_url: str,
) -> list[dict[str, object] | None]:
    parsed = urlparse(panel_action_url)
    if parsed.scheme != "https":
        return [None]
    url_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "打开 Panel 审批",
                    "url": panel_action_url,
                }
            ]
        ]
    }
    if panel_access_service.mini_app_url:
        return [
            {
                "inline_keyboard": [
                    [
                        {
                            "text": "打开 Mini App 审批",
                            "web_app": {"url": panel_action_url},
                        }
                    ]
                ]
            },
            url_markup,
            None,
        ]
    return [url_markup, None]


def _send_plan_notification(
    *,
    notifier: TelegramNotifierService,
    panel_access_service: PanelAccessService,
    plan: AutoResearchPlanRead,
    panel_action_url: str,
    telegram_uid: str | None,
) -> bool:
    if not notifier.enabled or not telegram_uid:
        return False
    for reply_markup in _build_plan_notification_markups(
        panel_access_service=panel_access_service,
        panel_action_url=panel_action_url,
    ):
        if notifier.send_message(
            chat_id=telegram_uid,
            text=_build_plan_notification_text(plan, delivery=_plan_notification_delivery(reply_markup)),
            reply_markup=reply_markup,
        ):
            return True
    return False


def _plan_notification_delivery(reply_markup: dict[str, object] | None) -> str:
    if reply_markup is None:
        return "text"
    try:
        button = reply_markup["inline_keyboard"][0][0]
    except (KeyError, IndexError, TypeError):
        return "panel"
    if isinstance(button, dict) and "web_app" in button:
        return "mini_app"
    return "panel"


def _build_plan_notification_text(plan: AutoResearchPlanRead, *, delivery: str) -> str:
    candidate = plan.selected_candidate
    if candidate is None:
        return "🔍 AutoResearch 完成扫描，但暂时没有生成可执行的规划单。"
    estimated_changes = max(1, len(candidate.allowed_paths))
    approval_hint = "请前往 Panel 审批执行。"
    if delivery == "mini_app":
        approval_hint = "请前往 Mini App 审批执行。"
    return (
        f"🔍 AutoResearch 发现新优化点: {candidate.title}\n"
        f"- target: {candidate.source_path}\n"
        f"- category: {candidate.category}\n"
        f"- estimated_changes: {estimated_changes}\n"
        f"{approval_hint}"
    )


def _send_upstream_watch_notification(
    *,
    notifier: TelegramNotifierService,
    plan: AutoResearchPlanRead,
    telegram_uid: str | None,
) -> bool:
    upstream_watch = plan.upstream_watch
    if not notifier.enabled or not telegram_uid or upstream_watch is None:
        return False
    if upstream_watch.decision is not UpstreamWatchDecision.SKIP:
        return False
    return notifier.send_message(
        chat_id=telegram_uid,
        text=_build_upstream_watch_notification_text(plan),
    )


def _build_upstream_watch_notification_text(plan: AutoResearchPlanRead) -> str:
    upstream_watch = plan.upstream_watch
    if upstream_watch is None:
        return "🛡️ 已完成上游巡检，当前没有需要同步的核心更新。"
    focus_labels = [_format_upstream_focus_area(item) for item in upstream_watch.focus_areas if item != "repo-meta"]
    focus_hint = "/".join(focus_labels[:3]) or "近期扩展"
    return (
        f"🛡️ 已完成上游巡检，最新变更（{focus_hint} 修复）与核心基建无关，"
        "已自动拦截跳过。"
    )


def _format_upstream_focus_area(focus_area: str) -> str:
    if focus_area.startswith("extension:"):
        name = focus_area.split(":", 1)[1]
        if name.lower() == "line":
            return "LINE"
        return name.replace("-", " ").title()
    return focus_area.replace("-", " ")
