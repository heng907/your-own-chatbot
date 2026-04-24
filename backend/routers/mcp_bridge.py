from fastapi import APIRouter, HTTPException
from backend.schemas import McpCallRequest, McpToolOut
from backend.services import mcp_manager

router = APIRouter(prefix="/mcp", tags=["mcp"])

"""
列出所有 MCP server 的工具（給前端展示用）
"""
@router.get("/tools", response_model=list[McpToolOut])
async def get_mcp_tools():
    """列出所有可用的 MCP 工具（fetch + sqlite）"""
    tools = await mcp_manager.list_all_tools()
    return [McpToolOut(**t) for t in tools]

"""
直接呼叫 MCP 工具
"""
@router.post("/call")
async def call_mcp_tool(req: McpCallRequest):
    """直接呼叫 MCP 工具（供前端手動測試用）"""
    if req.server not in ("fetch", "sqlite"):
        raise HTTPException(status_code=400, detail="server 只支援 fetch 或 sqlite")
    result = await mcp_manager.call_tool(req.server, req.tool_name, req.arguments)
    return {"result": result}
