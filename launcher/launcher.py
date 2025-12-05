#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launcher.exe - 启动本地后端并打开浏览器
"""
import os
import sys
import time
import subprocess
import webbrowser
import signal
import atexit
from pathlib import Path
from threading import Timer

def get_script_dir():
    """获取脚本所在目录（兼容打包后的 exe 和开发环境）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的情况：使用 sys.executable 获取实际 exe 路径
        return Path(sys.executable).parent.resolve()
    else:
        # 开发环境：使用脚本文件路径
        return Path(__file__).parent.resolve()

# 配置
BACKEND_PORT = 8000
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
# 根据平台选择后端可执行文件名
if sys.platform == 'win32':
    BACKEND_EXE = "backend.exe"
else:
    BACKEND_EXE = "backend"
UI_URL = f"http://127.0.0.1:{BACKEND_PORT}"

# 获取脚本所在目录
SCRIPT_DIR = get_script_dir()
BACKEND_EXE_PATH = SCRIPT_DIR / BACKEND_EXE

# 全局变量：后端进程
backend_process = None

def cleanup():
    """清理函数：关闭后端进程"""
    global backend_process
    if backend_process:
        try:
            print("\n正在关闭后端服务...")
            if sys.platform == 'win32':
                backend_process.terminate()
                # Windows 上需要等待一下
                time.sleep(1)
                if backend_process.poll() is None:
                    backend_process.kill()
            else:
                backend_process.terminate()
                backend_process.wait(timeout=5)
            print("✅ 后端服务已关闭")
        except Exception as e:
            print(f"⚠️ 关闭后端服务时出错: {e}")

def signal_handler(signum, frame):
    """信号处理函数"""
    cleanup()
    sys.exit(0)

def check_backend_ready(url, max_attempts=60, delay=2):
    """检查后端是否就绪"""
    import urllib.request
    import urllib.error
    
    print(f"   正在检测后端服务（最多等待 {max_attempts * delay} 秒）...")
    for i in range(max_attempts):
        try:
            req = urllib.request.Request(f"{url}/health")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    print(f"   ✅ 后端在第 {i + 1} 次检测时已就绪")
                    return True
        except (urllib.error.URLError, OSError) as e:
            # 每 10 次检测显示一次进度
            if (i + 1) % 10 == 0:
                print(f"   ⏳ 已等待 {(i + 1) * delay} 秒，继续检测...")
        time.sleep(delay)
    return False

def open_browser(url, delay=3):
    """延迟打开浏览器"""
    def _open():
        try:
            # 添加参数标识为桌面版模式
            desktop_url = f"{url}?mode=desktop&local=true"
            print(f"🌐 正在打开浏览器: {desktop_url}")
            webbrowser.open(desktop_url)
        except Exception as e:
            print(f"⚠️ 打开浏览器失败: {e}")
            print(f"请手动访问: {url}")
    
    Timer(delay, _open).start()

def main():
    global backend_process
    
    # 注册清理函数
    atexit.register(cleanup)
    if sys.platform != 'win32':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("🚀 Desktop AI - 桌面版启动器")
    print("=" * 60)
    
    # 检查 backend.exe 是否存在
    if not BACKEND_EXE_PATH.exists():
        print(f"❌ 错误: 找不到 {BACKEND_EXE_PATH}")
        print(f"   请确保 {BACKEND_EXE} 在启动器同一目录下")
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    # 启动后端
    print(f"📦 正在启动后端服务: {BACKEND_EXE_PATH}")
    print(f"   ⚠️  首次启动可能需要 30-60 秒（文件较大，需要解压）")
    try:
        # 创建日志文件路径
        log_file = SCRIPT_DIR / "backend.log"
        
        # 设置工作目录为脚本目录
        # 将输出重定向到日志文件和控制台
        with open(log_file, 'w', encoding='utf-8') as log:
            backend_process = subprocess.Popen(
                [str(BACKEND_EXE_PATH)],
                cwd=str(SCRIPT_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,  # 将 stderr 也重定向到 stdout
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
        
        print(f"✅ 后端进程已启动 (PID: {backend_process.pid})")
        print(f"   📝 日志文件: {log_file}")
        print(f"   💡 提示：如果后端退出，请查看日志文件了解原因")
    except Exception as e:
        print(f"❌ 启动后端失败: {e}")
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    # 等待后端就绪
    print(f"⏳ 等待后端服务就绪...")
    
    # 在等待期间，定期检查进程是否还在运行
    max_wait = 60  # 最多等待 60 次检测
    wait_count = 0
    while wait_count < max_wait:
        # 检查进程是否还在运行
        if backend_process.poll() is not None:
            # 进程已退出
            return_code = backend_process.returncode
            print(f"\n❌ 后端进程意外退出！")
            print(f"   退出码: {return_code}")
            print(f"   日志文件: {SCRIPT_DIR / 'backend.log'}")
            print(f"\n   请查看日志文件了解详细错误信息")
            print(f"   常见问题：")
            print(f"   1. 缺少环境变量（OPENAI_API_KEY, SUPABASE_URL 等）")
            print(f"   2. 端口 8000 被占用")
            print(f"   3. 依赖库缺失或版本不兼容")
            input("\n按 Enter 键退出...")
            sys.exit(1)
        
        # 检查后端是否就绪
        if check_backend_ready(BACKEND_URL, max_attempts=1, delay=1):
            print(f"✅ 后端服务已就绪: {BACKEND_URL}")
            break
        
        wait_count += 1
        time.sleep(2)  # 每 2 秒检查一次
    
    if wait_count >= max_wait:
        print(f"\n⚠️ 等待超时，后端可能未完全启动")
        print(f"   但继续尝试打开浏览器...")
        print(f"   如果无法访问，请查看日志文件: {SCRIPT_DIR / 'backend.log'}")
    
    # 打开浏览器
    open_browser(UI_URL)
    
    print("=" * 60)
    print("✅ 启动完成！")
    print(f"   后端地址: {BACKEND_URL}")
    print(f"   UI 地址: {UI_URL}")
    print("=" * 60)
    print("\n💡 提示:")
    print("   - 关闭此窗口将停止后端服务")
    print("   - 按 Ctrl+C 可以安全退出")
    print("=" * 60)
    
    # 保持运行，等待用户关闭
    try:
        # 监控后端进程
        while True:
            if backend_process.poll() is not None:
                print("\n⚠️ 后端进程意外退出")
                print(f"   退出码: {backend_process.returncode}")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n收到退出信号...")
    finally:
        cleanup()

if __name__ == "__main__":
    main()

