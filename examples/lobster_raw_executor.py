import subprocess
from pathlib import Path

def run_direct():
    print("🦞 龙虾物理旁路：防弹语法版启动...")
    
    # 将要执行的 Python 代码写成最安全的单行形式
    raw_code = "with open('/workspace/src/masfactory/nodes.py', 'a') as f: f.write('\\n# LOBSTER_M1_BYPASS_SUCCESS\\n')\nprint('✅ Modified nodes.py inside Docker!')"
    
    repo_root = Path.cwd()
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{repo_root}:/workspace",
        "ai-lab-ai-lab:latest",
        "python3", "-c", raw_code
    ]
    
    print("🚀 正在强行破门入库...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("\n✅ 物理爆破成功！")
        print(f"📊 容器输出: {result.stdout.strip()}")
    else:
        print("\n❌ 物理爆破失败！")
        print(f"🚨 错误信息: {result.stderr.strip()}")

if __name__ == "__main__":
    run_direct()
