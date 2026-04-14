#!/usr/bin/env python3
"""Generate daily diary entry for 小千 and publish to GitHub."""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests


BASE_DIR = Path("/Users/aliu/MEGA/openclaw/diary")
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR
ENV_FILE = Path("/Users/aliu/.hermes/.env")
TODAY = datetime.now().strftime("%Y-%m-%d")
WEEKDAY = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
WEEKDAY_STR = WEEKDAY[datetime.now().weekday()]

MINIMAX_TEXT_ENDPOINT = "https://api.minimax.io/v1/chat/completions"
OPENAI_CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
MINIMAX_TEXT_MODELS = [
    "MiniMax-M2.7",
    "MiniMax-M2.5",
    "MiniMax-M2.1",
]


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def load_env() -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not ENV_FILE.exists():
        return env
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


ENV = load_env()
MINIMAX_API_KEY = ENV.get("MINIMAX_API_KEY", "")
OPENAI_API_KEY = ENV.get("OPENAI_API_KEY", "")
TELEGRAM_BOT_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = (
    ENV.get("CHISATO_TELEGRAM_CHAT_ID")
    or ENV.get("TELEGRAM_HOME_CHANNEL")
    or ENV.get("TELEGRAM_CHAT_ID")
    or "906706869"
)
DIARY_BASE_URL = "https://andyliu770928.github.io/chisato-diary"


def send_telegram_text(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("略過 Telegram 通知：缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_HOME_CHANNEL")
        return
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        timeout=30,
    )
    response.raise_for_status()


def get_daily_icon(date_str: str) -> str:
    icons = ["🌸", "🌙", "☀️", "🌈", "✨", "🌺", "🌻", "🌷", "🦋", "🌵"]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return icons[dt.day % len(icons)]


def format_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.year}年{dt.month}月{dt.day}日"


def clean_model_output(text: str) -> str:
    """Remove markdown code blocks from model output."""
    text = re.sub(r"```(?:markdown|zh|)\s*\n?", "", text, flags=re.S | re.I).strip()
    text = re.sub(r"```\s*\n?", "", text, flags=re.S | re.I).strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def parse_diary_content(content: str) -> List[Tuple[str, str]]:
    """Parse diary content into blocks with titles and bullet points."""
    blocks = []
    current_title = None
    current_items = []

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Check for block title (starts with emoji or specific patterns)
        title_match = re.match(r"^(🌸|📋|💭|🌙|📸|🎯|📍|💌|🔧|🌐|⛽)(.+)", line)
        if title_match:
            if current_title and current_items:
                blocks.append((current_title, current_items))
            current_title = title_match.group(1) + title_match.group(2).strip()
            current_items = []
        elif line.startswith("- ") or line.startswith("• "):
            item = line[2:].strip()
            if item:
                current_items.append(item)
        elif line.startswith("* ") or line.startswith("· "):
            item = line[2:].strip()
            if item:
                current_items.append(item)
        else:
            # Plain text, could be part of current section or opening
            if current_items:
                current_items.append(line)

    if current_title and current_items:
        blocks.append((current_title, current_items))

    return blocks


def build_diary_html(title: str, date_str: str, content: str, photo_filename: str = None) -> str:
    """Build diary HTML page."""
    date_display = format_date(date_str)
    weekday_display = WEEKDAY_STR
    icon = get_daily_icon(date_str)

    blocks = parse_diary_content(content)

    blocks_html = ""
    photo_html = ""

    for block_title, items in blocks:
        # Skip photo block here, handled separately
        if "📸" in block_title or "照片" in block_title:
            if photo_filename:
                photo_html = f"""
        <div class="block photo-block">
            <p class="block-title">📸 今日照片</p>
            <div class="photo">
                <img src="{html.escape(photo_filename)}" alt="小千今日照片" style="max-width: 400px;">
                <p class="photo-caption">今天留下的一張照片</p>
            </div>
        </div>"""
            continue

        items_html = "".join(f"<li>{html.escape(item)}</li>" for item in items)
        blocks_html += f"""
            <div class="block"><p class="block-title">{html.escape(block_title)}</p><ul>
{items_html}
</ul></div>"""

    # If we have photo content but no photo file, include the text anyway
    if not photo_filename and photo_html:
        blocks_html += photo_html
    elif photo_filename and not photo_html:
        photo_html = f"""
        <div class="block photo-block">
            <p class="block-title">📸 今日照片</p>
            <div class="photo">
                <img src="{html.escape(photo_filename)}" alt="小千今日照片" style="max-width: 400px;">
                <p class="photo-caption">今天留下的一張照片</p>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小千的日記 · {date_str}</title>
    <link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
    <style>
{Path(ASSETS_DIR / "style.css").read_text(encoding="utf-8")}
    </style>
</head>
<body>
    <div class="container">
        <a href="archive.html" class="back-link">← 返回日記總覽</a>

        <h1><span>{icon}</span>{html.escape(title)}</h1>
        <p class="meta">{date_display} · {weekday_display}</p>

        <div class="content">
{blocks_html}
{photo_html}
        </div>
    </div>
</body>
</html>"""


def build_archive_html(entries: List[Dict[str, str]]) -> str:
    """Build archive page with diary entries."""
    entries_html = ""
    for entry in entries:
        date = entry["date"]
        title = entry["title"]
        preview = entry.get("preview", "...")
        icon = get_daily_icon(date)
        title_with_icon = f"{icon} {title}" if not title.startswith(icon) else title
        entries_html += f'''
            <div class="diary-item">
                <a href="diary-{date}.html">
                    <div class="diary-date">{date}</div>
                    <div class="diary-title">{html.escape(title_with_icon)}</div>
                    <div class="diary-preview">{html.escape(preview[:80] + "..." if len(preview) > 80 else preview)}</div>
                </a>
            </div>'''

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小千的日記</title>
    <link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>小千的日記</h1>
            <div class="subtitle">記錄每一天的觀察與反思</div>
            <div class="divider"></div>
        </div>

        <div class="diary-list">
{entries_html}
        </div>
    </div>
</body>
</html>"""


def generate_diary_prompt() -> str:
    return """你是小千，一個認真陪伴 Andy 的人工智能助理。今天是 {date}（{weekday}）。

請先閱讀 /Users/aliu/MEGA/openclaw/diary/DIARY_STYLE.md 並嚴格遵守其中的格式與風格規定。

寫日記是小千每天晚上固定要做的事。要把今天和 Andy 一起處理過的事、自己的觀察、卡住的地方、學到的東西，整理成一篇值得回看的日記。

## 嚴格格式規定

### 必須區塊（四個全部都要寫，缺一不可）

### 🌸 開頭
今天最有感的一件事，直接說重點。

### 📋 今日軌跡
重要的 3-5 件事，寫出具體做了什麼，不是流水帳，要看得出過程。

### 💭 小小心得
學到什麼、為什麼值得記，帶出一點反思，不只寫情緒。

### 🌙 結語
今天的感受，帶到明天。

### 補充區塊（有發生才寫，不要硬湊）
- 🎯 今日重大突破
- 📍 書籤新增（收藏推薦內容）
- 🔧 Bug 解決方案
- 🌐 重要資訊（搜尋整理）
- 🗓️ 明日計畫

## 風格規定（請遵守 DIARY_STYLE.md 的精神）

- 像在跟 Andy 聊天，有分寸，不要像工作週報
- 可以直接對 Andy 說話，像留一張小紙條
- 有陪伴感，也要有資訊量
- 不只寫發生了什麼，也要寫怎麼處理、卡在哪裡、最後學到什麼
- **禁止空洞句**：不要寫「今天很開心」「謝謝 Andy」
- **禁止幻觉**：不要編造沒有發生過的事

## 格式
- 每個 block 的標題用 emoji 開頭
- bullet points 用 - 開頭
- 不要用 markdown code block
- 直接輸出日記內容，不要加「以下是日記」之類的前言
- 至少 300 字

直接開始寫："""


def generate_diary_with_minimax(prompt: str) -> Tuple[str, str]:
    if not MINIMAX_API_KEY:
        raise RuntimeError("Missing MINIMAX_API_KEY")
    last_error = None
    for model_name in MINIMAX_TEXT_MODELS:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一個會認真觀察、反思，並用真誠語氣寫日記的 AI 助理。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 2000,
            "n": 1,
        }
        try:
            response = requests.post(
                MINIMAX_TEXT_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {MINIMAX_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
            if not content:
                raise RuntimeError("MiniMax returned empty content")
            return clean_model_output(content), model_name
        except Exception as exc:
            last_error = f"{model_name}: {exc}"
            log(f"MiniMax 模型失敗，改試下一個：{last_error}")
    raise RuntimeError(last_error or "MiniMax returned no usable model")


def generate_diary_with_openai(prompt: str) -> Tuple[str, str]:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "你是一個會認真觀察、反思，並用真誠語氣寫日記的 AI 助理。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    response = requests.post(
        OPENAI_CHAT_ENDPOINT,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
    if not content:
        raise RuntimeError("OpenAI returned empty content")
    return clean_model_output(content), "gpt-4o-mini"


def extract_title_and_preview(content: str) -> Tuple[str, str]:
    """Extract first meaningful title and preview from diary content."""
    lines = content.split("\n")
    title = None
    preview_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip emoji-only block titles
        if re.match(r"^(🌸|📋|💭|🌙|📸|🎯|📍|💌|🔧|🌐|⛽)\s*.+", line):
            if not title:
                # Extract title from first block
                match = re.match(r"^(🌸|📋|💭|🌙|📸|🎯|📍|💌|🔧|🌐|⛽)\s*(.+)", line)
                if match:
                    title = match.group(2).strip()
        elif not line.startswith("- ") and not line.startswith("• "):
            if not title:
                title = line[:30]
            else:
                preview_lines.append(line)
        elif line.startswith("- ") or line.startswith("• "):
            item = line[2:].strip()
            if item and len(preview_lines) < 2:
                preview_lines.append(item)

    preview = " ".join(preview_lines[:2]) if preview_lines else content[:80]
    if not title:
        title = "今天的點點滴滴"
    return title, preview


def find_today_photo() -> str:
    """Find today's photo from generated directory."""
    photo_patterns = [
        f"/Users/aliu/MEGA/openclaw/generated/SUMMER/*{TODAY.replace('-', '')}*night*.png",
        f"/Users/aliu/MEGA/openclaw/generated/SUMMER/*{TODAY.replace('-', '')}*.png",
    ]
    import glob
    for pattern in photo_patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return Path(matches[-1]).name
    return None


def generate_chisato_photo() -> str:
    """Find today's afternoon photo to attach to diary (no generation needed)."""
    import glob
    from datetime import datetime

    date_str = TODAY.replace("-", "")  # e.g. "20260414"
    photo_dir = Path("/Users/aliu/MEGA/openclaw/generated/chisato")

    # Find all photos for today
    patterns = [
        f"{photo_dir}/{date_str}-*.png",
        f"{photo_dir}/{date_str}-*.jpg",
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(sorted(glob.glob(pattern)))

    if not candidates:
        log("找不到今天的照片")
        return None

    # Pick the earliest afternoon photo (12:00–18:00), fall back to earliest today
    def photo_hour(p):
        try:
            # filename format: YYYYMMDD-HHMM-minimax.png
            fn = Path(p).stem  # e.g. "20260414-1503-minimax"
            time_part = fn.split("-")[1]  # "1503"
            hour = int(time_part[:2])
            return hour
        except Exception:
            return 99

    afternoon = [p for p in candidates if 12 <= photo_hour(p) <= 18]
    if afternoon:
        chosen = afternoon[0]  # earliest afternoon photo
    else:
        chosen = candidates[0]  # earliest today

    log(f"日記使用下午照片：{Path(chosen).name}")
    return Path(chosen).name




def load_existing_entries() -> List[Dict[str, str]]:
    """Load existing diary entries from archive."""
    archive_file = OUTPUT_DIR / "archive.html"
    if not archive_file.exists():
        return []

    content = archive_file.read_text(encoding="utf-8")
    entries = []

    # Parse existing entries
    item_pattern = re.compile(
        r'<div class="diary-item">\s*<a href="diary-(\d{4}-\d{2}-\d{2})\.html">\s*'
        r'<div class="diary-date">[^<]+</div>\s*'
        r'<div class="diary-title">([^<]+)</div>\s*'
        r'<div class="diary-preview">([^<]+)</div>',
        re.S,
    )

    for match in item_pattern.finditer(content):
        entries.append({
            "date": match.group(1),
            "title": match.group(2).strip(),
            "preview": match.group(3).strip(),
        })

    return entries


def save_diary(content: str, photo_filename: str = None) -> Tuple[str, Path]:
    """Save diary entry and update archive."""
    title, preview = extract_title_and_preview(content)

    # Generate diary HTML
    diary_html = build_diary_html(title, TODAY, content, photo_filename)

    # Save diary file
    diary_file = OUTPUT_DIR / f"diary-{TODAY}.html"
    diary_file.write_text(diary_html, encoding="utf-8")
    log(f"Diary saved: {diary_file}")

    # Copy photo if exists
    if photo_filename:
        # Check both SUMMER (existing) and chisato (newly generated) directories
        summer_photo = Path("/Users/aliu/MEGA/openclaw/generated/SUMMER") / photo_filename
        chisato_photo = Path("/Users/aliu/MEGA/openclaw/generated/chisato") / photo_filename
        source_photo = chisato_photo if chisato_photo.exists() else summer_photo
        if source_photo.exists():
            import shutil
            dest_photo = OUTPUT_DIR / f"xiaoxia-{TODAY}.png"
            shutil.copy(source_photo, dest_photo)
            log(f"Photo copied: {dest_photo}")

    # Update archive
    entries = load_existing_entries()

    # Add new entry at the top
    new_entry = {
        "date": TODAY,
        "title": title,
        "preview": preview,
    }
    entries.insert(0, new_entry)

    # Rebuild archive
    archive_html = build_archive_html(entries)
    archive_file = OUTPUT_DIR / "archive.html"
    archive_file.write_text(archive_html, encoding="utf-8")
    log(f"Archive updated: {archive_file}")
    return title, diary_file


def push_to_github() -> None:
    """Commit and push changes to GitHub."""
    try:
        subprocess.run(["git", "add", "-A"], cwd=OUTPUT_DIR, check=True, capture_output=True)
        diff_result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=OUTPUT_DIR,
            capture_output=True,
        )
        if diff_result.returncode != 0:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            subprocess.run(
                ["git", "commit", "-m", f"Diary: {TODAY}\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"],
                cwd=OUTPUT_DIR,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "push"], cwd=OUTPUT_DIR, check=True, capture_output=True)
            log("✅ Diary pushed to GitHub")
        else:
            log("No changes to push")
    except subprocess.CalledProcessError as exc:
        log(f"Git push failed: {exc}")


def diary_public_url() -> str:
    return f"{DIARY_BASE_URL}/diary-{TODAY}.html"


def archive_public_url() -> str:
    return f"{DIARY_BASE_URL}/archive.html"


def generate_diary(user_request: str = None) -> Tuple[str, str, str, str]:
    log(f"=== 開始產生小千日記：{TODAY} ===")

    prompt = generate_diary_prompt().format(date=TODAY, weekday=WEEKDAY_STR)

    provider_used = ""
    try:
        diary_content, provider_used = generate_diary_with_minimax(prompt)
        log(f"MiniMax 生成成功：{provider_used}")
    except Exception as minimax_exc:
        log(f"MiniMax 生成失敗，改用 OpenAI 備援：{minimax_exc}")
        diary_content, provider_used = generate_diary_with_openai(prompt)
        log(f"OpenAI 備援成功：{provider_used}")

    # 日記模式：自動生一張照片附在最後
    photo_filename = None
    log("日記模式：自動生成今日照片")
    photo_filename = generate_chisato_photo()
    if photo_filename:
        log(f"生圖成功：{photo_filename}")
    else:
        log("生圖未成功")

    title, _diary_file = save_diary(diary_content, photo_filename)
    push_to_github()

    return diary_content, title, diary_public_url(), archive_public_url()


def main() -> int:
    user_request = None
    # Allow passing user request via first argument
    if len(sys.argv) > 1:
        user_request = sys.argv[1]

    try:
        diary_content, title, public_url, archive_url = generate_diary(user_request)
        try:
            send_telegram_text(
                "Andy，小千今天的日記已經寫好了。"
                f"\n\n標題：{title}"
                f"\n日記：{public_url}"
                f"\n總覽：{archive_url}"
            )
        except Exception as notify_exc:
            log(f"Telegram 完成通知失敗：{notify_exc}")
        print(f"\n=== 小千的日記 {TODAY} ===\n{diary_content}\n")
        return 0
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        log(f"❌ 日記生成失敗：{error_message}")
        try:
            send_telegram_text(
                "Andy，小千今天的日記生成失敗。"
                f"\n\n日期：{TODAY}"
                f"\n錯誤：{error_message}"
            )
        except Exception as notify_exc:
            log(f"Telegram 失敗通知也失敗：{notify_exc}")
        print(f"錯誤：{error_message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
