import os
import base64
from io import BytesIO
from PIL import Image
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# ⚠️ 不再在模块级别初始化客户端，改为在函数中接收动态客户端

async def analyze_image(image_base64: str | list[str], prompt: str = None, client: AsyncOpenAI = None, model: str = None) -> tuple[str, dict]:
    """
    使用 OpenAI Vision API 分析图片（支持多张图片）
    
    Args:
        image_base64: Base64 编码的图片或图片列表
        prompt: 分析提示词（可选）
        client: OpenAI 客户端（必须提供）
        model: 模型名称（可选，如果不提供则使用环境变量或默认值）
        
    Returns:
        str: AI 分析结果
    """
    try:
        # 🔑 必须提供客户端
        if client is None:
            raise ValueError("Client must be provided")
        
        api_client = client
        # 默认提示词 - 结构化面试题版
        if not prompt:
            prompt = """请仔细阅读截图中的题目。

请严格按照以下 5 个部分进行回复，不要包含其他多余的描述：

1）问题解释（简短）
简要概括题目要求，不要啰嗦。

2）Clarification Questions
列出 3-5 个针对题目细节的关键澄清问题（例如：边界条件、输入规模、异常情况）。保持简短。

3）解题思路
分步骤说明最优解法，清晰明了。

4）代码
```python
# 在此提供完整的 Python 代码，包含关键注释
```

5）解释
对代码的关键逻辑进行简要解释，包括时间/空间复杂度分析。

⚠️ 禁止事项：
- 不要写 "问题描述"、"示例"、"约束条件" 章节。
- 不要写 "这张图片展示了..." 等废话。
- 保持回答专业、紧凑。"""

        # 获取模型名称（优先使用传入的模型，其次环境变量，最后默认值）
        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # 将单张图片转为列表
        if isinstance(image_base64, str):
            image_list = [image_base64]
        else:
            image_list = image_base64
        
        print(f"🤖 调用模型: {model}")
        print(f"📸 图片数量: {len(image_list)}")
        print(f"📝 提示词: {prompt[:100]}...")
        
        # 🔍 调试：检查图片数据
        for idx, img_base64 in enumerate(image_list):
            print(f"📷 图片 {idx + 1} 数据长度: {len(img_base64)} 字符")
            print(f"📷 图片 {idx + 1} 数据前50字符: {img_base64[:50]}")
        
        # 构建 content 数组
        content = [{"type": "text", "text": prompt}]
        
        # 添加所有图片
        for img_base64 in image_list:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}",
                    "detail": "high"
                }
            })
        
        # 调用 OpenAI Vision API
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
        
        # 提取回复
        answer = response.choices[0].message.content
        
        # 提取 token 使用量
        token_usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        print(f"✅ 分析完成，回复长度: {len(answer)} 字符")
        print(f"📊 Token 使用: {token_usage['total_tokens']} (输入: {token_usage['input_tokens']}, 输出: {token_usage['output_tokens']})")
        
        return answer, token_usage
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 视觉分析失败: {error_msg}")
        
        # 返回友好的错误信息
        error_message = ""
        if "api_key" in error_msg.lower() or "invalid api key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_message = "❌ API Key 错误。"
            # 检查是否在 Vercel 环境（多种方式检测）
            import os
            is_vercel = os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("NOW_REGION")
            
            if is_vercel:
                error_message += "\n\n请在 Vercel Dashboard 中检查："
                error_message += "\n1. 进入 Settings -> Environment Variables"
                error_message += "\n2. 确认 OPENAI_API_KEY 已配置"
                error_message += "\n3. 确保 API Key 值正确（以 'sk-' 开头）"
                error_message += "\n4. 添加后需要重新部署应用"
            else:
                error_message += "\n\n请检查："
                error_message += "\n1. 本地环境：检查 backend/.env 文件中的 OPENAI_API_KEY"
                error_message += "\n2. Vercel 环境：检查 Vercel Dashboard -> Settings -> Environment Variables"
                error_message += "\n3. 确保 API Key 以 'sk-' 开头且完整"
            error_message += "\n\n如果问题仍然存在，请查看服务器日志获取更多信息。"
        elif "rate_limit" in error_msg.lower():
            error_message = "❌ API 调用频率超限，请稍后再试"
        elif "insufficient_quota" in error_msg.lower():
            error_message = "❌ API 配额不足，请检查你的 OpenAI 账户余额"
        else:
            error_message = f"❌ 分析失败: {error_msg}"
        
        return error_message, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def validate_image_base64(image_base64: str) -> bool:
    """
    验证 Base64 图片是否有效
    
    Args:
        image_base64: Base64 编码的图片
        
    Returns:
        bool: 是否有效
    """
    try:
        # 解码 base64
        image_data = base64.b64decode(image_base64)
        
        # 尝试打开图片
        image = Image.open(BytesIO(image_data))
        
        # 检查图片格式
        if image.format not in ['PNG', 'JPEG', 'JPG', 'GIF', 'WEBP']:
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 图片验证失败: {e}")
        return False


async def analyze_image_with_context(
    image_base64: str, 
    context: str = None,
    question_type: str = "general"
) -> dict:
    """
    带上下文的图片分析
    
    Args:
        image_base64: Base64 编码的图片
        context: 额外的上下文信息
        question_type: 问题类型（algorithm, system_design, coding, general）
        
    Returns:
        dict: 包含分析结果的字典
    """
    # 根据问题类型调整提示词
    prompt_templates = {
        "algorithm": "这是一道算法题。请分析题目要求，提供解题思路、时间复杂度分析，并给出代码实现。",
        "system_design": "这是一道系统设计题。请分析需求，提供架构设计、技术选型，并说明设计理由。",
        "coding": "这是一道编程题。请分析题目，提供代码实现和测试用例。",
        "general": "请详细分析这张图片的内容。"
    }
    
    prompt = prompt_templates.get(question_type, prompt_templates["general"])
    
    if context:
        prompt += f"\n\n额外信息: {context}"
    
    answer, token_usage = await analyze_image(image_base64, prompt)
    
    return {
        "answer": answer,
        "question_type": question_type,
        "has_context": bool(context),
        "token_usage": token_usage
    }

