// ── Markdown formatter

export function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function formatContent(text) {
  // Code blocks
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="language-${lang}">${escapeHtml(code.trim())}</code></pre>`
  );
  // Inline code
  text = text.replace(/`([^`]+)`/g, (_, c) => `<code>${escapeHtml(c)}</code>`);
  // Bold
  text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Italic
  text = text.replace(/\*(.*?)\*/g, "<em>$1</em>");
  // Headings
  text = text.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  text = text.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  text = text.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  // Unordered list
  text = text.replace(/^\s*[-*] (.+)$/gm, "<li>$1</li>");
  text = text.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");
  // Newlines → <br>
  text = text.replace(/\n/g, "<br>");
  return text;
}

// ── 新增訊息到 #messages ──

export function addMessage(role, content, { imageDataUrl } = {}) {
  const welcome = document.getElementById("welcome-msg");
  if (welcome) welcome.remove();

  const msgs = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "👤" : "✦";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatContent(content);

  // 如果有附圖，顯示縮圖
  if (imageDataUrl) {
    const img = document.createElement("img");
    img.src = imageDataUrl;
    img.className = "attached-image";
    bubble.appendChild(img);
  }

  div.appendChild(avatar);
  div.appendChild(bubble);
  msgs.appendChild(div);
  scrollToBottom();
  return bubble;
}

// ── 建立串流 bubble（回傳 bubble element 供後續 append）──

export function createStreamingBubble() {
  const welcome = document.getElementById("welcome-msg");
  if (welcome) welcome.remove();

  const msgs = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = "msg assistant";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "✦";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = '<span class="cursor"></span>';

  div.appendChild(avatar);
  div.appendChild(bubble);
  msgs.appendChild(div);
  scrollToBottom();
  return bubble;
}

// ── Tool Call 卡片 ──

export function addToolCard(bubble, toolName, args, result, toolType) {
  const card = document.createElement("div");
  card.className = "tool-card";

  const icon = toolType?.startsWith("mcp") ? "🔌" : "🔧";
  const header = document.createElement("div");
  header.className = "tool-card-header";
  header.innerHTML = `${icon} <span>${toolName}</span> <span style="margin-left:auto;font-size:10px;opacity:0.6">▼ 展開</span>`;

  const body = document.createElement("div");
  body.className = "tool-card-body hidden";
  body.textContent = `Args: ${JSON.stringify(args, null, 2)}\n\nResult: ${result}`;

  header.onclick = () => {
    body.classList.toggle("hidden");
    header.querySelector("span:last-child").textContent =
      body.classList.contains("hidden") ? "▼ 展開" : "▲ 收起";
  };

  card.appendChild(header);
  card.appendChild(body);
  bubble.appendChild(card);
  scrollToBottom();
}

// ── 圖片生成卡片 ──

export function addImageCard(bubble, prompt, url) {
  const card = document.createElement("div");
  card.className = "image-card";

  const header = document.createElement("div");
  header.className = "image-card-header";
  header.innerHTML = `🖼 DALL-E 生成
    <a href="${url}" download="dalle-image.png" target="_blank"
       class="image-download-btn" title="下載圖片" onclick="event.stopPropagation()">⬇</a>`;

  const img = document.createElement("img");
  img.src = url;
  img.className = "generated-image";
  img.alt = prompt;
  img.loading = "lazy";

  const promptEl = document.createElement("div");
  promptEl.className = "image-prompt-text";
  promptEl.textContent = `提示詞：${prompt}`;

  card.appendChild(header);
  card.appendChild(img);
  card.appendChild(promptEl);
  bubble.appendChild(card);
  scrollToBottom();
}

// ── 更新 model badge ──

export function updateModelBadge(model, reason) {
  document.getElementById("model-badge-text").textContent = model;
  document.getElementById("model-reason-tooltip").textContent = `原因：${reason}`;
}

// ── Auto resize textarea ──

export function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 180) + "px";
}

// ── Scroll ──

export function scrollToBottom() {
  const msgs = document.getElementById("messages");
  msgs.scrollTop = msgs.scrollHeight;
}

// ── Toast 通知 ──

export function showToast(message, type = "") {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}
