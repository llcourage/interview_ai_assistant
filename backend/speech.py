"""
语音转文字模块 - 使用 faster-whisper
"""
from faster_whisper import WhisperModel
import os
import tempfile
from pathlib import Path

# 全局模型实例（延迟加载）
_model = None
_model_name = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large

def get_model():
    """获取或初始化 Whisper 模型（单例模式）"""
    global _model
    if _model is None:
        print(f"🤖 加载 Whisper 模型: {_model_name} (首次运行会下载模型)")
        # device: "cpu" 或 "cuda" (如果有 GPU)
        # compute_type: "int8", "int8_float16", "float16", "float32"
        device = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        _model = WhisperModel(
            _model_name,
            device=device,
            compute_type=compute_type,
            download_root=None  # 使用默认缓存目录
        )
        print(f"✅ Whisper 模型加载完成")
    return _model

async def transcribe_audio(audio_data: bytes, language: str = "zh") -> dict:
    """
    将音频数据转换为文字
    
    Args:
        audio_data: 音频文件的二进制数据
        language: 语言代码，默认为中文 "zh"，"auto" 为自动检测
        
    Returns:
        dict: {
            "text": str,  # 完整文本
            "segments": list,  # 分段信息
            "language": str,  # 检测到的语言
            "duration": float  # 音频时长（秒）
        }
    """
    try:
        # 获取模型
        model = get_model()
        
        # 将音频数据保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_path = tmp_file.name
        
        try:
            # 转写音频
            print(f"🎤 开始转写音频，语言: {language}")
            
            # 如果 language 是 "auto"，则自动检测
            segments, info = model.transcribe(
                tmp_path,
                language=None if language == "auto" else language,
                beam_size=5,
                vad_filter=True,  # 启用语音活动检测，过滤静音
            )
            
            # 收集所有文本片段
            text_parts = []
            segments_list = []
            
            for segment in segments:
                text_parts.append(segment.text)
                segments_list.append({
                    "text": segment.text,
                    "start": segment.start,
                    "end": segment.end,
                })
            
            full_text = " ".join(text_parts).strip()
            
            print(f"✅ 转写完成: {len(full_text)} 字符, 语言: {info.language}, 时长: {info.duration:.2f}秒")
            
            return {
                "text": full_text,
                "segments": segments_list,
                "language": info.language,
                "duration": info.duration,
            }
            
        finally:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except:
                pass
                
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 语音转文字失败: {error_msg}")
        raise Exception(f"语音转文字失败: {error_msg}")


