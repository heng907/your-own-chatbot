import { sendMessage, resetChat, setHistory, setConversationId } from "./chat.js";
import { loadMemories, addMemoryItem, removeMemoryItem } from "./memory.js";
import { initImageUpload, triggerImageUpload } from "./imageUpload.js";
import { autoResize, showToast, addMessage } from "./ui.js";
import {
  getConversations,
  getConversationMessages,
  deleteConversation,
  searchConversations,
  checkHealth,
} from "./api.js";

// ── 初始化 ──

window.addEventListener("DOMContentLoaded", async () => {
  initImageUpload();
  bindEvents();
  await loadMemories();
  await loadConversationList();
  await checkBackendHealth();

  // 還原上次對話 ID
  const lastId = localStorage.getItem("hw2_current_conv");
  if (lastId) {
    await loadConversation(lastId);
  }
});

// ── 後端健康檢查 ──

async function checkBackendHealth() {
  const ok = await checkHealth();
  if (!ok) {
    showToast("⚠ 無法連線後端，請確認 uvicorn 是否執行中", "error");
  }
}

// ── 事件綁定 ──

function bindEvents() {
  // 送出按鈕
  document.getElementById("send-btn").addEventListener("click", sendMessage);

  // Enter 送出 / Shift+Enter 換行
  document.getElementById("user-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Textarea 自動高度
  document.getElementById("user-input").addEventListener("input", (e) =>
    autoResize(e.target)
  );

  // 對話完成後重新載入列表
  document.addEventListener("chat:done", loadConversationList);

  // 對話搜尋（300ms debounce）
  let searchTimer = null;
  document.getElementById("conv-search").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    const q = e.target.value.trim();
    searchTimer = setTimeout(() => {
      if (q) {
        renderSearchResults(q);
      } else {
        loadConversationList(); // 清空搜尋時還原列表
      }
    }, 300);
  });
}

// ── 搜尋結果渲染 ──

function highlightKeyword(text, keyword) {
  if (!keyword) return text;
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return text.replace(
    new RegExp(escaped, "gi"),
    (match) => `<span class="conv-highlight">${match}</span>`
  );
}

async function renderSearchResults(query) {
  const el = document.getElementById("conv-list");
  el.innerHTML = `<span style="font-size:11px;color:var(--text-muted)">搜尋中…</span>`;

  try {
    const results = await searchConversations(query);

    if (!results.length) {
      el.innerHTML = `<span style="font-size:11px;color:var(--text-muted)">找不到「${query}」</span>`;
      return;
    }

    el.innerHTML = results
      .map((r) => `
        <div class="conv-item search-result" onclick="loadConv('${r.conversation_id}')">
          <div style="flex:1;min-width:0;">
            <div class="conv-item-title" title="${r.conversation_title}">
              ${highlightKeyword(r.conversation_title, query)}
            </div>
            <div class="conv-item-snippet">
              ${highlightKeyword(r.content_snippet, query)}
            </div>
          </div>
          <button class="conv-item-del" onclick="deleteConv(event,'${r.conversation_id}')" title="刪除">✕</button>
        </div>`)
      .join("");
  } catch (err) {
    el.innerHTML = `<span style="font-size:11px;color:#f87171">搜尋失敗：${err.message}</span>`;
  }
}

// ── 對話列表 ──

async function loadConversationList() {
  const el = document.getElementById("conv-list");
  const convs = await getConversations();

  if (!convs.length) {
    el.innerHTML = `<span style="font-size:11px;color:var(--text-muted)">尚無記錄</span>`;
    return;
  }

  const currentId = localStorage.getItem("hw2_current_conv");
  el.innerHTML = convs
    .map(
      (c) => `
    <div class="conv-item ${c.id === currentId ? "active" : ""}"
         onclick="loadConv('${c.id}')">
      <span class="conv-item-title" title="${c.title}">${c.title}</span>
      <button class="conv-item-del" onclick="deleteConv(event,'${c.id}')" title="刪除">✕</button>
    </div>`
    )
    .join("");
}

// ── 載入特定對話 ──

async function loadConversation(id) {
  const msgs = await getConversationMessages(id);
  if (!msgs.length) return;

  // 清空畫面
  const msgsEl = document.getElementById("messages");
  msgsEl.innerHTML = "";

  // 還原歷史
  const history = [];
  msgs.forEach((m) => {
    if (m.role === "user" || m.role === "assistant") {
      addMessage(m.role, m.content);
      history.push({ role: m.role, content: m.content });
    }
  });

  setHistory(history);
  setConversationId(id);
  localStorage.setItem("hw2_current_conv", id);
  await loadConversationList();
}

// ── 新對話 ──

export function newChat() {
  resetChat();
  localStorage.removeItem("hw2_current_conv");
  const msgsEl = document.getElementById("messages");
  msgsEl.innerHTML = `
    <div class="welcome" id="welcome-msg">
      <div class="big-icon">✦</div>
      <h3>MyChatGPT v2</h3>
      <p>新對話已開始。在左側設定參數後開始對話。</p>
    </div>`;
  loadConversationList();
}

export function clearCurrentChat() {
  newChat();
}

// ── 記憶操作（掛在 window 供 HTML onclick 使用）──

window.addMemory = () => {
  const key = document.getElementById("mem-key-input").value.trim();
  const val = document.getElementById("mem-val-input").value.trim();
  if (!key || !val) return showToast("請填寫 key 和 value", "error");
  addMemoryItem(key, val);
  document.getElementById("mem-key-input").value = "";
  document.getElementById("mem-val-input").value = "";
};

window.removeMemory = (key) => removeMemoryItem(key);

// ── 對話操作（掛在 window 供 HTML onclick 使用）──

window.loadConv = (id) => loadConversation(id);

window.deleteConv = async (e, id) => {
  e.stopPropagation();
  await deleteConversation(id);
  if (localStorage.getItem("hw2_current_conv") === id) {
    newChat();
  }
  await loadConversationList();
  showToast("對話已刪除");
};

window.newChat = newChat;
window.clearCurrentChat = clearCurrentChat;

// ── 圖片上傳（掛在 window 供 HTML onclick 使用）──
window.triggerImageUpload = triggerImageUpload;

// ── Mobile sidebar ──
window.openSidebar = () => {
  document.getElementById("sidebar").classList.add("open");
  document.getElementById("overlay").classList.add("show");
};
window.closeSidebar = () => {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("overlay").classList.remove("show");
};
