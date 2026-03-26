"""WebAuthn 前端拦截器

功能：
1. 覆写高危按钮的 onClick 事件
2. 调用 navigator.credentials.get() 触发生物识别
3. UI 约束：按钮文字变为 [ 验证身份中... ]（浅灰色）
4. 验证通过后才执行 POST 请求

使用方法：
    <button class="danger-button" data-action="merge_pr" data-uid="123456">
        批准并部署 PR
    </button>
    
    <script src="/static/webauthn-interceptor.js"></script>
"""

# ========================================================================
# JavaScript 代码（将被嵌入到 HTML 中）
# ========================================================================

WEBAUTHN_INTERCEPTOR_JS = """
// WebAuthn 前端拦截器
class WebAuthnInterceptor {
    constructor(apiBaseUrl = 'http://localhost:8000') {
        this.apiBaseUrl = apiBaseUrl;
        this.init();
    }
    
    init() {
        // 拦截所有高危按钮
        document.addEventListener('DOMContentLoaded', () => {
            this.interceptDangerousButtons();
        });
    }
    
    interceptDangerousButtons() {
        // 查找所有高危按钮
        const dangerousButtons = document.querySelectorAll('.danger-button, [data-action]');
        
        dangerousButtons.forEach(button => {
            // 保存原始 onClick 事件
            const originalOnClick = button.onclick;
            
            // 覆写 onClick 事件
            button.onclick = async (event) => {
                event.preventDefault();
                event.stopPropagation();
                
                // 获取操作类型和 UID
                const action = button.dataset.action || 'unknown';
                const uid = button.dataset.uid || 'default';
                
                try {
                    // 1. 请求挑战
                    const challenge = await this.requestChallenge(uid, action);
                    
                    // 2. 触发生物识别
                    const assertion = await this.triggerBiometric(challenge);
                    
                    // 3. 验证断言
                    const verified = await this.verifyAssertion(uid, assertion, challenge.challenge);
                    
                    if (verified) {
                        // 4. 执行原始操作
                        if (originalOnClick) {
                            originalOnClick.call(button, event);
                        }
                    }
                } catch (error) {
                    console.error('❌ 生物识别验证失败:', error);
                    this.showError(button, error.message);
                }
            };
        });
    }
    
    async requestChallenge(uid, action) {
        const response = await fetch(`${this.apiBaseUrl}/api/v1/auth/generate-challenge`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                telegram_uid: uid,
                operation: action,
            }),
        });
        
        if (!response.ok) {
            throw new Error('请求挑战失败');
        }
        
        return await response.json();
    }
    
    async triggerBiometric(challengeOptions) {
        // 更新按钮状态
        const activeButton = document.activeElement;
        const originalText = activeButton.textContent;
        activeButton.textContent = '[ 验证身份中... ]';
        activeButton.style.color = '#999';
        activeButton.disabled = true;
        
        try {
            // 调用 WebAuthn API
            const publicKey = {
                challenge: Uint8Array.from(atob(challengeOptions.challenge), c => c.charCodeAt(0)),
                timeout: challengeOptions.timeout,
                rpId: challengeOptions.rp_id,
                userVerification: challengeOptions.user_verification,
                allowCredentials: [],  // 空数组表示使用任何已注册的凭证
            };
            
            const assertion = await navigator.credentials.get({ publicKey });
            
            // 恢复按钮状态
            activeButton.textContent = originalText;
            activeButton.style.color = '';
            activeButton.disabled = false;
            
            return assertion;
        } catch (error) {
            // 恢复按钮状态
            activeButton.textContent = originalText;
            activeButton.style.color = '';
            activeButton.disabled = false;
            
            if (error.name === 'NotAllowedError') {
                throw new Error('生物识别验证被取消或失败');
            }
            throw error;
        }
    }
    
    async verifyAssertion(uid, assertion, challenge) {
        // 将 assertion 转换为可序列化的格式
        const credential = {
            id: assertion.id,
            rawId: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
            type: assertion.type,
            response: {
                clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(assertion.response.clientDataJSON))),
                authenticatorData: btoa(String.fromCharCode(...new Uint8Array(assertion.response.authenticatorData))),
                signature: btoa(String.fromCharCode(...new Uint8Array(assertion.response.signature))),
                userHandle: assertion.response.userHandle ? 
                    btoa(String.fromCharCode(...new Uint8Array(assertion.response.userHandle))) : null,
            },
        };
        
        const response = await fetch(`${this.apiBaseUrl}/api/v1/auth/verify-assertion`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                telegram_uid: uid,
                credential: credential,
                challenge: challenge,
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '验证失败');
        }
        
        const result = await response.json();
        return result.verified;
    }
    
    showError(button, message) {
        // 显示错误提示（不使用 alert）
        const originalText = button.textContent;
        button.textContent = `❌ ${message}`;
        button.style.color = '#f44336';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.color = '';
        }, 3000);
    }
}

// 初始化拦截器
const webauthnInterceptor = new WebAuthnInterceptor();
"""

# ========================================================================
# HTML 模板
# ========================================================================

WEBAUTHN_DEMO_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebAuthn 生物识别闸门演示</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        
        h1 {
            color: #2c3e50;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .danger-button {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px;
            transition: all 0.3s;
        }
        
        .danger-button:hover {
            background: #c0392b;
        }
        
        .danger-button:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
        }
        
        .info {
            background: #3498db;
            color: white;
        }
        
        .info:hover {
            background: #2980b9;
        }
        
        .warning {
            background: #f39c12;
            color: white;
        }
        
        .warning:hover {
            background: #e67e22;
        }
        
        .status {
            margin-top: 20px;
            padding: 15px;
            background: #ecf0f1;
            border-radius: 6px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <h1>🔐 WebAuthn 生物识别闸门演示</h1>
    
    <div class="card">
        <h2>高危操作（需要生物识别）</h2>
        
        <button class="danger-button" data-action="merge_pr" data-uid="123456">
            批准并部署 PR
        </button>
        
        <button class="danger-button warning" data-action="send_email" data-uid="123456">
            确认发送玛露营销信
        </button>
        
        <button class="danger-button info" data-action="kill_agent" data-uid="123456">
            强制终止 Agent
        </button>
    </div>
    
    <div class="card">
        <h2>普通操作（无需生物识别）</h2>
        
        <button onclick="alert('普通操作')">
            查看日志
        </button>
    </div>
    
    <div class="status" id="status">
        状态：等待操作...
    </div>
    
    <script>
        // 嵌入 WebAuthn 拦截器代码
        ${WEBAUTHN_INTERCEPTOR_JS}
        
        // 自定义操作处理
        document.querySelectorAll('.danger-button').forEach(button => {
            const originalOnClick = button.onclick;
            
            button.onclick = function(event) {
                // 这个 onClick 会在 WebAuthn 验证通过后被调用
                const action = this.dataset.action;
                const statusDiv = document.getElementById('status');
                
                statusDiv.innerHTML = `✅ 操作已执行：<strong>${action}</strong><br>时间：${new Date().toLocaleString()}`;
                
                // 这里执行真正的操作（如 POST 请求）
                console.log(`执行操作: ${action}`);
            };
        });
    </script>
</body>
</html>
"""

# ========================================================================
# FastAPI 端点：提供演示页面
# ========================================================================

from fastapi.responses import HTMLResponse
from fastapi import APIRouter

demo_router = APIRouter(tags=["demo"])


@demo_router.get("/webauthn-demo", response_class=HTMLResponse)
async def webauthn_demo():
    """WebAuthn 演示页面"""
    # 使用 f-string 替换 JavaScript 变量
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebAuthn 生物识别闸门演示</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }}
        
        h1 {{
            color: #2c3e50;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .danger-button {{
            background: #e74c3c;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px;
            transition: all 0.3s;
        }}
        
        .danger-button:hover {{
            background: #c0392b;
        }}
        
        .danger-button:disabled {{
            background: #bdc3c7;
            cursor: not-allowed;
        }}
        
        .info {{
            background: #3498db;
            color: white;
        }}
        
        .info:hover {{
            background: #2980b9;
        }}
        
        .warning {{
            background: #f39c12;
            color: white;
        }}
        
        .warning:hover {{
            background: #e67e22;
        }}
        
        .status {{
            margin-top: 20px;
            padding: 15px;
            background: #ecf0f1;
            border-radius: 6px;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <h1>🔐 WebAuthn 生物识别闸门演示</h1>
    
    <div class="card">
        <h2>高危操作（需要生物识别）</h2>
        
        <button class="danger-button" data-action="merge_pr" data-uid="123456">
            批准并部署 PR
        </button>
        
        <button class="danger-button warning" data-action="send_email" data-uid="123456">
            确认发送玛露营销信
        </button>
        
        <button class="danger-button info" data-action="kill_agent" data-uid="123456">
            强制终止 Agent
        </button>
    </div>
    
    <div class="card">
        <h2>普通操作（无需生物识别）</h2>
        
        <button onclick="alert('普通操作')">
            查看日志
        </button>
    </div>
    
    <div class="status" id="status">
        状态：等待操作...
    </div>
    
    <script>
        // 嵌入 WebAuthn 拦截器代码
        {WEBAUTHN_INTERCEPTOR_JS}
        
        // 自定义操作处理
        document.querySelectorAll('.danger-button').forEach(button => {{
            const originalOnClick = button.onclick;
            
            button.onclick = function(event) {{
                // 这个 onClick 会在 WebAuthn 验证通过后被调用
                const action = this.dataset.action;
                const statusDiv = document.getElementById('status');
                
                statusDiv.innerHTML = `✅ 操作已执行：<strong>${{action}}</strong><br>时间：${{new Date().toLocaleString()}}`;
                
                // 这里执行真正的操作（如 POST 请求）
                console.log(`执行操作: ${{action}}`);
            }};
        }});
    </script>
</body>
</html>
"""
    return html
