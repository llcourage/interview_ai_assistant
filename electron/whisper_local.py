"""
本地 Whisper 语音转文字服务
在 Electron 主进程中运行，不依赖云端
"""
import sys
import json
import tempfile
import os
from pathlib import Path
from faster_whisper import WhisperModel

# 全局模型实例
_model = None
_model_name = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large

def get_model():
    """获取或初始化 Whisper 模型（单例模式）"""
    global _model
    if _model is None:
        print(f"🤖 加载本地 Whisper 模型: {_model_name}", file=sys.stderr)
        device = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        _model = WhisperModel(
            _model_name,
            device=device,
            compute_type=compute_type,
            download_root=None
        )
        print(f"✅ Whisper 模型加载完成", file=sys.stderr)
    return _model

def transcribe_audio_file(audio_path: str, language: str = "zh") -> dict:
    """
    转写音频文件
    
    Args:
        audio_path: 音频文件路径
        language: 语言代码，默认为中文 "zh"，"auto" 为自动检测
        
    Returns:
        dict: {
            "text": str,
            "language": str,
            "duration": float,
            "success": bool,
            "error": str
        }
    """
    try:
        model = get_model()
        
        print(f"🎤 开始本地转写音频，语言: {language}", file=sys.stderr)
        
        segments, info = model.transcribe(
            audio_path,
            language=None if language == "auto" else language,
            beam_size=5,
            vad_filter=True,
        )
        
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text)
        
        full_text = " ".join(text_parts).strip()
        
        print(f"✅ 转写完成: {len(full_text)} 字符", file=sys.stderr)
        
        return {
            "text": full_text,
            "language": info.language,
            "duration": info.duration,
            "success": True,
            "error": None
        }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 本地语音转文字失败: {error_msg}", file=sys.stderr)
        return {
            "text": "",
            "language": "",
            "duration": 0.0,
            "success": False,
            "error": error_msg
        }

if __name__ == "__main__":
    # 从命令行参数读取
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "缺少参数: 需要音频文件路径"
        }))
        sys.exit(1)
    
    audio_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "zh"
    
    result = transcribe_audio_file(audio_path, language)
    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)









