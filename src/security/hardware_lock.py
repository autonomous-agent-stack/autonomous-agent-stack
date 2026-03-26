"""
Hardware Lock - WebAuthn 物理锁

FIDO2 注册与断言逻辑
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AuthenticatorAttachment,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier

logger = logging.getLogger(__name__)


@dataclass
class WebAuthnChallenge:
    """WebAuthn 挑战"""
    challenge_id: str
    challenge: bytes
    created_at: datetime
    expires_at: datetime
    operation: str
    verified: bool = False


class HardwareLock:
    """WebAuthn 物理锁"""

    def __init__(self, rp_id: str = "localhost", rp_name: str = "Autonomous Agent Stack"):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.challenges: Dict[str, WebAuthnChallenge] = {}
        self.registered_credentials: Dict[str, bytes] = {}

    async def generate_registration_challenge(self, user_id: str) -> Dict[str, Any]:
        """生成注册挑战"""
        try:
            import uuid
            challenge_id = f"reg_{uuid.uuid4().hex[:12]}"

            # 生成注册选项
            options = generate_registration_options(
                rp_id=self.rp_id,
                rp_name=self.rp_name,
                user_id=user_id.encode(),
                user_name=user_id,
                user_display_name=user_id,
                authenticator_selection=AuthenticatorSelectionCriteria(
                    authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                    user_verification=UserVerificationRequirement.REQUIRED
                ),
                supported_pub_key_algs=[
                    COSEAlgorithmIdentifier.ECDSA_SHA_256,
                    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
                ],
            )

            # 存储挑战
            challenge = WebAuthnChallenge(
                challenge_id=challenge_id,
                challenge=options.challenge,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=5),
                operation="registration"
            )
            self.challenges[challenge_id] = challenge

            logger.info(f"[HardwareLock] 🔑 注册挑战已生成: {challenge_id}")

            return json.loads(options_to_json(options))

        except Exception as e:
            logger.error(f"[HardwareLock] ❌ 生成注册挑战失败: {e}")
            raise

    async def verify_registration(self, challenge_id: str, credential: Dict[str, Any]) -> bool:
        """验证注册响应"""
        try:
            challenge = self.challenges.get(challenge_id)
            if not challenge:
                raise ValueError("挑战不存在")

            if datetime.now() > challenge.expires_at:
                raise ValueError("挑战已过期")

            # 验证注册响应
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=challenge.challenge,
                expected_origin=f"https://{self.rp_id}",
                expected_rp_id=self.rp_id,
            )

            # 存储凭证
            self.registered_credentials[challenge_id] = verification.credential_id

            # 标记挑战为已验证
            challenge.verified = True

            logger.info(f"[HardwareLock] ✅ 注册验证成功: {challenge_id}")
            return True

        except Exception as e:
            logger.error(f"[HardwareLock] ❌ 注册验证失败: {e}")
            return False

    async def generate_authentication_challenge(self, operation: str) -> Dict[str, Any]:
        """生成认证挑战"""
        try:
            import uuid
            challenge_id = f"auth_{uuid.uuid4().hex[:12]}"

            # 生成认证选项
            options = generate_authentication_options(
                rp_id=self.rp_id,
                user_verification=UserVerificationRequirement.REQUIRED,
                allow_credentials=[
                    PublicKeyCredentialDescriptor(id=cred_id)
                    for cred_id in self.registered_credentials.values()
                ]
            )

            # 存储挑战
            challenge = WebAuthnChallenge(
                challenge_id=challenge_id,
                challenge=options.challenge,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=1),
                operation=operation
            )
            self.challenges[challenge_id] = challenge

            logger.info(f"[HardwareLock] 🔐 认证挑战已生成: {operation}")

            return json.loads(options_to_json(options))

        except Exception as e:
            logger.error(f"[HardwareLock] ❌ 生成认证挑战失败: {e}")
            raise

    async def verify_authentication(self, challenge_id: str, credential: Dict[str, Any]) -> bool:
        """验证认证响应"""
        try:
            challenge = self.challenges.get(challenge_id)
            if not challenge:
                raise ValueError("挑战不存在")

            if datetime.now() > challenge.expires_at:
                raise ValueError("挑战已过期")

            # 验证认证响应
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=challenge.challenge,
                expected_origin=f"https://{self.rp_id}",
                expected_rp_id=self.rp_id,
                credential_id=self.registered_credentials.get(challenge_id),
                credential_public_key=credential.get("publicKey"),
            )

            # 标记挑战为已验证
            challenge.verified = True

            logger.info(f"[HardwareLock] ✅ 认证验证成功: {challenge.operation}")
            return True

        except Exception as e:
            logger.error(f"[HardwareLock] ❌ 认证验证失败: {e}")
            return False

    async def require_physical_auth(self, operation: str, timeout: int = 60) -> bool:
        """要求物理验证（阻塞直到验证成功或超时）"""
        try:
            # 生成认证挑战
            challenge = await self.generate_authentication_challenge(operation)

            logger.info(f"[HardwareLock] ⏳ 等待物理验证: {operation} (超时 {timeout}s)")

            # 模拟等待验证（实际应由前端调用 verify_authentication）
            start_time = datetime.now()

            while datetime.now() - start_time < timedelta(seconds=timeout):
                # 检查是否已验证
                if challenge.get("challenge_id") in self.challenges:
                    challenge_obj = self.challenges[challenge["challenge_id"]]
                    if challenge_obj.verified:
                        logger.info(f"[HardwareLock] ✅ 物理验证通过: {operation}")
                        return True

                await asyncio.sleep(0.5)

            logger.warning(f"[HardwareLock] ⏰ 物理验证超时: {operation}")
            return False

        except Exception as e:
            logger.error(f"[HardwareLock] ❌ 物理验证失败: {e}")
            return False


# 单例实例
_hardware_lock: Optional[HardwareLock] = None


def get_hardware_lock() -> HardwareLock:
    """获取硬件锁单例"""
    global _hardware_lock
    if _hardware_lock is None:
        _hardware_lock = HardwareLock()
    return _hardware_lock
