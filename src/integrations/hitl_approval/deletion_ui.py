"""浅色面板高危拦截 UI（硬删除）

功能：
1. 硬删除任务挂起并推送到看板
2. 极简浅色背景，黑色/深灰色粗体字
3. [🗑️ 确认清理] 按钮强制唤起 WebAuthn 生物核验
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Any

from fastapi.responses import HTMLResponse


@dataclass
class DeletionTask:
    """删除任务"""
    task_id: str
    resource_type: str  # "google_event" or "drive_file"
    resource_name: str
    resource_id: str
    status: str  # "pending" or "approved" or "rejected"


class DeletionConfirmationUI:
    """删除确认 UI 管理器"""
    
    @staticmethod
    def generate_confirmation_card(
        tasks: List[DeletionTask],
        api_base_url: str = "https://patient-constructed-sake-gsm.trycloudflare.com",
    ) -> str:
        """生成极简删除确认卡片
        
        Args:
            tasks: 删除任务列表
            api_base_url: API 基础 URL
            
        Returns:
            HTML 字符串
        """
        # 构建任务列表
        task_items = []
        for task in tasks:
            task_items.append(f"""
                <div style="margin-bottom: 16px; padding: 12px; background: #f8f9fa; border-radius: 6px;">
                    <div style="font-weight: 600; color: #212529; margin-bottom: 4px;">
                        准备删除: {task.resource_type} [{task.resource_name}]
                    </div>
                    <div style="font-size: 12px; color: #6c757d;">
                        ID: {task.resource_id}
                    </div>
                </div>
            """)
        
        tasks_html = "\n".join(task_items)
        
        # 生成 HTML
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>删除确认</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #ffffff;
            color: #212529;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        h1 {{
            font-size: 24px;
            font-weight: 700;
            color: #212529;
            margin-bottom: 24px;
        }}
        
        .warning {{
            background: #f8f9fa;
            border-left: 4px solid #6c757d;
            padding: 16px;
            margin-bottom: 24px;
        }}
        
        .tasks {{
            margin-bottom: 24px;
        }}
        
        .button {{
            background: #212529;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin-right: 12px;
        }}
        
        .button:hover {{
            background: #495057;
        }}
        
        .button:disabled {{
            background: #adb5bd;
            cursor: not-allowed;
        }}
        
        .cancel {{
            background: #f8f9fa;
            color: #212529;
            border: 1px solid #dee2e6;
        }}
        
        .cancel:hover {{
            background: #e9ecef;
        }}
    </style>
</head>
<body>
    <h1>🗑️ 删除确认</h1>
    
    <div class="warning">
        <strong>警告：</strong>以下资源将被永久删除。此操作不可撤销。
    </div>
    
    <div class="tasks">
        {tasks_html}
    </div>
    
    <div style="display: flex; gap: 12px;">
        <button class="button" id="confirmBtn" onclick="confirmDeletion()">
            🗑️ 确认清理
        </button>
        <button class="button cancel" onclick="cancelDeletion()">
            取消
        </button>
    </div>
    
    <script>
        async function confirmDeletion() {{
            const btn = document.getElementById('confirmBtn');
            btn.disabled = true;
            btn.textContent = '[ 身份核验中... ]';
            btn.style.background = '#adb5bd';
            
            try {{
                // 1. 请求挑战
                const challengeResponse = await fetch('{api_base_url}/api/v1/auth/generate-challenge', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        telegram_uid: 'current_user',
                        operation: 'confirm_deletion',
                    }}),
                }});
                
                if (!challengeResponse.ok) {{
                    throw new Error('请求挑战失败');
                }}
                
                const {{ challenge }} = await challengeResponse.json();
                
                // 2. 触发生物识别
                const publicKey = {{
                    challenge: Uint8Array.from(atob(challenge), c => c.charCodeAt(0)),
                    timeout: 60000,
                    rpId: 'localhost',
                    userVerification: 'required',
                    allowCredentials: [],
                }};
                
                const assertion = await navigator.credentials.get({{ publicKey }});
                
                if (!assertion) {{
                    throw new Error('生物识别验证被取消');
                }}
                
                // 3. 验证断言
                const credential = {{
                    id: assertion.id,
                    rawId: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
                    type: assertion.type,
                    response: {{
                        clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(assertion.response.clientDataJSON))),
                        authenticatorData: btoa(String.fromCharCode(...new Uint8Array(assertion.response.authenticatorData))),
                        signature: btoa(String.fromCharCode(...new Uint8Array(assertion.response.signature))),
                    }},
                }};
                
                const verifyResponse = await fetch('{api_base_url}/api/v1/auth/verify-assertion', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        telegram_uid: 'current_user',
                        credential: credential,
                        challenge: challenge,
                    }}),
                }});
                
                if (!verifyResponse.ok) {{
                    const errorData = await verifyResponse.json();
                    throw new Error(errorData.detail || '验证失败');
                }}
                
                const {{ verified }} = await verifyResponse.json();
                
                if (verified) {{
                    // 4. 执行删除
                    btn.textContent = '✅ 已确认';
                    btn.style.background = '#28a745';
                    
                    // TODO: 调用删除 API
                    setTimeout(() => {{
                        alert('删除操作已提交');
                        window.close();
                    }}, 1000);
                }}
            }} catch (error) {{
                console.error('❌ 验证失败:', error);
                btn.disabled = false;
                btn.textContent = '🗑️ 确认清理';
                btn.style.background = '#212529';
                alert('验证失败: ' + error.message);
            }}
        }}
        
        function cancelDeletion() {{
            window.close();
        }}
    </script>
</body>
</html>
"""
        
        return html


# 全局实例
deletion_ui = DeletionConfirmationUI()


# ========================================================================
# FastAPI 端点
# ========================================================================

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/deletion", tags=["deletion"])


@router.get("/confirm", response_class=HTMLResponse)
async def show_deletion_confirmation(request: Request):
    """显示删除确认页面"""
    tasks = _load_tasks_from_request(request)
    
    return deletion_ui.generate_confirmation_card(tasks)


def _load_tasks_from_request(request: Request) -> List[DeletionTask]:
    """从查询参数或数据库加载删除任务."""
    tasks_param = request.query_params.get("tasks", "").strip()
    if tasks_param:
        try:
            payload = json.loads(tasks_param)
            return _normalize_tasks(payload)
        except json.JSONDecodeError:
            pass

    task_ids = request.query_params.get("task_ids", "").strip()
    if task_ids:
        ids = [item.strip() for item in task_ids.split(",") if item.strip()]
        tasks_from_db = _load_tasks_from_db(ids)
        if tasks_from_db:
            return tasks_from_db

    db_fallback = _load_tasks_from_db([])
    if db_fallback:
        return db_fallback

    return [
        DeletionTask(
            task_id="1",
            resource_type="google_event",
            resource_name="无效分销商会议",
            resource_id="event_123",
            status="pending",
        ),
        DeletionTask(
            task_id="2",
            resource_type="drive_file",
            resource_name="玛露测试文档.pdf",
            resource_id="file_456",
            status="pending",
        ),
    ]


def _normalize_tasks(payload: Any) -> List[DeletionTask]:
    if isinstance(payload, dict):
        payload = payload.get("tasks", [])
    if not isinstance(payload, list):
        return []

    tasks: List[DeletionTask] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            tasks.append(
                DeletionTask(
                    task_id=str(item.get("task_id", "")),
                    resource_type=str(item.get("resource_type", "")),
                    resource_name=str(item.get("resource_name", "")),
                    resource_id=str(item.get("resource_id", "")),
                    status=str(item.get("status", "pending")),
                )
            )
        except Exception:
            continue
    return tasks


def _load_tasks_from_db(task_ids: List[str]) -> List[DeletionTask]:
    db_path = os.getenv("DELETION_UI_DB_PATH", "data/deletion_tasks.db")
    if not os.path.exists(db_path):
        return []

    query = """
        SELECT task_id, resource_type, resource_name, resource_id, status
        FROM deletion_tasks
    """
    params: List[Any] = []
    if task_ids:
        placeholders = ",".join("?" for _ in task_ids)
        query += f" WHERE task_id IN ({placeholders})"
        params.extend(task_ids)
    query += " ORDER BY task_id ASC LIMIT 100"

    tasks: List[DeletionTask] = []
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row in cursor.fetchall():
                tasks.append(
                    DeletionTask(
                        task_id=str(row[0]),
                        resource_type=str(row[1]),
                        resource_name=str(row[2]),
                        resource_id=str(row[3]),
                        status=str(row[4]),
                    )
                )
    except sqlite3.Error:
        return []
    return tasks
