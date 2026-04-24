from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

"""
讀取 .env 檔案，把 OPENAI_API_KEY、模型名稱、DB路徑等
包裝成一個 Settings 物件。所有其他檔案要用設定時，都來這裡拿。
"""
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""

    # 模型設定
    default_model: str = "gpt-4o-mini"
    fast_model: str = "gpt-4o-mini"
    smart_model: str = "gpt-4o"
    reasoning_model: str = "o3-mini"

    # 資料庫
    database_url: str = "sqlite:///./backend/chat.db"

    # MCP
    mcp_sqlite_db_path: str = "./backend/mcp_data.db"

    # 伺服器
    backend_port: int = 8000


@lru_cache # 確保 .env 只讀一次，不會每次請求都重新讀檔。
def get_settings() -> Settings:
    return Settings()
