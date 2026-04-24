import { getMemory, saveMemory, deleteMemory } from "./api.js";
import { showToast } from "./ui.js";

const LS_KEY = "hw2_memories";

// ── localStorage 層 ──

function loadLocal() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveLocal(items) {
  localStorage.setItem(LS_KEY, JSON.stringify(items));
}

// ── 渲染記憶列表 ──

export function renderMemoryList(items) {
  const el = document.getElementById("memory-list");
  if (!items.length) {
    el.innerHTML = `<span style="font-size:11px;color:var(--text-muted)">尚無記憶</span>`;
    return;
  }
  el.innerHTML = items
    .map(
      (m) => `
    <div class="memory-item">
      <span class="memory-key">${m.key}</span>
      <span class="memory-val">${m.value}</span>
      <button class="memory-del" onclick="removeMemory('${m.key}')" title="刪除">✕</button>
    </div>`
    )
    .join("");
}

// ── 從後端載入記憶（頁面初始化時呼叫）──

export async function loadMemories() {
  try {
    const items = await getMemory();
    // 合併到 localStorage
    saveLocal(items);
    renderMemoryList(items);
    return items;
  } catch {
    // 後端不通時，用 localStorage
    const local = loadLocal();
    renderMemoryList(local);
    return local;
  }
}

// ── 新增記憶 ──

export async function addMemoryItem(key, value) {
  if (!key || !value) return;
  try {
    await saveMemory(key.trim(), value.trim());
    // 更新 localStorage
    const items = loadLocal().filter((m) => m.key !== key.trim());
    items.unshift({ key: key.trim(), value: value.trim() });
    saveLocal(items);
    await loadMemories();
    showToast("記憶已儲存", "success");
  } catch (e) {
    showToast("儲存失敗：" + e.message, "error");
  }
}

// ── 刪除記憶 ──

export async function removeMemoryItem(key) {
  try {
    await deleteMemory(key);
    const items = loadLocal().filter((m) => m.key !== key);
    saveLocal(items);
    await loadMemories();
    showToast("記憶已刪除");
  } catch (e) {
    showToast("刪除失敗：" + e.message, "error");
  }
}
