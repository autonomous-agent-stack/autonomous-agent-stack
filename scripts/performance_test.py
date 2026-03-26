#!/usr/bin/env python3
"""API 性能测试脚本"""
import asyncio
import aiohttp
import time
from statistics import mean, median

API_BASE = "http://127.0.0.1:8000"

async def test_endpoint(session, endpoint, iterations=10):
    """测试单个端点的性能"""
    times = []
    
    for _ in range(iterations):
        start = time.time()
        try:
            async with session.get(f"{API_BASE}{endpoint}") as resp:
                await resp.text()
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
    
    if times:
        return {
            "endpoint": endpoint,
            "iterations": iterations,
            "avg": mean(times),
            "median": median(times),
            "min": min(times),
            "max": max(times)
        }
    return None

async def main():
    """运行性能测试"""
    endpoints = [
        "/api/v1/system/health",
        "/api/v1/admin/health",
        "/docs",
        "/openapi.json"
    ]
    
    print("🚀 开始性能测试...\n")
    
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *[test_endpoint(session, ep) for ep in endpoints]
        )
    
    # 输出结果
    print("=" * 80)
    print(f"{'端点':<40} {'平均':<10} {'中位数':<10} {'最小':<10} {'最大':<10}")
    print("=" * 80)
    
    for result in results:
        if result:
            print(
                f"{result['endpoint']:<40} "
                f"{result['avg']:>8.2f}ms "
                f"{result['median']:>8.2f}ms "
                f"{result['min']:>8.2f}ms "
                f"{result['max']:>8.2f}ms"
            )
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
