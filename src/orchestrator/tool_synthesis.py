"""
工具合成模块 - Docker 沙盒执行器

负责在隔离的 Docker 环境中执行工具脚本，记录沙盒生命周期日志。
"""

import os
import json
import time
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass

from .structured_logger import get_logger


@dataclass
class DockerConfig:
    """Docker 配置"""
    image: str = "python:3.11-slim"
    network_mode: str = "none"  # 强隔离网段
    timeout_seconds: int = 30
    memory_limit: str = "512m"
    cpu_quota: int = 50000  # 50% CPU


@dataclass
class SandboxResult:
    """沙盒执行结果"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    container_id: Optional[str] = None
    error: Optional[Exception] = None


class ToolSynthesis:
    """工具合成器 - 在 Docker 沙盒中执行动态生成的脚本"""
    
    def __init__(self, config: Optional[DockerConfig] = None):
        """初始化工具合成器
        
        Args:
            config: Docker 配置
        """
        self.config = config or DockerConfig()
        self.logger = get_logger("ToolSynthesis")
        self.temp_dir = tempfile.mkdtemp(prefix="tool_synthesis_")
        
        self.logger.info(
            "docker_sandbox",
            "initialized",
            image=self.config.image,
            network_mode=self.config.network_mode,
            temp_dir=self.temp_dir
        )
    
    def execute_script(
        self,
        script_content: str,
        input_data: Any = None,
        script_name: Optional[str] = None
    ) -> SandboxResult:
        """在 Docker 沙盒中执行脚本
        
        Args:
            script_content: 脚本内容
            input_data: 输入数据（将作为 stdin）
            script_name: 脚本名称（可选）
            
        Returns:
            沙盒执行结果
        """
        if not script_name:
            script_name = f"script_{int(time.time())}.py"
        
        script_path = os.path.join(self.temp_dir, script_name)
        
        # 写入脚本文件
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        self.logger.debug(
            "docker_sandbox",
            "script_prepared",
            script_name=script_name,
            script_path=script_path
        )
        
        # 准备输入数据
        input_str = self._serialize_input(input_data)
        
        # 构建 Docker 命令
        docker_cmd = self._build_docker_command(script_name)
        
        # 执行
        return self._run_in_sandbox(
            docker_cmd,
            input_str,
            script_name
        )
    
    def _build_docker_command(self, script_name: str) -> List[str]:
        """构建 Docker 命令
        
        Args:
            script_name: 脚本名称
            
        Returns:
            Docker 命令列表
        """
        return [
            "docker", "run", "--rm",
            "-v", f"{self.temp_dir}:/workspace",
            "-w", "/workspace",
            "--network", self.config.network_mode,
            "--memory", self.config.memory_limit,
            "--cpu-quota", str(self.config.cpu_quota),
            "--stop-timeout", str(self.config.timeout_seconds),
            self.config.image,
            "python", script_name
        ]
    
    def _run_in_sandbox(
        self,
        docker_cmd: List[str],
        input_str: str,
        script_name: str
    ) -> SandboxResult:
        """在沙盒中运行命令
        
        Args:
            docker_cmd: Docker 命令
            input_str: 标准输入
            script_name: 脚本名称
            
        Returns:
            沙盒执行结果
        """
        container_id = None
        start_time = time.time()
        
        self.logger.log_docker_sandbox(
            "start",
            self.config.image,
            script_name=script_name
        )
        
        try:
            # 执行 Docker 命令
            result = subprocess.run(
                docker_cmd,
                input=input_str,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if result.returncode == 0:
                self.logger.log_docker_sandbox(
                    "execute",
                    self.config.image,
                    container_id=container_id,
                    duration_ms=duration_ms,
                    script_name=script_name,
                    stdout_length=len(result.stdout),
                    success=True
                )
                
                return SandboxResult(
                    success=True,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    duration_ms=duration_ms,
                    container_id=container_id
                )
            else:
                self.logger.error(
                    "docker_sandbox",
                    "execute_failed",
                    script_name=script_name,
                    exit_code=result.returncode,
                    duration_ms=duration_ms,
                    stderr_preview=result.stderr[:200] if result.stderr else ""
                )
                
                return SandboxResult(
                    success=False,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    duration_ms=duration_ms,
                    container_id=container_id
                )
                
        except subprocess.TimeoutExpired as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.logger.error(
                "docker_sandbox",
                "timeout",
                script_name=script_name,
                timeout_seconds=self.config.timeout_seconds,
                duration_ms=duration_ms
            )
            
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Timeout after {self.config.timeout_seconds}s",
                exit_code=-1,
                duration_ms=duration_ms,
                container_id=container_id,
                error=e
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.logger.error(
                "docker_sandbox",
                "exception",
                script_name=script_name,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=duration_ms
            )
            
            return SandboxResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration_ms=duration_ms,
                container_id=container_id,
                error=e
            )
    
    def _serialize_input(self, input_data: Any) -> str:
        """序列化输入数据
        
        Args:
            input_data: 输入数据
            
        Returns:
            序列化后的字符串
        """
        if input_data is None:
            return ""
        
        if isinstance(input_data, str):
            return input_data
        
        if isinstance(input_data, (dict, list)):
            return json.dumps(input_data, ensure_ascii=False)
        
        return str(input_data)
    
    def validate_script(
        self,
        script_content: str,
        test_data: Any = None
    ) -> bool:
        """验证脚本（在 Docker 沙盒中测试运行）
        
        Args:
            script_content: 脚本内容
            test_data: 测试数据
            
        Returns:
            是否验证通过
        """
        self.logger.info(
            "docker_sandbox",
            "validation_started",
            test_data_provided=test_data is not None
        )
        
        result = self.execute_script(
            script_content,
            input_data=test_data,
            script_name="validation_test.py"
        )
        
        if result.success:
            self.logger.info(
                "docker_sandbox",
                "validation_passed",
                duration_ms=result.duration_ms
            )
            return True
        else:
            self.logger.warning(
                "docker_sandbox",
                "validation_failed",
                exit_code=result.exit_code,
                stderr_preview=result.stderr[:200]
            )
            return False
    
    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            
            self.logger.info(
                "docker_sandbox",
                "temp_files_cleaned",
                temp_dir=self.temp_dir
            )
        except Exception as e:
            self.logger.warning(
                "docker_sandbox",
                "cleanup_failed",
                error_message=str(e)
            )
    
    def __del__(self):
        """析构函数，清理临时文件"""
        self.cleanup_temp_files()
