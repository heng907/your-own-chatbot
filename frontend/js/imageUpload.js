// 暫存目前待傳送的圖片列表
const _pending = []; // [{dataUrl, file}]

// ── 最大邊長 1024px 的 canvas resize ──

function resizeImage(file, maxPx = 1024) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        let { width, height } = img;
        if (width > maxPx || height > maxPx) {
          if (width > height) {
            height = Math.round((height * maxPx) / width);
            width = maxPx;
          } else {
            width = Math.round((width * maxPx) / height);
            height = maxPx;
          }
        }
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        canvas.getContext("2d").drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// ── 渲染預覽 strip ──

function renderPreviews() {
  const strip = document.getElementById("image-preview-strip");
  strip.innerHTML = "";
  _pending.forEach((item, i) => {
    const wrapper = document.createElement("div");
    wrapper.className = "img-preview-item";

    const img = document.createElement("img");
    img.src = item.dataUrl;

    const btn = document.createElement("button");
    btn.className = "remove-img";
    btn.textContent = "✕";
    btn.onclick = () => {
      _pending.splice(i, 1);
      renderPreviews();
    };

    wrapper.appendChild(img);
    wrapper.appendChild(btn);
    strip.appendChild(wrapper);
  });
}

// ── 處理選擇的檔案 ──

async function handleFiles(files) {
  for (const file of files) {
    if (!file.type.startsWith("image/")) continue;
    const dataUrl = await resizeImage(file);
    _pending.push({ dataUrl, file });
  }
  renderPreviews();
}

// ── 初始化（綁定 input + paste + drop）──

export function initImageUpload() {
  const fileInput = document.getElementById("image-file-input");
  const inputArea = document.getElementById("input-area");

  // File input 選擇
  fileInput.addEventListener("change", () => {
    handleFiles(Array.from(fileInput.files));
    fileInput.value = ""; // 允許重複選同一張
  });

  // Ctrl+V 貼上截圖
  document.addEventListener("paste", (e) => {
    const items = Array.from(e.clipboardData?.items || []);
    const imageItems = items.filter((it) => it.type.startsWith("image/"));
    if (!imageItems.length) return;
    e.preventDefault();
    handleFiles(imageItems.map((it) => it.getAsFile()));
  });

  // 拖曳放入輸入區
  inputArea.addEventListener("dragover", (e) => e.preventDefault());
  inputArea.addEventListener("drop", (e) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith("image/")
    );
    if (files.length) handleFiles(files);
  });
}

// ── 觸發 file dialog ──

export function triggerImageUpload() {
  document.getElementById("image-file-input").click();
}

// ── 取得目前待傳送的圖片（送出後清空）──

export function getPendingImages() {
  return _pending.map((item) => item.dataUrl);
}

export function clearPendingImages() {
  _pending.length = 0;
  renderPreviews();
}
