import os
import base64
from io import BytesIO
from PIL import Image
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# ⚠️ No longer initialize client at module level, changed to receive dynamic client in function

async def analyze_image(image_base64: str | list[str], prompt: str = None, client: AsyncOpenAI = None, model: str = None) -> tuple[str, dict]:
    """
    Use OpenAI Vision API to analyze images (supports multiple images)
    
    Args:
        image_base64: Base64 encoded image or image list
        prompt: Analysis prompt (optional)
        client: OpenAI client (must be provided)
        model: Model name (optional, if not provided use environment variable or default)
        
    Returns:
        str: AI analysis result
    """
    try:
        # 🔑 Client must be provided
        if client is None:
            raise ValueError("Client must be provided")
        
        api_client = client
        # Default prompt - Structured interview question format
        if not prompt:
            prompt = """Please carefully read the problem in the screenshot.

Please strictly follow these 5 sections in your response, without any extra descriptions:

1) Problem Explanation (Brief)
Briefly summarize the problem requirements. Be concise.

2) Clarification Questions
List 3-5 key clarifying questions about the problem details (e.g., edge cases, input constraints, exceptions). Keep them brief.

3) Approach
Explain the optimal solution step by step, clearly and concisely.

4) Code
```python
# Provide complete Python code here with key comments
```

5) Explanation
Briefly explain the key logic of the code, including time/space complexity analysis.

⚠️ Prohibited:
- Do not write "Problem Description", "Examples", "Constraints" sections.
- Do not write phrases like "This image shows..." or other unnecessary text.
- Keep the response professional and concise."""

        # Get model name (prioritize passed model, then environment variable, finally default)
        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # Convert single image to list
        if isinstance(image_base64, str):
            image_list = [image_base64]
        else:
            image_list = image_base64
        
        print(f"🤖 Calling model: {model}")
        print(f"📸 Number of images: {len(image_list)}")
        print(f"📝 Prompt: {prompt[:100]}...")
        
        # 🔍 Debug: check image data
        for idx, img_base64 in enumerate(image_list):
            print(f"📷 Image {idx + 1} data length: {len(img_base64)} characters")
            print(f"📷 Image {idx + 1} first 50 characters: {img_base64[:50]}")
        
        # Build content array
        content = [{"type": "text", "text": prompt}]
        
        # Add all images
        for img_base64 in image_list:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}",
                    "detail": "high"
                }
            })
        
        # Call OpenAI Vision API
        response = await api_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=3000,
            temperature=0.3
        )
        
        # Extract reply
        answer = response.choices[0].message.content
        
        # Extract token usage
        token_usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        print(f"✅ Analysis completed, reply length: {len(answer)} characters")
        print(f"📊 Token usage: {token_usage['total_tokens']} (input: {token_usage['input_tokens']}, output: {token_usage['output_tokens']})")
        
        return answer, token_usage
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Vision analysis failed: {error_msg}")
        
        # Return friendly error message
        error_message = ""
        if "api_key" in error_msg.lower() or "invalid api key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_message = "❌ API Key error. "
            # Check if in Vercel environment (multiple detection methods)
            import os
            is_vercel = os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("NOW_REGION")
            
            if is_vercel:
                error_message += "\n\nPlease check in Vercel Dashboard:"
                error_message += "\n1. Go to Settings -> Environment Variables"
                error_message += "\n2. Confirm OPENAI_API_KEY is configured"
                error_message += "\n3. Ensure API Key value is correct (starts with 'sk-')"
                error_message += "\n4. Need to redeploy application after adding"
            else:
                error_message += "\n\nPlease check:"
                error_message += "\n1. Local environment: Check OPENAI_API_KEY in backend/.env file"
                error_message += "\n2. Vercel environment: Check Vercel Dashboard -> Settings -> Environment Variables"
                error_message += "\n3. Ensure API Key starts with 'sk-' and is complete"
            error_message += "\n\nIf the problem persists, please check server logs for more information."
        elif "rate_limit" in error_msg.lower():
            error_message = "❌ API call rate limit exceeded, please try again later"
        elif "insufficient_quota" in error_msg.lower():
            error_message = "❌ API quota insufficient, please check your OpenAI account balance"
        else:
            error_message = f"❌ Analysis failed: {error_msg}"
        
        return error_message, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def validate_image_base64(image_base64: str) -> bool:
    """
    Validate if Base64 image is valid
    
    Args:
        image_base64: Base64 encoded image
        
    Returns:
        bool: Whether valid
    """
    try:
        # Decode base64
        image_data = base64.b64decode(image_base64)
        
        # Try to open image
        image = Image.open(BytesIO(image_data))
        
        # Check image format
        if image.format not in ['PNG', 'JPEG', 'JPG', 'GIF', 'WEBP']:
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Image validation failed: {e}")
        return False


async def analyze_image_with_context(
    image_base64: str, 
    context: str = None,
    question_type: str = "general"
) -> dict:
    """
    Image analysis with context
    
    Args:
        image_base64: Base64 encoded image
        context: Additional context information
        question_type: Question type (algorithm, system_design, coding, general)
        
    Returns:
        dict: Dictionary containing analysis results
    """
    # Adjust prompt based on question type
    prompt_templates = {
        "algorithm": "This is an algorithm problem. Please analyze the problem requirements, provide the solution approach, time complexity analysis, and code implementation.",
        "system_design": "This is a system design problem. Please analyze the requirements, provide architecture design, technology choices, and explain the design rationale.",
        "coding": "This is a coding problem. Please analyze the problem, provide code implementation and test cases.",
        "general": "Please analyze the content of this image in detail."
    }
    
    prompt = prompt_templates.get(question_type, prompt_templates["general"])
    
    if context:
        prompt += f"\n\nAdditional information: {context}"
    
    answer, token_usage = await analyze_image(image_base64, prompt)
    
    return {
        "answer": answer,
        "question_type": question_type,
        "has_context": bool(context),
        "token_usage": token_usage
    }

