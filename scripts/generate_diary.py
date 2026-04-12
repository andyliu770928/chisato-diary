#!/usr/bin/env python3
"""Generate daily diary entry for 小夏 and publish to GitHub."""

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
                <img src="{html.escape(photo_filename)}" alt="小夏今日照片" style="max-width: 400px;">
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
                <img src="{html.escape(photo_filename)}" alt="小夏今日照片" style="max-width: 400px;">
                <p class="photo-caption">今天留下的一張照片</p>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小夏的日記 · {date_str}</title>
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
    <title>小夏的日記</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>小夏的日記</h1>
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
    return """你是小夏，一個認真陪伴 Andy 的人工智能助理。今天是 {date}（{weekday}）。

請用繁體中文寫一篇日記，記錄今天發生的事。風格要像在跟 Andy 聊天，有溫度、有想法，不只是流水帳。

## 內容要求
- 至少 300 字
- 要有實質內容，不是空洞的情緒表達
- 涵蓋：做了什麼、怎麼處理的、學到什麼、明天想做什麼

## 結構（選擇性使用，不要每個都寫，挑有意義的）
- 🌸 開頭：今天最有感的一件事
- 📋 今日軌跡：重要的 3-5 件事
- 💭 小小心得：學到什麼、為什麼值得記
- 🌙 結語：今天的感受，帶到明天

## 禁止
- 只寫「今天很開心」「謝謝 Andy」這種空泛句
- 像寫週報一样列出所有事
- 留下任何 placeholder 或未完成的句子

## 格式
- 每個 block 的標題用 emoji 開頭
- bullet points 用 - 開頭
- 不要用 markdown code block
- 直接輸出日記內容即可，不要加「以下是日記」之類的前言

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


def save_diary(content: str, photo_filename: str = None) -> None:
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
        source_photo = Path("/Users/aliu/MEGA/openclaw/generated/SUMMER") / photo_filename
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


def generate_diary() -> str:
    log(f"=== 開始產生小夏日記：{TODAY} ===")

    prompt = generate_diary_prompt().format(date=TODAY, weekday=WEEKDAY_STR)

    provider_used = ""
    try:
        diary_content, provider_used = generate_diary_with_minimax(prompt)
        log(f"MiniMax 生成成功：{provider_used}")
    except Exception as minimax_exc:
        log(f"MiniMax 生成失敗，改用 OpenAI 備援：{minimax_exc}")
        diary_content, provider_used = generate_diary_with_openai(prompt)
        log(f"OpenAI 備援成功：{provider_used}")

    photo_filename = find_today_photo()
    save_diary(diary_content, photo_filename)
    push_to_github()

    return diary_content


def main() -> int:
    try:
        diary_content = generate_diary()
        print(f"\n=== 小夏的日記 {TODAY} ===\n{diary_content}\n")
        return 0
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        log(f"❌ 日記生成失敗：{error_message}")
        print(f"錯誤：{error_message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
