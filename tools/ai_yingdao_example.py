#!/usr/bin/env python3
"""
AI + 影刀自动化示例

功能：
- AI 决策何时启动任务
- AI 生成动态参数
- AI 监控任务执行
- AI 处理任务结果

使用方法：
    1. 设置环境变量：
       export YINGDAO_ACCESS_KEY_ID="your_key_id"
       export YINGDAO_ACCESS_KEY_SECRET="your_key_secret"
    
    2. 配置任务 UUID：
       SCHEDULE_UUID = "your_schedule_uuid"
       ROBOT_UUID = "your_robot_uuid"
    
    3. 运行示例：
       python ai_yingdao_example.py
"""

import os
import time
import uuid
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime


class AIYingdaoAutomation:
    """AI + 影刀自动化类"""
    
    def __init__(self, access_key_id: str = None, access_key_secret: str = None):
        """
        初始化
        
        Args:
            access_key_id: 访问密钥 ID
            access_key_secret: 访问密钥密码
        """
        self.access_key_id = access_key_id or os.getenv("YINGDAO_ACCESS_KEY_ID")
        self.access_key_secret = access_key_secret or os.getenv("YINGDAO_ACCESS_KEY_SECRET")
        self.base_url = "https://api.yingdao.com/oapi/"
        self.token = None
        self.token_expires_at = None
        
        if not self.access_key_id or not self.access_key_secret:
            raise ValueError("缺少 API 密钥！请设置环境变量或传入参数")
    
    def get_token(self, force_refresh: bool = False) -> str:
        """
        获取访问令牌
        
        Args:
            force_refresh: 是否强制刷新
        
        Returns:
            accessToken
        """
        # 检查缓存的 token
        if not force_refresh and self.token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.token
        
        # 获取新 token
        url = f"{self.base_url}token/v2/token/create"
        params = {
            "accessKeyId": self.access_key_id,
            "accessKeySecret": self.access_key_secret
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise Exception(f"获取 token 失败: {data.get('msg')}")
            
            self.token = data["data"]["accessToken"]
            expires_in = data["data"]["expiresIn"]
            # 提前 5 分钟过期
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
            
            print(f"✅ 获取 token 成功，有效期 {expires_in} 秒")
            return self.token
            
        except Exception as e:
            raise Exception(f"获取 token 失败: {str(e)}")
    
    def start_task(self, schedule_uuid: str, robot_params: Dict) -> str:
        """
        AI 启动影刀任务
        
        Args:
            schedule_uuid: 任务 UUID
            robot_params: 机器人参数（AI 生成）
        
        Returns:
            task_uuid: 任务运行 UUID
        """
        token = self.get_token()
        url = f"{self.base_url}dispatch/v2/task/start"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        payload = {
            "scheduleUuid": schedule_uuid,
            "idempotentUuid": str(uuid.uuid4()),  # 幂等性
            "scheduleRelaParams": [robot_params]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise Exception(f"启动任务失败: {data.get('msg')}")
            
            task_uuid = data["data"]["taskUuid"]
            print(f"✅ 任务已启动: {task_uuid}")
            return task_uuid
            
        except Exception as e:
            raise Exception(f"启动任务失败: {str(e)}")
    
    def query_result(self, task_uuid: str, max_wait: int = 300) -> Dict:
        """
        AI 查询任务结果
        
        Args:
            task_uuid: 任务运行 UUID
            max_wait: 最大等待时间（秒）
        
        Returns:
            任务结果
        """
        token = self.get_token()
        url = f"{self.base_url}dispatch/v2/task/query"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        while True:
            payload = {"taskUuid": task_uuid}
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if not data.get("success"):
                    raise Exception(f"查询失败: {data.get('msg')}")
                
                result = data["data"]
                task_status = result["status"]
                
                print(f"⏳ 任务状态: {result['statusName']}")
                
                # 检查是否终态
                if task_status in ["finish", "failed", "canceled"]:
                    return result
                
                # 超时检查
                if time.time() - start_time > max_wait:
                    raise Exception("任务超时")
                
                # 等待 5 秒后继续轮询
                time.sleep(5)
                
            except Exception as e:
                raise Exception(f"查询失败: {str(e)}")
    
    def stop_task(self, task_uuid: str) -> Dict:
        """AI 停止任务"""
        token = self.get_token()
        url = f"{self.base_url}dispatch/v2/task/stop"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"taskUuid": task_uuid}
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 任务已停止: {task_uuid}")
            return data
            
        except Exception as e:
            raise Exception(f"停止任务失败: {str(e)}")
    
    # ========== AI 增强功能 ==========
    
    def ai_analyze_and_decide(self, context: Dict) -> Optional[Dict]:
        """
        AI 分析业务场景，决定是否启动任务
        
        Args:
            context: 业务上下文
        
        Returns:
            如果需要启动任务，返回参数；否则返回 None
        """
        # 这里用简单的规则演示
        # 实际应用中，这里可以调用大模型进行智能决策
        
        if context.get("order_count", 0) > 100:
            return {
                "robotUuid": context["robot_uuid"],
                "params": [
                    {
                        "name": "batch_size",
                        "value": "100",
                        "type": "str"
                    },
                    {
                        "name": "priority",
                        "value": "high",
                        "type": "str"
                    }
                ]
            }
        else:
            return None
    
    def ai_process_result(self, result: Dict) -> str:
        """
        AI 分析任务结果，决定下一步操作
        
        Args:
            result: 任务结果
        
        Returns:
            决策结果
        """
        if result["status"] == "finish":
            # AI 分析输出参数
            job_data = result["jobDataList"][0] if result["jobDataList"] else None
            
            if job_data:
                robot_params = job_data.get("robotParams", {})
                outputs = robot_params.get("outputs", [])
                
                # 简单示例：检查是否有输出
                if outputs:
                    return "任务完成，继续下一步"
                else:
                    return "任务完成，但无输出"
            
            return "任务完成"
        
        elif result["status"] == "failed":
            return "任务失败，需要重试或报警"
        
        else:
            return f"任务异常状态: {result['status']}"


# ========== 使用示例 ==========

def example_1_simple_automation():
    """示例 1: 简单自动化"""
    print("=" * 60)
    print("示例 1: AI + 影刀简单自动化")
    print("=" * 60)
    
    # 初始化
    automation = AIYingdaoAutomation()
    
    # AI 生成参数
    robot_params = {
        "robotUuid": "your_robot_uuid",
        "params": [
            {
                "name": "input_data",
                "value": "AI 生成的测试数据",
                "type": "str"
            }
        ]
    }
    
    # AI 启动任务
    schedule_uuid = "your_schedule_uuid"
    task_uuid = automation.start_task(schedule_uuid, robot_params)
    
    # AI 查询结果
    result = automation.query_result(task_uuid)
    
    # AI 处理结果
    decision = automation.ai_process_result(result)
    print(f"\n🤖 AI 决策: {decision}")


def example_2_ai_decision():
    """示例 2: AI 智能决策"""
    print("\n" + "=" * 60)
    print("示例 2: AI 智能决策")
    print("=" * 60)
    
    automation = AIYingdaoAutomation()
    
    # 模拟业务场景
    contexts = [
        {"order_count": 50, "robot_uuid": "robot_1"},
        {"order_count": 150, "robot_uuid": "robot_1"},
        {"order_count": 80, "robot_uuid": "robot_1"},
    ]
    
    for context in contexts:
        print(f"\n📊 业务场景: 订单数 = {context['order_count']}")
        
        # AI 决策
        params = automation.ai_analyze_and_decide(context)
        
        if params:
            print("✅ AI 决定启动任务")
            print(f"   参数: {params}")
        else:
            print("⏸️  AI 决定暂不启动任务")


def example_3_workflow():
    """示例 3: 完整工作流"""
    print("\n" + "=" * 60)
    print("示例 3: AI + 影刀完整工作流")
    print("=" * 60)
    
    automation = AIYingdaoAutomation()
    
    # Step 1: AI 分析业务数据
    print("\n📊 Step 1: AI 分析业务数据...")
    business_data = {"order_count": 120, "robot_uuid": "robot_1"}
    
    # Step 2: AI 决策
    print("\n🤖 Step 2: AI 决策...")
    params = automation.ai_analyze_and_decide(business_data)
    
    if not params:
        print("⏸️  AI 决定不启动任务")
        return
    
    # Step 3: AI 启动影刀任务
    print("\n🚀 Step 3: AI 启动影刀任务...")
    schedule_uuid = "your_schedule_uuid"
    task_uuid = automation.start_task(schedule_uuid, params)
    
    # Step 4: AI 监控任务
    print("\n⏳ Step 4: AI 监控任务...")
    result = automation.query_result(task_uuid)
    
    # Step 5: AI 处理结果
    print("\n✅ Step 5: AI 处理结果...")
    decision = automation.ai_process_result(result)
    print(f"🤖 AI 决策: {decision}")


def main():
    """主函数"""
    print("🤖 AI + 影刀自动化示例")
    print("=" * 60)
    
    try:
        # 检查环境变量
        if not os.getenv("YINGDAO_ACCESS_KEY_ID"):
            print("⚠️  未设置 YINGDAO_ACCESS_KEY_ID 环境变量")
            print("请先设置: export YINGDAO_ACCESS_KEY_ID='your_key_id'")
            return
        
        if not os.getenv("YINGDAO_ACCESS_KEY_SECRET"):
            print("⚠️  未设置 YINGDAO_ACCESS_KEY_SECRET 环境变量")
            print("请先设置: export YINGDAO_ACCESS_KEY_SECRET='your_key_secret'")
            return
        
        # 运行示例
        example_1_simple_automation()
        example_2_ai_decision()
        example_3_workflow()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
