import { streamChat } from "./api.js";
import {
  addMessage,
  createStreamingBubble,
  addToolCard,
  addImageCard,
  updateModelBadge,
  formatContent,
  scrollToBottom,
  showToast,
} from "./ui.js";
import { getPendingImages, clearPendingImages } from "./imageUpload.js";

// ── 對話狀態 ──
let conversationHistory = [];  // {role, content}[]
let currentConversationId = null;
let isStreaming = false;
let totalTokens = 0;

export function getCurrentConversationId() {
  return currentConversationId;
}

export function setConversationId(id) {
  currentConversationId = id;
}

export function setHistory(messages) {
  conversationHistory = messages.map((m) => ({
    role: m.role,
    content: m.content,
  }));
}

export function resetChat() {
  conversationHistory = [];
  currentConversationId = null;
  totalTokens = 0;
  document.getElementById("token-count").textContent = "0";
}

// ── 主要送出函式 ──

export async function sendMessage() {
  if (isStreaming) return;

  const input = document.getElementById("user-input");
  const userText = input.value.trim();
  const images = getPendingImages();

  if (!userText && !images.length) return;

  // 組建 content（純文字 or multimodal）
  let userContent;
  if (images.length) {
    userContent = [{ type: "text", text: userText || "(圖片)" }];
    images.forEach((url) =>
      userContent.push({ type: "image_url", image_url: { url, detail: "auto" } })
    );
  } else {
    userContent = userText;
  }

  // 清空輸入
  input.value = "";
  input.style.height = "auto";
  clearPendingImages();
  document.getElementById("send-btn").disabled = true;
  isStreaming = true;

  // 顯示 user 訊息
  addMessage("user", userText || "(圖片)", {
    imageDataUrl: images[0] || null,
  });
  conversationHistory.push({ role: "user", content: userContent });

  // 讀取設定
  const autoRoute = document.getElementById("toggle-auto-route").checked;
  const useTools = document.getElementById("toggle-tools").checked;
  const modelSelect = document.getElementById("model-select").value;
  const systemPrompt = document.getElementById("system-prompt").value.trim();
  const temperature = parseFloat(document.getElementById("temperature").value);
  const maxTokens = parseInt(document.getElementById("max-tokens").value);
  const memoryTurns = parseInt(document.getElementById("memory-turns").value);

  // 限制記憶輪數
  let history = conversationHistory;
  if (memoryTurns > 0) {
    history = conversationHistory.slice(-(memoryTurns * 2));
  }

  const payload = {
    messages: history,
    model: autoRoute || modelSelect === "auto" ? null : modelSelect,
    auto_route: autoRoute || modelSelect === "auto",
    use_tools: useTools,
    conversation_id: currentConversationId,
    system_prompt: systemPrompt,
    temperature,
    max_tokens: maxTokens,
    memory_turns: memoryTurns,
  };

  // 建立串流 bubble
  const bubble = createStreamingBubble();
  let fullText = "";

  try {
    for await (const chunk of streamChat(payload)) {
      if (chunk.type === "model_selected") {
        updateModelBadge(chunk.model, chunk.reason);
      } else if (chunk.type === "text") {
        fullText += chunk.content;
        bubble.innerHTML =
          formatContent(fullText) + '<span class="cursor"></span>';
        scrollToBottom();
      } else if (chunk.type === "tool_call") {
        addToolCard(bubble, chunk.tool, chunk.args, chunk.result, chunk.tool_type);
      } else if (chunk.type === "image_generated") {
        addImageCard(bubble, chunk.prompt, chunk.url);
      } else if (chunk.type === "done") {
        currentConversationId = chunk.conversation_id;
        localStorage.setItem("hw2_current_conv", chunk.conversation_id);
      }
    }

    // 移除游標，完成渲染
    bubble.innerHTML = formatContent(fullText);

    // 加入 assistant 歷史
    if (fullText) {
      conversationHistory.push({ role: "assistant", content: fullText });
    }

    // 通知 app.js 重新載入對話列表
    document.dispatchEvent(new CustomEvent("chat:done"));
  } catch (err) {
    bubble.innerHTML = `<span style="color:#f87171">⚠ 錯誤：${err.message}</span>`;
    showToast(err.message, "error");
  }

  document.getElementById("send-btn").disabled = false;
  isStreaming = false;
}
