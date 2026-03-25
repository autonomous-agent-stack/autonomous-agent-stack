#!/usr/bin/env python3
"""
OpenSage 异构数据胶水层 - 动态适配器生成器

当系统捕获到 Claude CLI 或 OpenClaw 历史状态数据格式解析报错时，
自动触发生成节点动态产出 Python 清洗脚本。
"""

import os
import json
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ErrorType(Enum):
    """解析错误类型枚举"""
    JSON_DECODE_ERROR = "json_decode_error"
    MISSING_FIELD = "missing_field"
    TYPE_MISMATCH = "type_mismatch"
    ENCODING_ERROR = "encoding_error"
    APPLE_DOUBLE_FILE = "apple_double_file"
    UNKNOWN_FORMAT = "unknown_format"


@dataclass
class ParseError:
    """解析错误封装"""
    error_type: ErrorType
    raw_data: Any
    error_message: str
    sample_data: Optional[Any] = None
    context: Optional[Dict[str, Any]] = None


class AdapterRegistry:
    """适配器注册表"""
    
    def __init__(self, registry_path: str = None):
        self.registry_path = registry_path or os.path.join(
            os.path.dirname(__file__), 
            ".adapter_registry.json"
        )
        self._load_registry()
    
    def _load_registry(self):
        """加载已注册的适配器"""
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    self.adapters = json.loads(content)
                else:
                    self.adapters = {}
        else:
            self.adapters = {}
    
    def _save_registry(self):
        """保存适配器注册表"""
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.adapters, f, indent=2, ensure_ascii=False)
    
    def register(self, adapter_name: str, adapter_path: str, error_type: str, metadata: Dict = None):
        """注册新适配器"""
        self.adapters[adapter_name] = {
            "path": adapter_path,
            "error_type": error_type,
            "metadata": metadata or {},
            "created_at": os.path.getmtime(adapter_path) if os.path.exists(adapter_path) else None
        }
        self._save_registry()
    
    def get_adapter(self, error_type: str) -> Optional[str]:
        """获取指定错误类型的适配器路径"""
        for name, info in self.adapters.items():
            if info["error_type"] == error_type:
                return info["path"]
        return None
    
    def list_adapters(self) -> List[Dict]:
        """列出所有已注册适配器"""
        return [
            {"name": name, **info}
            for name, info in self.adapters.items()
        ]


class CleaningScriptGenerator:
    """清洗脚本生成器"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__),
            "generated_adapters"
        )
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate(self, error: ParseError) -> str:
        """基于错误类型生成清洗脚本"""
        
        if error.error_type == ErrorType.APPLE_DOUBLE_FILE:
            return self._generate_apple_double_filter()
        
        elif error.error_type == ErrorType.JSON_DECODE_ERROR:
            return self._generate_json_repair_script(error)
        
        elif error.error_type == ErrorType.MISSING_FIELD:
            return self._generate_field_filler_script(error)
        
        elif error.error_type == ErrorType.ENCODING_ERROR:
            return self._generate_encoding_fix_script(error)
        
        elif error.error_type == ErrorType.TYPE_MISMATCH:
            return self._generate_type_converter_script(error)
        
        else:
            return self._generate_generic_fallback_script(error)
    
    def _generate_apple_double_filter(self) -> str:
        """生成 macOS AppleDouble 文件过滤脚本"""
        return '''#!/usr/bin/env python3
"""自动生成的适配器: macOS AppleDouble 文件过滤"""

import os
import sys

def filter_apple_double(items):
    """过滤 ._ 开头的 macOS 元数据文件"""
    if isinstance(items, list):
        return [item for item in items if not str(item).startswith("._")]
    elif isinstance(items, dict):
        return {k: v for k, v in items.items() if not k.startswith("._")}
    return items

def process(input_data):
    """主处理函数"""
    return filter_apple_double(input_data)

if __name__ == "__main__":
    # 从 stdin 读取数据
    import json
    try:
        data = json.load(sys.stdin)
        result = process(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
'''
    
    def _generate_json_repair_script(self, error: ParseError) -> str:
        """生成 JSON 修复脚本"""
        sample = error.sample_data or str(error.raw_data)[:500]
        script_content = '''#!/usr/bin/env python3
"""自动生成的适配器: JSON 修复工具"""

import json
import re
import sys

def repair_json(raw_string):
    """尝试修复常见的 JSON 格式问题"""
    # 移除 BOM
    if raw_string.startswith('\\ufeff'):
        raw_string = raw_string[1:]
    
    # 移除尾部逗号
    raw_string = re.sub(r',\\s*([\\]}])', r'\\1', raw_string)
    
    # 修复单引号为双引号
    raw_string = raw_string.replace("'", '"')
    
    # 移除注释
    raw_string = re.sub(r'//.*?\\n', '\\n', raw_string)
    raw_string = re.sub(r'/\\*.*?\\*/', '', raw_string, flags=re.DOTALL)
    
    return raw_string

def process(input_data):
    """主处理函数"""
    if isinstance(input_data, str):
        try:
            return json.loads(repair_json(input_data))
        except:
            # 尝试逐行解析
            lines = input_data.strip().split('\\n')
            results = []
            for line in lines:
                if line.strip():
                    try:
                        results.append(json.loads(repair_json(line)))
                    except:
                        results.append({"raw": line})
            return results
    return input_data

if __name__ == "__main__":
    try:
        data = sys.stdin.read()
        result = process(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
'''
        return script_content
    
    def _generate_field_filler_script(self, error: ParseError) -> str:
        """生成字段填充脚本"""
        missing_fields = error.context.get("missing_fields", []) if error.context else []
        fields_str = str(missing_fields)
        script_content = f'''#!/usr/bin/env python3
"""自动生成的适配器: 缺失字段填充"""

import json
import sys
from datetime import datetime

DEFAULTS = {{
    "timestamp": lambda: datetime.now().isoformat(),
    "role": lambda: "user",
    "content": lambda: "",
    "model": lambda: "unknown",
    "id": lambda: f"msg_{{hash(datetime.now().isoformat())}}",
}}

def fill_missing_fields(data):
    """填充缺失的字段"""
    if isinstance(data, list):
        return [fill_missing_fields(item) for item in data]
    elif isinstance(data, dict):
        for field in {fields_str}:
            if field not in data or data[field] is None:
                if field in DEFAULTS:
                    data[field] = DEFAULTS[field]()
                else:
                    data[field] = None
        return data
    return data

def process(input_data):
    """主处理函数"""
    return fill_missing_fields(input_data)

if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
        result = process(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {{e}}", file=sys.stderr)
        sys.exit(1)
'''
        return script_content
    
    def _generate_encoding_fix_script(self, error: ParseError) -> str:
        """生成编码修复脚本"""
        script_content = '''#!/usr/bin/env python3
"""自动生成的适配器: 编码修复"""

import sys
import chardet

def detect_and_decode(data):
    """检测并修复编码问题"""
    if isinstance(data, bytes):
        detected = chardet.detect(data)
        encoding = detected.get('encoding', 'utf-8')
        try:
            return data.decode(encoding)
        except:
            # 尝试常见编码
            for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    return data.decode(enc)
                except:
                    continue
            return data.decode('utf-8', errors='ignore')
    return data

def process(input_data):
    """主处理函数"""
    return detect_and_decode(input_data)

if __name__ == "__main__":
    try:
        data = sys.stdin.buffer.read()
        result = process(data)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
'''
        return script_content
    
    def _generate_type_converter_script(self, error: ParseError) -> str:
        """生成类型转换脚本"""
        return '''#!/usr/bin/env python3
"""自动生成的适配器: 类型转换"""

import json
import sys
from datetime import datetime

def convert_types(data):
    """智能类型转换"""
    if isinstance(data, dict):
        return {k: convert_types(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_types(item) for item in data]
    elif isinstance(data, str):
        # 尝试转数字
        try:
            if '.' in data:
                return float(data)
            return int(data)
        except ValueError:
            pass
        # 尝试转布尔
        if data.lower() in ('true', 'yes', '1'):
            return True
        if data.lower() in ('false', 'no', '0'):
            return False
        # 尝试转时间戳
        try:
            return datetime.fromisoformat(data).isoformat()
        except:
            pass
    return data

def process(input_data):
    """主处理函数"""
    return convert_types(input_data)

if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
        result = process(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
'''
    
    def _generate_generic_fallback_script(self, error: ParseError) -> str:
        """生成通用兜底脚本"""
        error_msg = error.error_message.replace('"', '\\"')
        script_content = f'''#!/usr/bin/env python3
"""自动生成的适配器: 通用兜底处理器"""

import json
import sys

def safe_parse(data):
    """安全解析，保留原始数据"""
    try:
        if isinstance(data, str):
            return json.loads(data)
        return data
    except:
        # 返回带错误信息的结构
        return {{
            "error": "{error_msg}",
            "raw_data": str(data)[:1000],
            "type": str(type(data).__name__)
        }}

def process(input_data):
    """主处理函数"""
    return safe_parse(input_data)

if __name__ == "__main__":
    try:
        data = sys.stdin.read()
        result = process(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {{e}}", file=sys.stderr)
        sys.exit(1)
'''
        return script_content
    
    def save_script(self, script_content: str, adapter_name: str) -> str:
        """保存生成的脚本到文件"""
        script_path = os.path.join(self.output_dir, f"{adapter_name}.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)  # 可执行
        return script_path


class DockerValidator:
    """Docker 沙盒验证器"""
    
    def __init__(self, image: str = "python:3.11-slim"):
        self.image = image
        self.temp_dir = tempfile.mkdtemp()
    
    def validate(self, script_path: str, test_data: Any = None) -> bool:
        """在 Docker 沙盒中验证清洗脚本"""
        script_name = os.path.basename(script_path)
        
        # 复制脚本到临时目录
        temp_script = os.path.join(self.temp_dir, script_name)
        with open(temp_script, 'w', encoding='utf-8') as f:
            with open(script_path, 'r', encoding='utf-8') as src:
                f.write(src.read())
        
        # 准备测试数据
        test_input = json.dumps(test_data or {"test": "data"})
        
        # Docker 验证命令
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.temp_dir}:/workspace",
            "-w", "/workspace",
            "--network=none",  # 强隔离网段
            self.image,
            "python", script_name
        ]
        
        try:
            result = subprocess.run(
                docker_cmd,
                input=test_input,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✓ 脚本验证通过: {script_name}")
                print(f"  输出: {result.stdout[:200]}")
                return True
            else:
                print(f"✗ 脚本验证失败: {script_name}")
                print(f"  错误: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"✗ 脚本超时: {script_name}")
            return False
        except Exception as e:
            print(f"✗ 验证异常: {e}")
            return False
        finally:
            # 清理临时文件
            try:
                os.remove(temp_script)
            except:
                pass


class OpenSageAdapter:
    """OpenSage 适配器主入口"""
    
    def __init__(self):
        self.registry = AdapterRegistry()
        self.generator = CleaningScriptGenerator()
        self.validator = DockerValidator()
    
    def parse_external_format(self, raw_data: Any) -> Any:
        """解析外部数据格式（带自动适配）"""
        try:
            # 尝试直接解析
            if isinstance(raw_data, str):
                return json.loads(raw_data)
            return raw_data
            
        except json.JSONDecodeError as e:
            # 捕获 JSON 解析错误
            error = ParseError(
                error_type=ErrorType.JSON_DECODE_ERROR,
                raw_data=raw_data,
                error_message=str(e),
                sample_data=raw_data[:500] if len(str(raw_data)) > 500 else raw_data
            )
            return self._handle_parse_error(error)
            
        except Exception as e:
            # 未知错误
            error = ParseError(
                error_type=ErrorType.UNKNOWN_FORMAT,
                raw_data=raw_data,
                error_message=str(e),
                context={"exception_type": type(e).__name__}
            )
            return self._handle_parse_error(error)
    
    def _handle_parse_error(self, error: ParseError) -> Any:
        """处理解析错误：生成并验证适配器"""
        
        # 检查是否已有适配器
        existing_adapter = self.registry.get_adapter(error.error_type.value)
        if existing_adapter:
            print(f"使用已注册适配器: {existing_adapter}")
            return self._run_adapter(existing_adapter, error.raw_data)
        
        # 生成新适配器
        print(f"生成新适配器: {error.error_type.value}")
        script = self.generator.generate(error)
        
        # 基于错误类型哈希生成适配器名
        adapter_name = f"adapter_{error.error_type.value}_{hash(error.error_message) % 10000:04d}"
        script_path = self.generator.save_script(script, adapter_name)
        
        # 在 Docker 沙盒中验证
        if self.validator.validate(script_path, error.raw_data):
            # 注册为永久适配器
            self.registry.register(
                adapter_name=adapter_name,
                adapter_path=script_path,
                error_type=error.error_type.value,
                metadata={"error_message": error.error_message}
            )
            print(f"✓ 适配器已注册: {adapter_name}")
            
            # 运行清洗后的数据
            return self._run_adapter(script_path, error.raw_data)
        else:
            print(f"✗ 适配器验证失败，返回原始数据")
            return error.raw_data
    
    def _run_adapter(self, adapter_path: str, raw_data: Any) -> Any:
        """运行适配器处理数据"""
        try:
            result = subprocess.run(
                ["python", adapter_path],
                input=json.dumps(raw_data) if not isinstance(raw_data, str) else raw_data,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"适配器运行失败: {result.stderr}")
                return raw_data
                
        except Exception as e:
            print(f"适配器异常: {e}")
            return raw_data
    
    def list_adapters(self) -> List[Dict]:
        """列出所有已注册适配器"""
        return self.registry.list_adapters()


# CLI 接口
def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenSage 异构数据胶水层")
    parser.add_argument("file", help="要解析的数据文件")
    parser.add_argument("--list-adapters", action="store_true", help="列出已注册适配器")
    
    args = parser.parse_args()
    
    adapter = OpenSageAdapter()
    
    if args.list_adapters:
        print("已注册适配器:")
        for info in adapter.list_adapters():
            print(f"  - {info['name']}: {info['path']}")
        return
    
    # 读取并解析文件
    with open(args.file, 'r', encoding='utf-8') as f:
        raw_data = f.read()
    
    result = adapter.parse_external_format(raw_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
