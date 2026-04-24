# your own chatbot

以 FastAPI 為後端、原生 JavaScript 為前端的全端 ChatGPT 介面，支援長期記憶、多模態輸入、自動模型路由、Tool Use、MCP 整合與圖片生成。

---

## 功能特色

| 功能 | 說明 |
|------|------|
| 💬 串流對話 | SSE 串流即時輸出，支援 Markdown 渲染 |
| 🧠 長期記憶 | Key-Value 記憶存至 SQLite，自動注入 System Prompt |
| 🖼 多模態輸入 | 支援圖片上傳（檔案選取、剪貼簿貼上、拖放），傳送給 GPT-4o Vision |
| 🔀 自動模型路由 | 依訊息內容自動選擇 gpt-4o-mini / gpt-4o / o3-mini |
| 🔧 Tool Use | 內建天氣查詢、匯率查詢、數學計算、時間查詢 |
| 🎨 圖片生成 | 透過 DALL-E 3 根據文字描述生成圖片 |
| 🔌 MCP 整合 | 透過 Model Context Protocol 接入 fetch 與 sqlite 工具 |
| 📚 對話記錄 | 自動儲存歷史對話，可隨時切換載入 |
| 🔍 對話搜尋 | 全文搜尋歷史對話內容，關鍵字高亮顯示 |

---

## 專案結構

```
hw2/
├── backend/
│   ├── main.py                  # FastAPI 入口，CORS、路由註冊、靜態檔案
│   ├── config.py                # pydantic-settings，讀取 .env
│   ├── database.py              # SQLAlchemy engine & session
│   ├── models.py                # ORM：Conversation、Message、LongTermMemory
│   ├── schemas.py               # Pydantic request/response 結構
│   ├── routers/
│   │   ├── chat.py              # POST /api/chat（SSE 串流，Tool Use loop）
│   │   ├── conversations.py     # 對話 CRUD + 關鍵字搜尋
│   │   ├── memory.py            # 長期記憶 CRUD
│   │   └── mcp_bridge.py        # MCP 工具列表 & 呼叫橋接
│   └── services/
│       ├── openai_client.py     # AsyncOpenAI singleton（含 SSL 修正）
│       ├── model_router.py      # 自動路由邏輯（regex heuristics）
│       ├── tool_registry.py     # 內建工具定義 & 執行（含 DALL-E 3）
│       └── mcp_manager.py       # MCP stdio subprocess 管理
├── frontend/
│   ├── index.html               # 單頁介面
│   ├── style.css                # 全部樣式
│   └── js/
│       ├── app.js               # 主入口，事件綁定，對話搜尋邏輯
│       ├── chat.js              # 送出訊息，串流處理，對話狀態
│       ├── ui.js                # DOM 操作（addMessage、addToolCard、addImageCard）
│       ├── api.js               # 所有 fetch 呼叫封裝
│       ├── memory.js            # 長期記憶 UI 邏輯
│       └── imageUpload.js       # 圖片上傳、壓縮、base64 轉換
├── requirements.txt
├── .env                         # API Key（不加入版本控制）
└── .gitignore
```

---

## 環境需求

- Python 3.10+
- Conda（建議）或 venv
- OpenAI API Key

---

## 安裝與啟動

### 1. 建立 Conda 環境

```bash
conda create -n chatbot python=3.11 -y
conda activate chatbot
```

### 2. 安裝相依套件

```bash
cd chatbot
pip install -r requirements.txt
```

### 3. 設定 API Key

在 `chatbot/` 根目錄建立 `.env` 檔案：

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

可選設定（有預設值）：

```env
DEFAULT_MODEL=gpt-4o-mini
FAST_MODEL=gpt-4o-mini
SMART_MODEL=gpt-4o
REASONING_MODEL=o3-mini
DATABASE_URL=sqlite:///./backend/chat.db
MCP_SQLITE_DB_PATH=./backend/mcp_data.db
BACKEND_PORT=8000
```

### 4. 啟動後端

```bash
uvicorn backend.main:app --reload --port 8000
```

### 5. 開啟網頁

瀏覽器前往：**http://localhost:8000**

---

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/chat` | 串流對話（SSE） |
| `GET` | `/api/memory` | 取得所有長期記憶 |
| `POST` | `/api/memory` | 新增記憶 |
| `DELETE` | `/api/memory/{key}` | 刪除記憶 |
| `GET` | `/api/conversations` | 列出所有對話 |
| `GET` | `/api/conversations/search?q=關鍵字` | 搜尋對話內容 |
| `GET` | `/api/conversations/{id}/messages` | 取得對話訊息 |
| `DELETE` | `/api/conversations/{id}` | 刪除對話 |
| `GET` | `/api/mcp/tools` | 列出可用 MCP 工具 |
| `POST` | `/api/mcp/call` | 呼叫 MCP 工具 |
| `GET` | `/api/health` | 後端健康檢查 |

---

## 自動模型路由規則

| 條件 | 選用模型 |
|------|---------|
| 包含圖片 | `gpt-4o`（Vision） |
| 推理/數學/邏輯題 | `o3-mini` |
| 程式碼相關 | `gpt-4o` |
| 長文本（>500 字）| `gpt-4o` |
| 短問句（<50 字）| `gpt-4o-mini` |
| 其他 | `gpt-4o-mini` |

---

## 內建工具（Tool Use）

| 工具名稱 | 說明 |
|---------|------|
| `get_current_datetime` | 取得台灣時區目前時間 |
| `calculate` | 安全數學算式計算 |
| `get_weather` | 即時天氣查詢（Open-Meteo，免費） |
| `get_exchange_rate` | 即時匯率查詢（Frankfurter，免費） |
| `generate_image` | DALL-E 3 圖片生成 |

---

## 使用範例

**圖片生成**
```
幫我畫一隻貓坐在宇宙中，背景有星球
```

**天氣查詢**
```
台北現在天氣如何？
```

**匯率查詢**
```
1 美金現在等於多少台幣？
```

**對話搜尋**  
在左側「🔍 搜尋對話內容…」輸入框中輸入關鍵字，300ms 後自動顯示含關鍵字的歷史對話，點擊即可載入。

---

## 注意事項

- `.env` 已加入 `.gitignore`，請勿將 API Key 提交至版本控制
- 使用 Conda 環境時若遇到 SSL 錯誤，`openai_client.py` 已自動透過 `certifi` 修正
- DALL-E 3 圖片生成會消耗較多 API 費用，每張約 $0.04
- MCP 工具需要安裝 `mcp-server-fetch` 與 `mcp-server-sqlite`（`npm install -g`）

---

## 技術架構

```
Browser
  └─ Vanilla JS (ES Modules)
       └─ fetch / SSE
            └─ FastAPI (uvicorn)
                 ├─ OpenAI API (gpt-4o / o3-mini / dall-e-3)
                 ├─ SQLite (chat.db)    ← 對話 & 記憶
                 └─ MCP stdio
                      ├─ mcp-server-fetch
                      └─ mcp-server-sqlite (mcp_data.db)
```
