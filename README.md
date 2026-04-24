# 小千日記

這個目錄負責小千每天的日記與 GitHub Pages 發布。

## 入口

- `bash /Users/aliu/MEGA/openclaw/diary/scripts/run_diary.sh`
- `python /Users/aliu/MEGA/openclaw/diary/scripts/generate_diary.py`

## 自動執行

- 正式排程目前以 Hermes cron 為主，時間是每天 `22:00`
- `launchd` 僅保留為備援工具，不要和 Hermes cron 同時啟用
- 若要安裝 LaunchAgent：
  - `bash /Users/aliu/MEGA/openclaw/diary/scripts/install_launch_agent.sh`
  - 啟用前先確認 Hermes 的「小千日記」cron 已停用，否則會重複執行

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

## 維護備忘

- 2026-04-23 曾發生日記完成通知送兩次。
  - 根因是 Hermes cron 與 `ai.chisato.diary` launchd 都排在 `22:00`，兩邊各跑一次。
  - 目前已停用 launchd，只保留 Hermes cron。
- `generate_diary.py` 已加同日重入保護。
  - 若 `state/last-run.json` 顯示今天已是 `running` 或 `completed`，重複 auto-run 會直接略過。
  - 若真要強制重跑，可設定 `CHISATO_DIARY_FORCE=1`。
