import sys
import logging
from typing import Any

"""
MCP Manager：管理 MCP server subprocess 的生命週期並呼叫工具。

支援的 server：
  - fetch   (mcp-server-fetch)   : 抓取網頁內容
  - sqlite  (mcp-server-sqlite)  : 查詢/寫入 SQLite 資料庫

每次呼叫都會新開一個連線，如需長連線可改為在 lifespan 中建立並保持。

運作方式：
  用 subprocess 啟動 MCP server（例如 mcp-server-fetch）
  透過 stdin/stdout pipe 傳送 JSON-RPC 訊息
  拿到結果後回傳給 chat.py
"""

logger = logging.getLogger(__name__)

"""
定義如何啟動各個 MCP server（指令 + 參數）
"""
def _get_server_params(server: str):
    """回傳 MCP server 的啟動參數"""
    from mcp.client.stdio import StdioServerParameters
    from backend.config import get_settings

    s = get_settings()

    if server == "fetch":
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server_fetch"],
        )
    if server == "sqlite":
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server_sqlite", "--db-path", s.mcp_sqlite_db_path],
        )
    raise ValueError(f"未知的 MCP server：{server}，目前支援 fetch / sqlite")

"""
問某個 MCP server「你有什麼工具？」
"""
async def list_tools(server: str) -> list[dict[str, Any]]:
    """列出某個 MCP server 提供的所有工具"""
    try:
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        params = _get_server_params(server)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {
                        "server": server,
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema or {},
                    }
                    for tool in result.tools
                ]
    except Exception as e:
        logger.warning(f"MCP list_tools({server}) 失敗：{e}")
        return []


async def list_all_tools() -> list[dict[str, Any]]:
    """列出所有 MCP server 的工具（用於前端展示）"""
    results = []
    for server in ("fetch", "sqlite"):
        results.extend(await list_tools(server))
    return results

"""
實際呼叫 MCP server 上的工具
"""
async def call_tool(server: str, tool_name: str, arguments: dict[str, Any]) -> str:
    """呼叫 MCP server 上的特定工具，回傳文字結果"""
    try:
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        params = _get_server_params(server)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                # result.content 是 list[TextContent | ImageContent | ...]
                texts = []
                for item in result.content:
                    if hasattr(item, "text"):
                        texts.append(item.text)
                return "\n".join(texts) if texts else "（工具無回傳內容）"

    except Exception as e:
        logger.error(f"MCP call_tool({server}.{tool_name}) 失敗：{e}")
        return f"MCP 工具呼叫失敗：{e}"


async def get_mcp_tool_schemas_for_openai(servers: list[str] = None) -> list[dict]:
    """
    取得 MCP 工具的 schema，轉換為 OpenAI function calling 格式，
    以便直接加入 OpenAI API 的 tools 參數中。
    """
    if servers is None:
        servers = ["fetch", "sqlite"]

    openai_tools = []
    for server in servers:
        for tool in await list_tools(server):
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": f"mcp__{server}__{tool['name']}",  # 避免命名衝突
                    "description": f"[MCP:{server}] {tool['description']}",
                    "parameters": tool["input_schema"] or {
                        "type": "object", "properties": {}, "required": []
                    },
                },
            })
    return openai_tools


def parse_mcp_tool_name(full_name: str) -> tuple[str, str] | None:
    """
    解析 OpenAI tool call 的 name，判斷是否為 MCP 工具。
    格式：mcp__{server}__{tool_name}
    回傳 (server, tool_name) 或 None（不是 MCP 工具）
    """
    if full_name.startswith("mcp__"):
        parts = full_name.split("__", 2)
        if len(parts) == 3:
            return parts[1], parts[2]
    return None
