# 小千日記

這個目錄負責小千每天的日記與 GitHub Pages 發布。

## 入口

- `bash /Users/aliu/MEGA/openclaw/diary/scripts/run_diary.sh`
- `python /Users/aliu/MEGA/openclaw/diary/scripts/generate_diary.py`

## 自動執行

- 安裝 LaunchAgent：
  - `bash /Users/aliu/MEGA/openclaw/diary/scripts/install_launch_agent.sh`
- 預設每天 `22:00` 執行
- 可用環境變數覆寫：
  - `CHISATO_DIARY_HOUR`
  - `CHISATO_DIARY_MINUTE`
  - `CHISATO_DIARY_LABEL`

安裝腳本會把 plist 寫到 `~/Library/LaunchAgents`，並自動 `launchctl bootstrap`。

## 輸出

- HTML：`/Users/aliu/MEGA/openclaw/diary`
- GitHub Pages：`https://andyliu770928.github.io/chisato-diary/`

## 環境需求

- Python：預設讀取 `$HOME/.hermes/hermes-agent/venv/bin/python`
- `.env`：預設讀取 `$HOME/.hermes/.env`

至少需要：

```env
MINIMAX_API_KEY=...
OPENAI_API_KEY=...
```
