"""WebAuthn 生物识别认证路由器 (简化版)

功能：
1. 生成挑战（challenge）
2. 验证生物识别签名（assertion）
3. 模拟模式（无需 webauthn 库）
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/auth", tags=["webauthn"])

# 配置
RP_ID = os.getenv("WEBAUTHN_RP_ID", "localhost")
DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "webauthn.db"


# 数据模型
class ChallengeRequest(BaseModel):
    telegram_uid: str
    operation: str


class ChallengeResponse(BaseModel):
    challenge: str
    timeout: int
    rp_id: str


class AssertionRequest(BaseModel):
    telegram_uid: str
    credential: Dict[str, Any]
    challenge: str


# 数据库管理
class WebAuthnDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                challenge TEXT PRIMARY KEY,
                telegram_uid TEXT NOT NULL,
                operation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    
    def save_challenge(self, challenge: str, telegram_uid: str, operation: str, expires_in_seconds: int = 60):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=expires_in_seconds)
        cursor.execute("""
            INSERT INTO challenges (challenge, telegram_uid, operation, created_at, expires_at, used)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (challenge, telegram_uid, operation, now.isoformat(), expires_at.isoformat()))
        conn.commit()
        conn.close()
    
    def get_challenge(self, challenge: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT telegram_uid, operation, created_at, expires_at, used
            FROM challenges WHERE challenge = ?
        """, (challenge,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "telegram_uid": row[0],
                "operation": row[1],
                "created_at": row[2],
                "expires_at": row[3],
                "used": bool(row[4]),
            }
        return None
    
    def mark_challenge_used(self, challenge: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE challenges SET used = 1 WHERE challenge = ?", (challenge,))
        conn.commit()
        conn.close()


db = WebAuthnDB()


# API 端点
@router.post("/generate-challenge", response_model=ChallengeResponse)
async def generate_challenge(request: ChallengeRequest):
    challenge = secrets.token_urlsafe(32)
    db.save_challenge(challenge, request.telegram_uid, request.operation, 60)
    
    return ChallengeResponse(
        challenge=challenge,
        timeout=60000,
        rp_id=RP_ID,
    )


@router.post("/verify-assertion")
async def verify_assertion(request: AssertionRequest):
    challenge_data = db.get_challenge(request.challenge)
    
    if not challenge_data:
        raise HTTPException(status_code=401, detail="Biometric required: Invalid or expired challenge")
    
    if challenge_data["used"]:
        raise HTTPException(status_code=401, detail="Biometric required: Challenge already used")
    
    expires_at = datetime.fromisoformat(challenge_data["expires_at"])
    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=401, detail="Biometric required: Challenge expired")
    
    if challenge_data["telegram_uid"] != request.telegram_uid:
        raise HTTPException(status_code=401, detail="Biometric required: UID mismatch")
    
    # 模拟验证（生产环境应该使用 webauthn 库）
    db.mark_challenge_used(request.challenge)
    
    return {"verified": True, "message": "Biometric authentication successful (mock)"}


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "rp_id": RP_ID}
