#!/usr/bin/env python3
"""
NotebookLM PPT 自动处理脚本

功能：
1. 监控下载文件夹
2. 自动检测新 PPT
3. 去除水印
4. 保存到指定位置

使用方法：
    # 单次处理
    python tools/notebooklm_auto_processor.py --once input.pptx
    
    # 监控模式
    python tools/notebooklm_auto_processor.py --monitor
    
    # 批量处理
    python tools/notebooklm_auto_processor.py --batch ./folder/
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# 导入去水印脚本
try:
    from remove_ppt_watermark import process_pptx, is_watermark_shape
except ImportError:
    print("错误: 找不到 remove_ppt_watermark.py")
    print("请确保该文件在同一目录下")
    sys.exit(1)


def process_single_file(input_path: str, output_path: str = None, verbose: bool = True) -> dict:
    """
    处理单个 PPT 文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径（可选）
        verbose: 是否显示详细信息
    
    Returns:
        处理结果
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        return {"success": False, "error": "文件不存在"}
    
    if not input_file.suffix.lower() == '.pptx':
        return {"success": False, "error": "不是 PPTX 文件"}
    
    # 生成输出路径
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(input_file.parent / f"{input_file.stem}_cleaned_{timestamp}.pptx")
    
    if verbose:
        print(f"📝 处理文件: {input_file.name}")
        print(f"💾 输出至: {output_path}")
    
    # 调用去水印函数
    result = process_pptx(str(input_file), output_path, verbose=verbose)
    
    return result


def batch_process(input_dir: str, output_dir: str = None, verbose: bool = True) -> list:
    """
    批量处理文件夹中的 PPT
    
    Args:
        input_dir: 输入文件夹
        output_dir: 输出文件夹（可选）
        verbose: 是否显示详细信息
    
    Returns:
        处理结果列表
    """
    input_folder = Path(input_dir)
    
    if not input_folder.exists():
        print(f"❌ 文件夹不存在: {input_dir}")
        return []
    
    # 创建输出文件夹
    if output_dir is None:
        output_dir = input_folder / "cleaned"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找所有 PPTX 文件
    pptx_files = list(input_folder.glob("*.pptx"))
    
    # 排除已处理的文件
    pptx_files = [f for f in pptx_files if "_cleaned" not in f.name]
    
    if not pptx_files:
        print(f"❌ 未找到 PPTX 文件: {input_dir}")
        return []
    
    print(f"🔍 找到 {len(pptx_files)} 个 PPTX 文件")
    print("=" * 60)
    
    results = []
    
    for i, pptx_file in enumerate(pptx_files, 1):
        print(f"\n[{i}/{len(pptx_files)}] 处理: {pptx_file.name}")
        
        output_path = output_dir / f"{pptx_file.stem}_cleaned.pptx"
        result = process_single_file(str(pptx_file), str(output_path), verbose=verbose)
        
        results.append({
            "input": str(pptx_file),
            "output": str(output_path),
            "result": result
        })
    
    print("\n" + "=" * 60)
    print(f"✅ 批量处理完成！处理了 {len(results)} 个文件")
    
    return results


def monitor_mode(watch_dir: str = None, output_dir: str = None):
    """
    监控模式：自动检测并处理新下载的 PPT
    
    Args:
        watch_dir: 监控目录（默认为下载文件夹）
        output_dir: 输出目录
    """
    # 尝试导入 watchdog
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("❌ 缺少 watchdog 库")
        print("请安装: pip install watchdog")
        sys.exit(1)
    
    # 设置监控目录
    if watch_dir is None:
        # 尝试自动检测下载文件夹
        possible_dirs = [
            Path.home() / "Downloads",
            Path.home() / "下载",
        ]
        
        for d in possible_dirs:
            if d.exists():
                watch_dir = str(d)
                break
        
        if watch_dir is None:
            print("❌ 未找到下载文件夹，请手动指定 --watch-dir")
            sys.exit(1)
    
    # 设置输出目录
    if output_dir is None:
        output_dir = Path(watch_dir) / "cleaned"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建事件处理器
    class PPTHandler(FileSystemEventHandler):
        def __init__(self, output_dir):
            self.output_dir = output_dir
        
        def on_created(self, event):
            if event.is_directory:
                return
            
            if not event.src_path.endswith('.pptx'):
                return
            
            # 排除已处理的文件
            if "_cleaned" in event.src_path:
                return
            
            print(f"\n🔔 检测到新 PPT: {Path(event.src_path).name}")
            
            # 等待文件完全下载
            time.sleep(3)
            
            # 检查文件是否可访问
            try:
                with open(event.src_path, 'rb') as f:
                    pass
            except IOError:
                print("⚠️  文件仍在下载中，等待...")
                time.sleep(5)
            
            # 处理文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"{Path(event.src_path).stem}_cleaned_{timestamp}.pptx"
            
            print(f"⚙️  正在处理...")
            result = process_single_file(event.src_path, str(output_path), verbose=False)
            
            if result:
                print(f"✅ 完成！保存至: {output_path}")
                if "watermarks_removed" in result:
                    print(f"   删除了 {result['watermarks_removed']} 个水印")
            else:
                print(f"❌ 处理失败")
    
    # 启动监控
    event_handler = PPTHandler(output_dir)
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=False)
    observer.start()
    
    print("=" * 60)
    print("🔍 NotebookLM PPT 自动处理器")
    print("=" * 60)
    print(f"📁 监控目录: {watch_dir}")
    print(f"📁 输出目录: {output_dir}")
    print("\n💡 提示:")
    print("   1. 在 NotebookLM 中生成 PPT")
    print("   2. 下载到监控目录")
    print("   3. 脚本会自动检测并去除水印")
    print("\n按 Ctrl+C 停止监控...")
    print("=" * 60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  停止监控")
        observer.stop()
    
    observer.join()


def main():
    parser = argparse.ArgumentParser(
        description="NotebookLM PPT 自动处理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单次处理
  python notebooklm_auto_processor.py --once input.pptx
  python notebooklm_auto_processor.py --once input.pptx --output cleaned.pptx

  # 批量处理
  python notebooklm_auto_processor.py --batch ./folder/
  python notebooklm_auto_processor.py --batch ./folder/ --output ./cleaned/

  # 监控模式
  python notebooklm_auto_processor.py --monitor
  python notebooklm_auto_processor.py --monitor --watch-dir ~/Downloads
        """
    )
    
    # 互斥组：选择处理模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--once", metavar="FILE", help="单次处理模式")
    mode_group.add_argument("--batch", metavar="DIR", help="批量处理模式")
    mode_group.add_argument("--monitor", action="store_true", help="监控模式")
    
    # 输出选项
    parser.add_argument("--output", "-o", help="输出路径（文件或文件夹）")
    parser.add_argument("--watch-dir", help="监控目录（监控模式）")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    # 单次处理模式
    if args.once:
        result = process_single_file(args.once, args.output, verbose=verbose)
        
        if not result:
            sys.exit(1)
        
        if verbose:
            print("\n✅ 处理完成！")
    
    # 批量处理模式
    elif args.batch:
        results = batch_process(args.batch, args.output, verbose=verbose)
        
        if not results:
            sys.exit(1)
    
    # 监控模式
    elif args.monitor:
        monitor_mode(args.watch_dir, args.output)


if __name__ == "__main__":
    main()
