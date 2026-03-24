#!/usr/bin/env python3
"""
影刀 RPA CLI 工具
用于与影刀开放 API 交互

功能：
- Token 管理（获取、缓存、刷新）
- 任务管理（列表、启动、停止、查询）
- 工作队列管理
- 机器人管理
- 应用管理
- 文件操作
- 运行日志查询

使用方法：
    python yingdao_cli.py --help
    python yingdao_cli.py token get
    python yingdao_cli.py task list
    python yingdao_cli.py robot list
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import requests
from pathlib import Path


class YingdaoAPI:
    """影刀 API 客户端"""
    
    def __init__(self, access_key_id: str = None, access_key_secret: str = None, 
                 base_url: str = "https://api.yingdao.com/oapi/"):
        """
        初始化 API 客户端
        
        Args:
            access_key_id: 访问密钥 ID
            access_key_secret: 访问密钥密码
            base_url: API 基础 URL（默认公有云，专有云需要修改）
        """
        self.base_url = base_url
        self.access_key_id = access_key_id or os.getenv("YINGDAO_ACCESS_KEY_ID")
        self.access_key_secret = access_key_secret or os.getenv("YINGDAO_ACCESS_KEY_SECRET")
        self.token_cache_file = Path.home() / ".yingdao" / "token_cache.json"
        self.access_token = None
        self.token_expires_at = None
        
        if not self.access_key_id or not self.access_key_secret:
            raise ValueError(
                "缺少 API 密钥！请设置环境变量 YINGDAO_ACCESS_KEY_ID 和 YINGDAO_ACCESS_KEY_SECRET，"
                "或在初始化时传入参数。"
            )
    
    def _load_token_cache(self) -> Optional[Dict]:
        """从缓存文件加载 token"""
        if not self.token_cache_file.exists():
            return None
        
        try:
            with open(self.token_cache_file, 'r') as f:
                cache = json.load(f)
                return cache
        except Exception:
            return None
    
    def _save_token_cache(self, token: str, expires_in: int):
        """保存 token 到缓存文件"""
        self.token_cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        cache = {
            "access_token": token,
            "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(self.token_cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        获取访问令牌
        
        Args:
            force_refresh: 是否强制刷新 token
        
        Returns:
            accessToken
        """
        # 如果不强制刷新，先尝试从缓存加载
        if not force_refresh:
            # 尝试从内存缓存
            if self.access_token and self.token_expires_at:
                if datetime.now() < self.token_expires_at - timedelta(minutes=5):
                    return self.access_token
            
            # 尝试从文件缓存
            cache = self._load_token_cache()
            if cache:
                expires_at = datetime.fromisoformat(cache["expires_at"])
                if datetime.now() < expires_at - timedelta(minutes=5):
                    self.access_token = cache["access_token"]
                    self.token_expires_at = expires_at
                    return self.access_token
        
        # 从 API 获取新 token
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
                raise Exception(f"获取 token 失败: {data.get('msg', '未知错误')}")
            
            self.access_token = data["data"]["accessToken"]
            expires_in = data["data"]["expiresIn"]
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # 保存到缓存
            self._save_token_cache(self.access_token, expires_in)
            
            return self.access_token
            
        except requests.RequestException as e:
            raise Exception(f"请求失败: {str(e)}")
    
    def _call_api(self, endpoint: str, method: str = "GET", params: Dict = None, 
                  data: Dict = None) -> Dict:
        """
        调用 API 接口
        
        Args:
            endpoint: API 端点（如 "task/v2/task/list"）
            method: HTTP 方法（GET/POST/PUT/DELETE）
            params: 查询参数
            data: 请求体数据
        
        Returns:
            API 响应数据
        """
        token = self.get_access_token()
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, params=params, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=params, timeout=30)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            # 如果返回 401，尝试刷新 token 并重试
            if result.get("code") == 401:
                token = self.get_access_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {token}"
                
                if method == "GET":
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                elif method == "POST":
                    response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                
                response.raise_for_status()
                result = response.json()
            
            return result
            
        except requests.RequestException as e:
            raise Exception(f"API 调用失败: {str(e)}")
    
    # ========== 任务管理 ==========
    
    def list_tasks(self, page: int = 1, page_size: int = 20, **filters) -> Dict:
        """
        获取任务列表
        
        Args:
            page: 页码
            page_size: 每页数量
            **filters: 其他过滤条件
        """
        params = {"page": page, "pageSize": page_size}
        params.update(filters)
        return self._call_api("task/v2/task/list", params=params)
    
    def get_task(self, task_id: str) -> Dict:
        """获取任务详情"""
        return self._call_api(f"task/v2/task/{task_id}")
    
    def start_task(self, task_id: str) -> Dict:
        """启动任务"""
        return self._call_api(f"task/v2/task/{task_id}/start", method="POST")
    
    def stop_task(self, task_id: str) -> Dict:
        """停止任务"""
        return self._call_api(f"task/v2/task/{task_id}/stop", method="POST")
    
    # ========== 机器人管理 ==========
    
    def list_robots(self, page: int = 1, page_size: int = 20) -> Dict:
        """获取机器人列表"""
        params = {"page": page, "pageSize": page_size}
        return self._call_api("robot/v2/robot/list", params=params)
    
    def get_robot(self, robot_id: str) -> Dict:
        """获取机器人详情"""
        return self._call_api(f"robot/v2/robot/{robot_id}")
    
    # ========== 应用管理 ==========
    
    def list_apps(self, page: int = 1, page_size: int = 20) -> Dict:
        """获取应用列表"""
        params = {"page": page, "pageSize": page_size}
        return self._call_api("app/v2/app/list", params=params)
    
    def get_app(self, app_id: str) -> Dict:
        """获取应用详情"""
        return self._call_api(f"app/v2/app/{app_id}")
    
    # ========== 工作队列 ==========
    
    def list_work_queues(self, page: int = 1, page_size: int = 20) -> Dict:
        """获取工作队列列表"""
        params = {"page": page, "pageSize": page_size}
        return self._call_api("workqueue/v2/workqueue/list", params=params)
    
    # ========== 运行日志 ==========
    
    def list_logs(self, task_id: str = None, page: int = 1, page_size: int = 20) -> Dict:
        """获取运行日志"""
        params = {"page": page, "pageSize": page_size}
        if task_id:
            params["taskId"] = task_id
        return self._call_api("log/v2/log/list", params=params)
    
    # ========== 文件操作 ==========
    
    def list_files(self, parent_id: str = None, page: int = 1, page_size: int = 20) -> Dict:
        """获取文件列表"""
        params = {"page": page, "pageSize": page_size}
        if parent_id:
            params["parentId"] = parent_id
        return self._call_api("file/v2/file/list", params=params)


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        description="影刀 RPA CLI 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s token get              # 获取访问令牌
  %(prog)s task list              # 列出所有任务
  %(prog)s task get <task_id>     # 获取任务详情
  %(prog)s robot list             # 列出所有机器人
  %(prog)s app list               # 列出所有应用
  %(prog)s log list --task <id>   # 查询运行日志
        """
    )
    
    parser.add_argument("--access-key-id", help="访问密钥 ID")
    parser.add_argument("--access-key-secret", help="访问密钥密码")
    parser.add_argument("--base-url", help="API 基础 URL（专有云）")
    parser.add_argument("--output", "-o", choices=["json", "table"], default="json", 
                       help="输出格式（默认 json）")
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # Token 命令
    token_parser = subparsers.add_parser("token", help="Token 管理")
    token_subparsers = token_parser.add_subparsers(dest="token_command")
    token_subparsers.add_parser("get", help="获取访问令牌")
    token_subparsers.add_parser("refresh", help="刷新访问令牌")
    
    # Task 命令
    task_parser = subparsers.add_parser("task", help="任务管理")
    task_subparsers = task_parser.add_subparsers(dest="task_command")
    
    task_list = task_subparsers.add_parser("list", help="列出任务")
    task_list.add_argument("--page", type=int, default=1, help="页码")
    task_list.add_argument("--page-size", type=int, default=20, help="每页数量")
    
    task_get = task_subparsers.add_parser("get", help="获取任务详情")
    task_get.add_argument("task_id", help="任务 ID")
    
    task_start = task_subparsers.add_parser("start", help="启动任务")
    task_start.add_argument("task_id", help="任务 ID")
    
    task_stop = task_subparsers.add_parser("stop", help="停止任务")
    task_stop.add_argument("task_id", help="任务 ID")
    
    # Robot 命令
    robot_parser = subparsers.add_parser("robot", help="机器人管理")
    robot_subparsers = robot_parser.add_subparsers(dest="robot_command")
    
    robot_list = robot_subparsers.add_parser("list", help="列出机器人")
    robot_list.add_argument("--page", type=int, default=1, help="页码")
    robot_list.add_argument("--page-size", type=int, default=20, help="每页数量")
    
    robot_get = robot_subparsers.add_parser("get", help="获取机器人详情")
    robot_get.add_argument("robot_id", help="机器人 ID")
    
    # App 命令
    app_parser = subparsers.add_parser("app", help="应用管理")
    app_subparsers = app_parser.add_subparsers(dest="app_command")
    
    app_list = app_subparsers.add_parser("list", help="列出应用")
    app_list.add_argument("--page", type=int, default=1, help="页码")
    app_list.add_argument("--page-size", type=int, default=20, help="每页数量")
    
    app_get = app_subparsers.add_parser("get", help="获取应用详情")
    app_get.add_argument("app_id", help="应用 ID")
    
    # Log 命令
    log_parser = subparsers.add_parser("log", help="运行日志")
    log_subparsers = log_parser.add_subparsers(dest="log_command")
    
    log_list = log_subparsers.add_parser("list", help="列出日志")
    log_list.add_argument("--task-id", help="任务 ID")
    log_list.add_argument("--page", type=int, default=1, help="页码")
    log_list.add_argument("--page-size", type=int, default=20, help="每页数量")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # 初始化 API 客户端
        api = YingdaoAPI(
            access_key_id=args.access_key_id,
            access_key_secret=args.access_key_secret,
            base_url=args.base_url or "https://api.yingdao.com/oapi/"
        )
        
        result = None
        
        # 处理命令
        if args.command == "token":
            if args.token_command == "get":
                token = api.get_access_token()
                result = {
                    "success": True,
                    "accessToken": token,
                    "expiresAt": api.token_expires_at.isoformat() if api.token_expires_at else None
                }
            elif args.token_command == "refresh":
                token = api.get_access_token(force_refresh=True)
                result = {
                    "success": True,
                    "accessToken": token,
                    "expiresAt": api.token_expires_at.isoformat() if api.token_expires_at else None
                }
        
        elif args.command == "task":
            if args.task_command == "list":
                result = api.list_tasks(page=args.page, page_size=args.page_size)
            elif args.task_command == "get":
                result = api.get_task(args.task_id)
            elif args.task_command == "start":
                result = api.start_task(args.task_id)
            elif args.task_command == "stop":
                result = api.stop_task(args.task_id)
        
        elif args.command == "robot":
            if args.robot_command == "list":
                result = api.list_robots(page=args.page, page_size=args.page_size)
            elif args.robot_command == "get":
                result = api.get_robot(args.robot_id)
        
        elif args.command == "app":
            if args.app_command == "list":
                result = api.list_apps(page=args.page, page_size=args.page_size)
            elif args.app_command == "get":
                result = api.get_app(args.app_id)
        
        elif args.command == "log":
            if args.log_command == "list":
                result = api.list_logs(task_id=args.task_id, page=args.page, page_size=args.page_size)
        
        # 输出结果
        if result:
            if args.output == "json":
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                # TODO: 实现 table 格式输出
                print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("未知命令")
    
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
