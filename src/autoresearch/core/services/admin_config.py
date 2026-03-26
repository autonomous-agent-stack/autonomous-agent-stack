from __future__ import annotations

import re
from typing import Any

from autoresearch.shared.models import (
    AdminAgentConfigCreateRequest,
    AdminAgentConfigRead,
    AdminAgentConfigUpdateRequest,
    AdminChannelConfigCreateRequest,
    AdminChannelConfigRead,
    AdminChannelConfigUpdateRequest,
    AdminConfigRevisionRead,
    AdminConfigRollbackRequest,
    AdminSecretRecordRead,
    utc_now,
)
from autoresearch.core.services.admin_secrets import AdminSecretCipher
from autoresearch.shared.store import Repository, create_resource_id


class AdminConfigService:
    """Editable admin backend for agent/channel configuration with versioned revisions."""

    def __init__(
        self,
        agent_repository: Repository[AdminAgentConfigRead],
        channel_repository: Repository[AdminChannelConfigRead],
        revision_repository: Repository[AdminConfigRevisionRead],
        secret_repository: Repository[AdminSecretRecordRead] | None = None,
        secret_cipher: AdminSecretCipher | None = None,
    ) -> None:
        self._agent_repository = agent_repository
        self._channel_repository = channel_repository
        self._revision_repository = revision_repository
        self._secret_repository = secret_repository
        self._secret_cipher = secret_cipher

    # ---------------------------------------------------------------------
    # Agent config
    # ---------------------------------------------------------------------

    def create_agent(self, request: AdminAgentConfigCreateRequest) -> AdminAgentConfigRead:
        now = utc_now()
        agent_id = create_resource_id("agentcfg")
        record = AdminAgentConfigRead(
            agent_id=agent_id,
            version=1,
            status="active" if request.enabled else "inactive",
            name=request.name.strip(),
            description=request.description.strip(),
            task_name=request.task_name.strip(),
            prompt_template=request.prompt_template,
            default_timeout_seconds=request.default_timeout_seconds,
            default_generation_depth=request.default_generation_depth,
            default_env=dict(request.default_env),
            cli_args=list(request.cli_args),
            command_override=list(request.command_override) if request.command_override else None,
            append_prompt=request.append_prompt,
            channel_bindings=[item.strip() for item in request.channel_bindings if item.strip()],
            metadata=dict(request.metadata),
            created_at=now,
            updated_at=now,
        )
        saved = self._agent_repository.save(record.agent_id, record)
        self._save_revision(
            target_type="agent",
            target_id=saved.agent_id,
            version=saved.version,
            action="create",
            actor=request.actor,
            reason=None,
            snapshot=saved.model_dump(mode="json"),
            metadata={"source": "admin.create_agent"},
        )
        return saved

    def list_agents(self) -> list[AdminAgentConfigRead]:
        items = self._agent_repository.list()
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    def get_agent(self, agent_id: str) -> AdminAgentConfigRead | None:
        return self._agent_repository.get(agent_id)

    def update_agent(self, agent_id: str, request: AdminAgentConfigUpdateRequest) -> AdminAgentConfigRead:
        current = self.get_agent(agent_id)
        if current is None:
            raise KeyError(f"agent config not found: {agent_id}")

        metadata = dict(current.metadata)
        metadata.update(request.metadata_updates)
        updated = current.model_copy(
            update={
                "version": current.version + 1,
                "name": request.name.strip() if request.name is not None else current.name,
                "description": request.description.strip() if request.description is not None else current.description,
                "task_name": request.task_name.strip() if request.task_name is not None else current.task_name,
                "prompt_template": (
                    request.prompt_template if request.prompt_template is not None else current.prompt_template
                ),
                "default_timeout_seconds": (
                    request.default_timeout_seconds
                    if request.default_timeout_seconds is not None
                    else current.default_timeout_seconds
                ),
                "default_generation_depth": (
                    request.default_generation_depth
                    if request.default_generation_depth is not None
                    else current.default_generation_depth
                ),
                "default_env": request.default_env if request.default_env is not None else current.default_env,
                "cli_args": list(request.cli_args) if request.cli_args is not None else current.cli_args,
                "command_override": (
                    list(request.command_override) if request.command_override is not None else current.command_override
                ),
                "append_prompt": request.append_prompt if request.append_prompt is not None else current.append_prompt,
                "channel_bindings": (
                    [item.strip() for item in request.channel_bindings if item.strip()]
                    if request.channel_bindings is not None
                    else current.channel_bindings
                ),
                "metadata": metadata,
                "updated_at": utc_now(),
            }
        )
        saved = self._agent_repository.save(updated.agent_id, updated)
        self._save_revision(
            target_type="agent",
            target_id=saved.agent_id,
            version=saved.version,
            action="update",
            actor=request.actor,
            reason=request.reason,
            snapshot=saved.model_dump(mode="json"),
            metadata={"source": "admin.update_agent"},
        )
        return saved

    def set_agent_enabled(
        self,
        *,
        agent_id: str,
        enabled: bool,
        actor: str,
        reason: str | None = None,
    ) -> AdminAgentConfigRead:
        current = self.get_agent(agent_id)
        if current is None:
            raise KeyError(f"agent config not found: {agent_id}")
        next_status = "active" if enabled else "inactive"
        if current.status == next_status:
            return current

        updated = current.model_copy(
            update={
                "version": current.version + 1,
                "status": next_status,
                "updated_at": utc_now(),
            }
        )
        saved = self._agent_repository.save(updated.agent_id, updated)
        self._save_revision(
            target_type="agent",
            target_id=saved.agent_id,
            version=saved.version,
            action="activate" if enabled else "deactivate",
            actor=actor,
            reason=reason,
            snapshot=saved.model_dump(mode="json"),
            metadata={"source": "admin.set_agent_enabled"},
        )
        return saved

    def rollback_agent(self, agent_id: str, request: AdminConfigRollbackRequest) -> AdminAgentConfigRead:
        current = self.get_agent(agent_id)
        if current is None:
            raise KeyError(f"agent config not found: {agent_id}")

        revision = self._find_revision(target_type="agent", target_id=agent_id, version=request.version)
        if revision is None:
            raise ValueError(f"agent revision not found: version={request.version}")

        snapshot = AdminAgentConfigRead.model_validate(revision.snapshot)
        restored = current.model_copy(
            update={
                "version": current.version + 1,
                "status": snapshot.status,
                "name": snapshot.name,
                "description": snapshot.description,
                "task_name": snapshot.task_name,
                "prompt_template": snapshot.prompt_template,
                "default_timeout_seconds": snapshot.default_timeout_seconds,
                "default_generation_depth": snapshot.default_generation_depth,
                "default_env": snapshot.default_env,
                "cli_args": snapshot.cli_args,
                "command_override": snapshot.command_override,
                "append_prompt": snapshot.append_prompt,
                "channel_bindings": snapshot.channel_bindings,
                "metadata": {
                    **snapshot.metadata,
                    "rollback_from_version": request.version,
                    **request.metadata,
                },
                "updated_at": utc_now(),
            }
        )
        saved = self._agent_repository.save(restored.agent_id, restored)
        self._save_revision(
            target_type="agent",
            target_id=saved.agent_id,
            version=saved.version,
            action="rollback",
            actor=request.actor,
            reason=request.reason,
            snapshot=saved.model_dump(mode="json"),
            metadata={
                "source": "admin.rollback_agent",
                "rollback_from_version": request.version,
                **request.metadata,
            },
        )
        return saved

    # ---------------------------------------------------------------------
    # Channel config
    # ---------------------------------------------------------------------

    def create_channel(self, request: AdminChannelConfigCreateRequest) -> AdminChannelConfigRead:
        if request.secret_value is not None and not request.secret_value.strip():
            raise ValueError("secret_value cannot be empty string")
        key = self._normalize_key(request.key)
        self._ensure_unique_channel_key(key=key, exclude_channel_id=None)
        now = utc_now()
        channel_id = create_resource_id("chcfg")
        record = AdminChannelConfigRead(
            channel_id=channel_id,
            version=1,
            status="active" if request.enabled else "inactive",
            key=key,
            display_name=request.display_name.strip(),
            provider=request.provider,
            endpoint_url=request.endpoint_url.strip() if request.endpoint_url else None,
            secret_ref=request.secret_ref.strip() if request.secret_ref else None,
            has_secret=bool(request.secret_value and request.secret_value.strip()),
            allowed_chat_ids=[item.strip() for item in request.allowed_chat_ids if item.strip()],
            allowed_user_ids=[item.strip() for item in request.allowed_user_ids if item.strip()],
            routing_policy=dict(request.routing_policy),
            metadata=dict(request.metadata),
            created_at=now,
            updated_at=now,
        )
        saved = self._channel_repository.save(record.channel_id, record)
        if request.secret_value is not None and request.secret_value.strip():
            self._upsert_channel_secret(
                channel_id=saved.channel_id,
                secret_value=request.secret_value.strip(),
                actor=request.actor,
                reason="channel create",
            )
            saved = self._with_channel_secret_state(saved)
            saved = self._channel_repository.save(saved.channel_id, saved)
        self._save_revision(
            target_type="channel",
            target_id=saved.channel_id,
            version=saved.version,
            action="create",
            actor=request.actor,
            reason=None,
            snapshot=saved.model_dump(mode="json"),
            metadata={"source": "admin.create_channel"},
        )
        return saved

    def list_channels(self) -> list[AdminChannelConfigRead]:
        items = self._channel_repository.list()
        items = [self._with_channel_secret_state(item) for item in items]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    def get_channel(self, channel_id: str) -> AdminChannelConfigRead | None:
        item = self._channel_repository.get(channel_id)
        if item is None:
            return None
        return self._with_channel_secret_state(item)

    def update_channel(
        self,
        channel_id: str,
        request: AdminChannelConfigUpdateRequest,
    ) -> AdminChannelConfigRead:
        current = self.get_channel(channel_id)
        if current is None:
            raise KeyError(f"channel config not found: {channel_id}")

        key = current.key
        if request.provider is not None and request.provider == "telegram" and not key:
            raise ValueError("channel key cannot be empty")
        if request.secret_value is not None and request.clear_secret:
            raise ValueError("secret_value and clear_secret cannot both be set")
        if request.secret_value is not None and not request.secret_value.strip():
            raise ValueError("secret_value cannot be empty string")

        metadata = dict(current.metadata)
        metadata.update(request.metadata_updates)
        endpoint_url = current.endpoint_url
        if request.endpoint_url is not None:
            endpoint_url = request.endpoint_url.strip() or None

        secret_ref = current.secret_ref
        if request.secret_ref is not None:
            secret_ref = request.secret_ref.strip() or None

        updated = current.model_copy(
            update={
                "version": current.version + 1,
                "display_name": (
                    request.display_name.strip() if request.display_name is not None else current.display_name
                ),
                "provider": request.provider if request.provider is not None else current.provider,
                "endpoint_url": endpoint_url,
                "secret_ref": secret_ref,
                "allowed_chat_ids": (
                    [item.strip() for item in request.allowed_chat_ids if item.strip()]
                    if request.allowed_chat_ids is not None
                    else current.allowed_chat_ids
                ),
                "allowed_user_ids": (
                    [item.strip() for item in request.allowed_user_ids if item.strip()]
                    if request.allowed_user_ids is not None
                    else current.allowed_user_ids
                ),
                "routing_policy": (
                    request.routing_policy if request.routing_policy is not None else current.routing_policy
                ),
                "has_secret": current.has_secret,
                "metadata": metadata,
                "updated_at": utc_now(),
            }
        )
        if request.clear_secret:
            self._delete_channel_secret(
                channel_id=updated.channel_id,
                actor=request.actor,
                reason=request.reason or "channel secret cleared",
            )
        elif request.secret_value is not None and request.secret_value.strip():
            self._upsert_channel_secret(
                channel_id=updated.channel_id,
                secret_value=request.secret_value.strip(),
                actor=request.actor,
                reason=request.reason or "channel secret rotated",
            )
        updated = self._with_channel_secret_state(updated)
        saved = self._channel_repository.save(updated.channel_id, updated)
        self._save_revision(
            target_type="channel",
            target_id=saved.channel_id,
            version=saved.version,
            action="update",
            actor=request.actor,
            reason=request.reason,
            snapshot=saved.model_dump(mode="json"),
            metadata={"source": "admin.update_channel"},
        )
        return saved

    def set_channel_enabled(
        self,
        *,
        channel_id: str,
        enabled: bool,
        actor: str,
        reason: str | None = None,
    ) -> AdminChannelConfigRead:
        current = self.get_channel(channel_id)
        if current is None:
            raise KeyError(f"channel config not found: {channel_id}")
        next_status = "active" if enabled else "inactive"
        if current.status == next_status:
            return current

        updated = current.model_copy(
            update={
                "version": current.version + 1,
                "status": next_status,
                "has_secret": current.has_secret,
                "updated_at": utc_now(),
            }
        )
        saved = self._channel_repository.save(updated.channel_id, updated)
        self._save_revision(
            target_type="channel",
            target_id=saved.channel_id,
            version=saved.version,
            action="activate" if enabled else "deactivate",
            actor=actor,
            reason=reason,
            snapshot=saved.model_dump(mode="json"),
            metadata={"source": "admin.set_channel_enabled"},
        )
        return saved

    def rollback_channel(self, channel_id: str, request: AdminConfigRollbackRequest) -> AdminChannelConfigRead:
        current = self.get_channel(channel_id)
        if current is None:
            raise KeyError(f"channel config not found: {channel_id}")

        revision = self._find_revision(target_type="channel", target_id=channel_id, version=request.version)
        if revision is None:
            raise ValueError(f"channel revision not found: version={request.version}")

        snapshot = AdminChannelConfigRead.model_validate(revision.snapshot)
        self._ensure_unique_channel_key(key=snapshot.key, exclude_channel_id=current.channel_id)
        restored = current.model_copy(
            update={
                "version": current.version + 1,
                "status": snapshot.status,
                "key": snapshot.key,
                "display_name": snapshot.display_name,
                "provider": snapshot.provider,
                "endpoint_url": snapshot.endpoint_url,
                "secret_ref": snapshot.secret_ref,
                "allowed_chat_ids": snapshot.allowed_chat_ids,
                "allowed_user_ids": snapshot.allowed_user_ids,
                "routing_policy": snapshot.routing_policy,
                "has_secret": self._channel_has_secret(current.channel_id),
                "metadata": {
                    **snapshot.metadata,
                    "rollback_from_version": request.version,
                    **request.metadata,
                },
                "updated_at": utc_now(),
            }
        )
        saved = self._channel_repository.save(restored.channel_id, restored)
        self._save_revision(
            target_type="channel",
            target_id=saved.channel_id,
            version=saved.version,
            action="rollback",
            actor=request.actor,
            reason=request.reason,
            snapshot=saved.model_dump(mode="json"),
            metadata={
                "source": "admin.rollback_channel",
                "rollback_from_version": request.version,
                **request.metadata,
            },
        )
        return saved

    def resolve_channel_secret(self, channel_id: str) -> str | None:
        record = self._get_channel_secret_record(channel_id)
        if record is None:
            return None
        cipher = self._ensure_secret_cipher()
        return cipher.decrypt(record.ciphertext)

    # ---------------------------------------------------------------------
    # Revisions
    # ---------------------------------------------------------------------

    def list_revisions(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int = 100,
    ) -> list[AdminConfigRevisionRead]:
        revisions = self._revision_repository.list()
        if target_type is not None:
            revisions = [item for item in revisions if item.target_type == target_type]
        if target_id is not None:
            revisions = [item for item in revisions if item.target_id == target_id]
        revisions.sort(key=lambda item: item.created_at, reverse=True)
        return revisions[: max(1, limit)]

    def _find_revision(
        self,
        *,
        target_type: str,
        target_id: str,
        version: int,
    ) -> AdminConfigRevisionRead | None:
        for item in self._revision_repository.list():
            if item.target_type != target_type:
                continue
            if item.target_id != target_id:
                continue
            if item.version == version:
                return item
        return None

    def _with_channel_secret_state(self, channel: AdminChannelConfigRead) -> AdminChannelConfigRead:
        has_secret = self._channel_has_secret(channel.channel_id)
        if channel.has_secret == has_secret:
            return channel
        return channel.model_copy(update={"has_secret": has_secret})

    def _channel_has_secret(self, channel_id: str) -> bool:
        record = self._get_channel_secret_record(channel_id)
        return record is not None and record.status == "active"

    def _get_channel_secret_record(self, channel_id: str) -> AdminSecretRecordRead | None:
        if self._secret_repository is None:
            return None
        target_id = self._channel_secret_resource_id(channel_id)
        return self._secret_repository.get(target_id)

    def _upsert_channel_secret(
        self,
        *,
        channel_id: str,
        secret_value: str,
        actor: str,
        reason: str,
    ) -> None:
        if self._secret_repository is None:
            raise RuntimeError("secret repository is not configured")
        cipher = self._ensure_secret_cipher()
        now = utc_now()
        target_id = self._channel_secret_resource_id(channel_id)
        existing = self._secret_repository.get(target_id)
        created_at = existing.created_at if existing is not None else now
        record = AdminSecretRecordRead(
            secret_id=target_id,
            scope="channel",
            scope_id=channel_id,
            status="active",
            algorithm="fernet-v1",
            ciphertext=cipher.encrypt(secret_value),
            created_at=created_at,
            updated_at=now,
            metadata={
                "actor": actor,
                "reason": reason,
            },
        )
        self._secret_repository.save(target_id, record)

    def _delete_channel_secret(
        self,
        *,
        channel_id: str,
        actor: str,
        reason: str,
    ) -> None:
        if self._secret_repository is None:
            return
        target_id = self._channel_secret_resource_id(channel_id)
        existing = self._secret_repository.get(target_id)
        if existing is None:
            return
        deleted = existing.model_copy(
            update={
                "status": "deleted",
                "updated_at": utc_now(),
                "metadata": {
                    **existing.metadata,
                    "deleted_by": actor,
                    "delete_reason": reason,
                },
            }
        )
        self._secret_repository.save(target_id, deleted)

    @staticmethod
    def _channel_secret_resource_id(channel_id: str) -> str:
        return f"secret_channel_{channel_id}"

    def _ensure_secret_cipher(self) -> AdminSecretCipher:
        if self._secret_cipher is None or not self._secret_cipher.enabled:
            raise RuntimeError("secret cipher is disabled: missing AUTORESEARCH_ADMIN_SECRET_KEY")
        return self._secret_cipher

    def _save_revision(
        self,
        *,
        target_type: str,
        target_id: str,
        version: int,
        action: str,
        actor: str,
        reason: str | None,
        snapshot: dict[str, Any],
        metadata: dict[str, Any],
    ) -> AdminConfigRevisionRead:
        entry = AdminConfigRevisionRead(
            revision_id=create_resource_id("rev"),
            target_type=target_type,
            target_id=target_id,
            version=version,
            action=action,
            actor=actor.strip() or "admin_api",
            reason=reason.strip() if isinstance(reason, str) and reason.strip() else None,
            snapshot=snapshot,
            metadata=metadata,
            created_at=utc_now(),
        )
        return self._revision_repository.save(entry.revision_id, entry)

    def _ensure_unique_channel_key(self, *, key: str, exclude_channel_id: str | None) -> None:
        for item in self.list_channels():
            if exclude_channel_id is not None and item.channel_id == exclude_channel_id:
                continue
            if item.key == key:
                raise ValueError(f"duplicate channel key: {key}")

    @staticmethod
    def _normalize_key(value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip().lower())
        normalized = re.sub(r"-+", "-", normalized).strip("-")
        if not normalized:
            raise ValueError("channel key must contain alphanumeric characters")
        return normalized
