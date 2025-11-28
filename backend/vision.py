import os
import base64
from io import BytesIO
from PIL import Image
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# 初始化 OpenAI 客户端
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

async def analyze_image(image_base64: str | list[str], prompt: str = None) -> str:
    """
    使用 OpenAI Vision API 分析图片（支持多张图片）
    
    Args:
        image_base64: Base64 编码的图片或图片列表
        prompt: 分析提示词（可选）
        
    Returns:
        str: AI 分析结果
    """
    try:
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

        # 获取模型名称
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # 将单张图片转为列表
        if isinstance(image_base64, str):
            image_list = [image_base64]
        else:
            image_list = image_base64
        
        print(f"🤖 调用模型: {model}")
        print(f"📸 图片数量: {len(image_list)}")
        print(f"📝 提示词: {prompt[:100]}...")
        
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
        response = await client.chat.completions.create(
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
        
        print(f"✅ 分析完成，回复长度: {len(answer)} 字符")
        
        return answer
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 视觉分析失败: {error_msg}")
        
        # 返回友好的错误信息
        if "api_key" in error_msg.lower():
            return "❌ API Key 错误，请检查 .env 文件中的 OPENAI_API_KEY"
        elif "rate_limit" in error_msg.lower():
            return "❌ API 调用频率超限，请稍后再试"
        elif "insufficient_quota" in error_msg.lower():
            return "❌ API 配额不足，请检查你的 OpenAI 账户余额"
        else:
            return f"❌ 分析失败: {error_msg}"


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
    
    answer = await analyze_image(image_base64, prompt)
    
    return {
        "answer": answer,
        "question_type": question_type,
        "has_context": bool(context)
    }

