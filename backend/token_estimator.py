"""
Token estimation utilities
Provides rough token estimation before calling OpenAI API
"""
from typing import Union, List


def estimate_tokens_text(text: str) -> int:
    """
    Roughly estimate token count for text
    Uses simple heuristic: ~4 characters per token for English, ~1.5 characters per token for Chinese
    This is a rough estimate, actual token count may vary
    """
    if not text:
        return 0
    
    # Rough estimation: mixed Chinese/English text averages ~2 chars per token
    # Add some overhead for formatting tokens
    estimated = len(text) // 2
    # Add base overhead for message structure
    return max(estimated, 10)


def estimate_tokens_image(image_base64: str, detail: str = "high") -> int:
    """
    Estimate token count for an image
    Based on OpenAI's pricing:
    - Low detail: 85 tokens per image
    - High detail: 170 tokens base + variable based on image size
    """
    if detail == "low":
        return 85
    
    # High detail: base tokens + size-dependent tokens
    # For high detail, it's roughly 170 base + ~85 per 512x512 tile
    # We estimate based on base64 size as a proxy for image size
    base_tokens = 170
    
    # Estimate image size from base64 length
    # Base64 is ~4/3 the size of raw image data
    # For a 1024x1024 PNG, base64 is roughly ~500KB
    # That would be ~4 tiles, so ~340 additional tokens
    # Simplified: estimate 1 token per 1000 base64 characters
    size_tokens = len(image_base64) // 1000
    
    return base_tokens + size_tokens


def estimate_tokens_for_request(
    user_input: str = None,
    context: str = None,
    prompt: str = None,
    images: Union[str, List[str]] = None,
    max_output_tokens: int = 2000
) -> int:
    """
    Estimate total tokens needed for a request
    Includes input tokens and estimated output tokens
    
    Args:
        user_input: User text input
        context: Conversation context
        prompt: System prompt
        images: Base64 encoded image(s)
        max_output_tokens: Maximum output tokens (used for estimation)
    """
    total_input_tokens = 0
    
    # System prompt tokens
    if prompt:
        total_input_tokens += estimate_tokens_text(prompt)
    
    # Context tokens
    if context:
        total_input_tokens += estimate_tokens_text(context)
    
    # User input tokens
    if user_input:
        total_input_tokens += estimate_tokens_text(user_input)
    
    # Image tokens
    if images:
        if isinstance(images, str):
            images = [images]
        for img in images:
            total_input_tokens += estimate_tokens_image(img)
    
    # Add message structure overhead (~5 tokens per message)
    message_count = sum([
        1 if prompt else 0,
        1 if context else 0,
        1 if user_input else 0,
        len(images) if images else 0
    ])
    total_input_tokens += message_count * 5
    
    # Estimate output tokens (conservative estimate for pre-check only)
    # Lower ratio for more conservative pre-check: 0.3-0.4 instead of 0.6
    # Actual tokens will be deducted from OpenAI's response.usage
    estimated_output_tokens = int(max_output_tokens * 0.3)
    
    return total_input_tokens + estimated_output_tokens

