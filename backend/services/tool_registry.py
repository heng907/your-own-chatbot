import ast
import operator
import datetime as dt
from typing import Any

"""
內建工具的「定義 + 執行器」。

分兩部分：
1. TOOLS 陣列：告訴 OpenAI「你有哪些工具可以用」
   （OpenAI function calling 格式的 JSON schema）

2. execute_tool() 函式：當 OpenAI 說「我要呼叫 calculate」，
   這個函式實際執行計算並回傳結果。

"""
# ── Tool schemas（OpenAI function calling 格式）──

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "取得目前的日期與時間（台灣時區）",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "安全地計算數學算式，例如 '2 ** 10' 或 '(3 + 5) * 2'",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要計算的數學算式（純數字與運算符）",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查詢某城市目前的天氣狀況（使用 Open-Meteo 免費 API）",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名稱，例如 'Taipei'、'Tokyo'、'London'",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "查詢兩種貨幣之間的即時匯率",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_currency": {"type": "string", "description": "來源貨幣，例如 'USD'"},
                    "to_currency": {"type": "string", "description": "目標貨幣，例如 'TWD'"},
                },
                "required": ["from_currency", "to_currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "使用 DALL-E 3 根據文字描述生成圖片。當使用者說「幫我畫」、「生成一張」、「畫一個」、「create an image」等時使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "圖片的詳細描述（中文或英文皆可）",
                    },
                    "size": {
                        "type": "string",
                        "enum": ["1024x1024", "1024x1792", "1792x1024"],
                        "description": "圖片尺寸：1024x1024（正方形）、1024x1792（直式）、1792x1024（橫式），預設正方形",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
]


# ── 安全的算式計算器 ──

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.FloorDiv, ast.USub, ast.UAdd,
)

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(expr: str) -> float:
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"不允許的算式節點：{type(node).__name__}")

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return _OPS[type(node.op)](_eval(node.operand))
        raise ValueError("無法計算的節點")

    return _eval(tree.body)


# ── 天氣查詢（Open-Meteo + Geocoding API，免費無需 API Key）──

_CITY_COORDS: dict[str, tuple[float, float]] = {
    "taipei": (25.0375, 121.5625),
    "kaohsiung": (22.6273, 120.3014),
    "tokyo": (35.6762, 139.6503),
    "osaka": (34.6937, 135.5023),
    "london": (51.5074, -0.1278),
    "new york": (40.7128, -74.0060),
    "paris": (48.8566, 2.3522),
    "singapore": (1.3521, 103.8198),
    "hong kong": (22.3193, 114.1694),
    "seoul": (37.5665, 126.9780),
}

_WMO_CODES: dict[int, str] = {
    0: "晴天", 1: "大致晴朗", 2: "部分多雲", 3: "陰天",
    45: "有霧", 48: "結冰霧",
    51: "毛毛雨（輕）", 53: "毛毛雨（中）", 55: "毛毛雨（強）",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "陣雨（輕）", 81: "陣雨（中）", 82: "陣雨（強）",
    95: "雷陣雨", 96: "冰雹雷雨", 99: "強冰雹雷雨",
}


async def _fetch_weather(city: str) -> str:
    import httpx

    key = city.lower().strip()
    coords = _CITY_COORDS.get(key)

    if coords is None:
        # 嘗試透過 Open-Meteo Geocoding API 查詢
        async with httpx.AsyncClient(timeout=10) as client:
            geo = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "zh", "format": "json"},
            )
        results = geo.json().get("results")
        if not results:
            return f"找不到城市：{city}"
        coords = (results[0]["latitude"], results[0]["longitude"])

    lat, lon = coords
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weathercode",
                "timezone": "Asia/Taipei",
            },
        )
    data = resp.json().get("current", {})
    code = data.get("weathercode", -1)
    desc = _WMO_CODES.get(code, "未知")
    temp = data.get("temperature_2m", "?")
    humidity = data.get("relative_humidity_2m", "?")
    wind = data.get("wind_speed_10m", "?")
    return f"{city} 目前天氣：{desc}，氣溫 {temp}°C，濕度 {humidity}%，風速 {wind} km/h"


# ── 匯率查詢（frankfurter.app，免費無需 API Key）──

async def _fetch_exchange_rate(from_currency: str, to_currency: str) -> str:
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"https://api.frankfurter.app/latest",
            params={"from": from_currency.upper(), "to": to_currency.upper()},
        )
    if resp.status_code != 200:
        return f"無法查詢匯率：{from_currency} → {to_currency}"
    data = resp.json()
    rate = data["rates"].get(to_currency.upper(), "?")
    return f"1 {from_currency.upper()} = {rate} {to_currency.upper()}（資料日期：{data['date']}）"


# ── 圖片生成（DALL-E 3）──

async def _generate_image(prompt: str, size: str = "1024x1024") -> str:
    from backend.services.openai_client import get_client

    valid_sizes = {"1024x1024", "1024x1792", "1792x1024"}
    if size not in valid_sizes:
        size = "1024x1024"

    client = get_client()
    response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="standard",
        n=1,
    )
    url = response.data[0].url
    # 以特殊前綴標記，讓 chat.py 識別並發送 image_generated SSE event
    return f"IMAGE_URL:{url}"


# ── 主要 dispatch 函式 ──

async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    try:
        if name == "get_current_datetime":
            now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
            return now.strftime("目前時間：%Y-%m-%d %H:%M:%S（台灣時區 UTC+8）")

        if name == "calculate":
            expr = arguments.get("expression", "")
            result = _safe_eval(expr)
            return f"{expr} = {result}"

        if name == "get_weather":
            return await _fetch_weather(arguments.get("city", ""))

        if name == "get_exchange_rate":
            return await _fetch_exchange_rate(
                arguments.get("from_currency", "USD"),
                arguments.get("to_currency", "TWD"),
            )

        if name == "generate_image":
            return await _generate_image(
                arguments.get("prompt", ""),
                arguments.get("size", "1024x1024"),
            )

        return f"未知的工具：{name}"

    except Exception as e:
        return f"工具執行錯誤（{name}）：{e}"
