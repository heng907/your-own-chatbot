const BASE = "http://localhost:8000/api";

// ── Streaming Chat（generator，逐一 yield 解析後的 chunk）──

export async function* streamChat(payload) {
  const resp = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop(); // 保留不完整的最後一行

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (data === "[DONE]") return;
      try {
        yield JSON.parse(data);
      } catch {
        // 忽略無法解析的行
      }
    }
  }
}

// ── Memory ──

export async function getMemory() {
  const resp = await fetch(`${BASE}/memory`);
  if (!resp.ok) return [];
  return resp.json();
}

export async function saveMemory(key, value) {
  const resp = await fetch(`${BASE}/memory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, value }),
  });
  if (!resp.ok) throw new Error("儲存記憶失敗");
  return resp.json();
}

export async function deleteMemory(key) {
  const resp = await fetch(`${BASE}/memory/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
  if (!resp.ok) throw new Error("刪除記憶失敗");
  return resp.json();
}

// ── Conversations ──

export async function getConversations() {
  const resp = await fetch(`${BASE}/conversations`);
  if (!resp.ok) return [];
  return resp.json();
}

export async function getConversationMessages(id) {
  const resp = await fetch(`${BASE}/conversations/${id}/messages`);
  if (!resp.ok) return [];
  return resp.json();
}

export async function deleteConversation(id) {
  const resp = await fetch(`${BASE}/conversations/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error("刪除對話失敗");
  return resp.json();
}

export async function searchConversations(query) {
  if (!query.trim()) return [];
  const resp = await fetch(
    `${BASE}/conversations/search?q=${encodeURIComponent(query.trim())}`
  );
  if (!resp.ok) return [];
  return resp.json();
}

// ── MCP ──

export async function getMcpTools() {
  const resp = await fetch(`${BASE}/mcp/tools`);
  if (!resp.ok) return [];
  return resp.json();
}

export async function callMcpTool(server, toolName, args) {
  const resp = await fetch(`${BASE}/mcp/call`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ server, tool_name: toolName, arguments: args }),
  });
  if (!resp.ok) throw new Error("MCP 呼叫失敗");
  return resp.json();
}

// ── Health check ──

export async function checkHealth() {
  try {
    const resp = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(3000) });
    return resp.ok;
  } catch {
    return false;
  }
}
