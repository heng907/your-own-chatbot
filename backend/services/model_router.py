import re
from backend.config import get_settings

"""
Auto Routing 的核心邏輯。
輸入：訊息列表 + 是否有圖片
輸出：(模型名稱, 選擇原因)

"""

def route(messages: list[dict], has_image: bool = False) -> tuple[str, str]:
    """
    根據訊息內容自動選擇最適合的模型。
    回傳 (model_name, reason)
    """
    s = get_settings()

    # 1. 有圖片 → 必須用支援 vision 的模型
    if has_image:
        return s.smart_model, "圖片輸入，需要 vision 模型"

    # 取最後一則 user 訊息的文字
    user_text = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                user_text = content
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_text += part.get("text", "")
            break

    lower = user_text.lower()

    # 2. 推理類問題 → reasoning model
    reasoning_patterns = [
        r"\bprove\b", r"\bderive\b", r"step.by.step",
        r"數學證明", r"邏輯推理", r"推導", r"o1", r"o3",
        r"reasoning", r"logic puzzle",
    ]
    if any(re.search(p, lower) for p in reasoning_patterns):
        return s.reasoning_model, "推理/數學任務"

    # 3. 程式碼相關 → smart model
    code_patterns = [
        r"```", r"\bcode\b", r"\bdebug\b", r"\bfunction\b",
        r"\bimplement\b", r"\brefactor\b", r"\balgorithm\b",
        r"寫程式", r"程式碼", r"實作", r"debug", r"修bug",
    ]
    if any(re.search(p, lower) for p in code_patterns):
        return s.smart_model, "程式碼任務"

    # 4. 長對話或長訊息 → smart model
    total_chars = sum(
        len(m.get("content", "") if isinstance(m.get("content"), str) else "")
        for m in messages
    )
    if len(user_text) > 500 or total_chars > 3000:
        return s.smart_model, "長文本/複雜對話"

    # 5. 短問句 → fast model
    if len(user_text) < 50 and "?" not in user_text and "？" not in user_text:
        return s.fast_model, "簡短訊息"

    # 6. 預設
    return s.default_model, "一般對話"
