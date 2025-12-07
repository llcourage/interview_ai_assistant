"""
Local Whisper speech-to-text service
Runs in Electron main process, no cloud dependency
"""
import sys
import json
import tempfile
import os
from pathlib import Path
from faster_whisper import WhisperModel

# Global model instance
_model = None
_model_name = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large

def get_model():
    """Get or initialize Whisper model (singleton pattern)"""
    global _model
    if _model is None:
        print(f"🤖 Loading local Whisper model: {_model_name}", file=sys.stderr)
        device = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        _model = WhisperModel(
            _model_name,
            device=device,
            compute_type=compute_type,
            download_root=None
        )
        print(f"✅ Whisper model loaded", file=sys.stderr)
    return _model

def transcribe_audio_file(audio_path: str, language: str = "zh") -> dict:
    """
    Transcribe audio file
    
    Args:
        audio_path: Audio file path
        language: Language code, default is Chinese "zh", "auto" for auto detection
        
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
        
        print(f"🎤 Starting local transcription, language: {language}", file=sys.stderr)
        
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
        
        print(f"✅ Transcription completed: {len(full_text)} characters", file=sys.stderr)
        
        return {
            "text": full_text,
            "language": info.language,
            "duration": info.duration,
            "success": True,
            "error": None
        }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Local speech-to-text failed: {error_msg}", file=sys.stderr)
        return {
            "text": "",
            "language": "",
            "duration": 0.0,
            "success": False,
            "error": error_msg
        }

if __name__ == "__main__":
    # Read from command line arguments
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Missing parameter: audio file path required"
        }))
        sys.exit(1)
    
    audio_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "zh"
    
    result = transcribe_audio_file(audio_path, language)
    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)









