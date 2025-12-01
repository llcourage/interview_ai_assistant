#!/usr/bin/env python3
"""
启动脚本 - AI 面试助手后端服务
"""
import os
import sys
from pathlib import Path

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def check_env():
    """检查环境配置"""
    env_file = current_dir / ".env"
    
    if not env_file.exists():
        print("⚠️  未找到 .env 文件")
        print("📝 正在创建 .env 文件...")
        
        # 复制 .env.example
        example_file = current_dir / ".env.example"
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("✅ .env 文件已创建")
            print("⚠️  请编辑 .env 文件，填入你的 OPENAI_API_KEY")
            return False
        else:
            print("❌ 未找到 .env.example 文件")
            return False
    
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    # 检查是否有任何 API Key 配置（现在支持多个计划）
    openai_key = os.getenv("OPENAI_API_KEY", "")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    if not openai_key or openai_key == "your_openai_api_key_here":
        if not deepseek_key:
            print("⚠️  提示：建议至少配置一个 API Key")
            print("   - DEEPSEEK_API_KEY (Normal Plan)")
            print("   - OPENAI_API_KEY (High Plan 或 Starter Plan)")
        else:
            print("✅ DeepSeek API Key 已配置 (Normal Plan)")
            print("⚠️  OPENAI_API_KEY 未配置 (High Plan 不可用)")
    else:
        print("✅ OpenAI API Key 已配置")
    
    return True  # 允许启动，即使没有配置（用户可以选择 Starter Plan 使用自己的 Key）

def main():
    print("🚀 启动 AI 面试助手后端服务...")
    print()
    
    # 检查环境
    if not check_env():
        print()
        print("=" * 60)
        print("配置步骤：")
        print("1. 打开 backend/.env 文件")
        print("2. 将 OPENAI_API_KEY 设置为你的 API Key")
        print("3. 重新运行启动脚本")
        print("=" * 60)
        # 即使没有配置，也继续启动服务（会在调用时提示配置）
    
    # 启动服务
    import uvicorn
    from main import app
    
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print("🔥 AI 面试助手后端服务")
    print("=" * 60)
    print(f"📡 服务地址: http://{host}:{port}")
    print(f"📚 API 文档: http://{host}:{port}/docs")
    print(f"🔧 健康检查: http://{host}:{port}/health")
    print("=" * 60)
    print()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()










