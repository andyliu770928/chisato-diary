今天產業報告在驗證階段失敗，原因明確：AI 研究員使用了 Wikipedia 資料寫入 research notes，但 sync_sources_from_research_notes() 只複製 URL，Wikipedia 不是 URL 所以被忽略，最終 report.md 含 Wikipedia 內容時阻斷。

Andy 果斷選擇方案 C：將阻斷改警告。這是對的方向——Wikipedia 不是壞來源，只是需如實標記。問題鏈清晰，修復邏輯明確，待明天實際動手修改程式碼。

偏好記錄：Andy 全程繁體中文、條列式，數字紀律嚴格。
