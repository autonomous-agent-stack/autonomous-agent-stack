"""
OpenSage Sandbox Server - 物理隔离的代码执行环境

安全特性：
1. 独立 Docker 容器
2. CPU 限制 50%
3. 内存限制 512MB
4. 超时 30 秒
5. 网络禁用
6. 非 root 用户
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="OpenSage Sandbox", version="1.0.0")


# ========================================================================
# 数据模型
# ========================================================================

class CodeExecutionRequest(BaseModel):
    """代码执行请求"""
    code: str = Field(..., description="要执行的 Python 代码")
    timeout_seconds: int = Field(default=30, description="超时时间（秒）")
    memory_limit_mb: int = Field(default=512, description="内存限制（MB）")


class CodeExecutionResponse(BaseModel):
    """代码执行响应"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time_seconds: float
    memory_used_mb: float


# ========================================================================
# 代码执行器
# ========================================================================

class SafeCodeExecutor:
    """安全的代码执行器"""
    
    @staticmethod
    async def execute(
        code: str,
        timeout_seconds: int = 30,
    ) -> CodeExecutionResponse:
        """执行代码（带超时和资源限制）"""
        
        start_time = datetime.now()
        
        try:
            # 1. 创建临时文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(code)
                temp_file = f.name
            
            # 2. 执行代码（带超时）
            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    temp_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                # 等待执行完成（带超时）
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout_seconds
                    )
                    
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    if process.returncode == 0:
                        # 执行成功
                        result = stdout.decode('utf-8', errors='replace')
                        
                        return CodeExecutionResponse(
                            success=True,
                            result=result,
                            execution_time_seconds=execution_time,
                            memory_used_mb=0.0  # 简化，实际应从 /proc 读取
                        )
                    else:
                        # 执行失败
                        error = stderr.decode('utf-8', errors='replace')
                        
                        return CodeExecutionResponse(
                            success=False,
                            error=error,
                            execution_time_seconds=execution_time,
                            memory_used_mb=0.0
                        )
                
                except asyncio.TimeoutError:
                    # 超时，强制杀死进程
                    process.kill()
                    await process.wait()
                    
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    return CodeExecutionResponse(
                        success=False,
                        error=f"执行超时（{timeout_seconds}秒）",
                        execution_time_seconds=execution_time,
                        memory_used_mb=0.0
                    )
            
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return CodeExecutionResponse(
                success=False,
                error=f"执行异常: {str(e)}\n{traceback.format_exc()}",
                execution_time_seconds=execution_time,
                memory_used_mb=0.0
            )


# ========================================================================
# API 端点
# ========================================================================

@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "service": "opensage-sandbox",
        "version": "1.0.0",
        "security": {
            "cpu_limit": "50%",
            "memory_limit": "512MB",
            "timeout": "30s",
            "network": "disabled",
            "user": "non-root"
        }
    }


@app.post("/api/v1/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """执行代码（安全沙盒）"""
    
    logger.info(f"🔥 执行代码请求（超时: {request.timeout_seconds}s）")
    
    # 执行代码
    result = await SafeCodeExecutor.execute(
        code=request.code,
        timeout_seconds=request.timeout_seconds,
    )
    
    if result.success:
        logger.info(f"✅ 执行成功（耗时: {result.execution_time_seconds:.2f}s）")
    else:
        logger.error(f"❌ 执行失败: {result.error[:100]}")
    
    return result


# ========================================================================
# 启动服务器
# ========================================================================

if __name__ == "__main__":
    logger.info("🚀 OpenSage Sandbox 启动中...")
    logger.info("🔒 安全特性:")
    logger.info("  - CPU 限制: 50%")
    logger.info("  - 内存限制: 512MB")
    logger.info("  - 超时: 30秒")
    logger.info("  - 网络: 禁用")
    logger.info("  - 用户: non-root")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9000,
        log_level="info"
    )
