from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from autoresearch.shared.models import ButlerAgentStateRead, ButlerAgentStatus, utc_now
from autoresearch.shared.store import Repository


@dataclass(frozen=True)
class ButlerAgentDefinition:
    agent_name: str
    capability_id: str


DEFAULT_BUTLER_AGENT_DEFINITIONS: tuple[ButlerAgentDefinition, ...] = (
    ButlerAgentDefinition("butler_orchestrator", "hermes_openclaw"),
    ButlerAgentDefinition("source_collect", "source_collect"),
    ButlerAgentDefinition("content_kb", "content_kb"),
    ButlerAgentDefinition("excel_audit", "excel_audit"),
    ButlerAgentDefinition("youtube_ops", "youtube_autoflow"),
    ButlerAgentDefinition("github_ops_accountA", "github_assistant"),
    ButlerAgentDefinition("github_ops_accountB", "github_assistant"),
)


class ButlerAgentStateService:
    """Persistent hot-plug state for Butler target agents."""

    def __init__(
        self,
        *,
        repository: Repository[ButlerAgentStateRead],
        definitions: tuple[ButlerAgentDefinition, ...] = DEFAULT_BUTLER_AGENT_DEFINITIONS,
    ) -> None:
        self._repository = repository
        self._definitions = definitions
        self._definition_by_name = {item.agent_name: item for item in definitions}
        self._canonical_by_lower = {item.agent_name.lower(): item.agent_name for item in definitions}

    def list_agents(self, *, now: datetime | None = None) -> list[ButlerAgentStateRead]:
        current = now or utc_now()
        saved = {item.agent_name: item for item in self._repository.list()}
        ordered: list[ButlerAgentStateRead] = []
        for definition in self._definitions:
            ordered.append(saved.pop(definition.agent_name, self._default_state(definition, now=current)))
        ordered.extend(sorted(saved.values(), key=lambda item: item.agent_name))
        return ordered

    def get_agent(self, agent_name: str, *, now: datetime | None = None) -> ButlerAgentStateRead | None:
        canonical = self._canonical_agent_name(agent_name)
        if canonical is None:
            return None
        saved = self._repository.get(canonical)
        if saved is not None:
            return saved
        return self._default_state(self._definition_by_name[canonical], now=now or utc_now())

    def set_status(
        self,
        agent_name: str,
        status: ButlerAgentStatus | str,
        *,
        actor: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> ButlerAgentStateRead:
        current = now or utc_now()
        canonical = self._canonical_agent_name(agent_name)
        if canonical is None:
            raise KeyError(agent_name)
        normalized_status = ButlerAgentStatus(status)
        definition = self._definition_by_name[canonical]
        current_state = self.get_agent(canonical, now=current)
        current_metadata = dict(current_state.metadata) if current_state is not None else {}
        next_metadata = {**current_metadata, **dict(metadata or {})}
        state = ButlerAgentStateRead(
            agent_name=canonical,
            status=normalized_status,
            capability_id=definition.capability_id,
            reason=reason,
            actor=actor.strip() or "butlerctl",
            updated_at=current,
            metadata=next_metadata,
        )
        return self._repository.save(canonical, state)

    def is_active(self, agent_name: str | None) -> bool:
        name = str(agent_name or "").strip()
        if not name:
            return True
        state = self.get_agent(name)
        if state is None:
            return True
        return state.status == ButlerAgentStatus.ACTIVE

    def nonactive_agents(self) -> list[ButlerAgentStateRead]:
        return [item for item in self.list_agents() if item.status != ButlerAgentStatus.ACTIVE]

    def unavailable_reason(self, agent_name: str | None) -> tuple[ButlerAgentStateRead, str] | None:
        name = str(agent_name or "").strip()
        if not name:
            return None
        state = self.get_agent(name)
        if state is None or state.status == ButlerAgentStatus.ACTIVE:
            return None
        if state.status == ButlerAgentStatus.DRAINING:
            return state, f"Agent {state.agent_name} is draining and not accepting new tasks"
        return state, f"Agent {state.agent_name} is disabled and not accepting new tasks"

    def default_agent_for_capability(self, capability_id: str | None) -> str | None:
        capability = str(capability_id or "").strip()
        if not capability:
            return None
        for definition in self._definitions:
            if definition.capability_id == capability:
                return definition.agent_name
        return None

    def _canonical_agent_name(self, value: str) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        if text in self._definition_by_name:
            return text
        return self._canonical_by_lower.get(text.lower())

    @staticmethod
    def _default_state(definition: ButlerAgentDefinition, *, now: datetime) -> ButlerAgentStateRead:
        return ButlerAgentStateRead(
            agent_name=definition.agent_name,
            status=ButlerAgentStatus.ACTIVE,
            capability_id=definition.capability_id,
            reason=None,
            actor="system",
            updated_at=now,
            metadata={"source": "default"},
        )
