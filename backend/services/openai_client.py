import os
import certifi
from openai import AsyncOpenAI
from backend.config import get_settings

"""
建立一個全域共用的 AsyncOpenAI client。
整個 app 只建立一個 client 實例（singleton pattern），
好處是連線池可以複用，不會每次請求都重新握手。
"""

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Module-level singleton，整個 app 共用同一個 client（連線池複用）
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    return _client
