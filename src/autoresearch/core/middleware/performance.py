"""
性能监控中间件
记录请求响应时间和性能指标
"""
import time
from fastapi import Request, Response
from typing import Callable
import logging

logger = logging.getLogger(__name__)

async def performance_middleware(request: Request, call_next: Callable) -> Response:
    """
    性能监控中间件
    记录每个请求的处理时间
    """
    start_time = time.time()
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = (time.time() - start_time) * 1000  # 毫秒
    
    # 添加到响应头
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    # 记录慢请求（>1秒）
    if process_time > 1000:
        logger.warning(
            f"慢请求: {request.method} {request.url.path} "
            f"耗时 {process_time:.2f}ms"
        )
    
    # 记录到访问日志
    logger.info(
        f"{request.method} {request.url.path} "
        f"- {response.status_code} "
        f"- {process_time:.2f}ms"
    )
    
    return response
