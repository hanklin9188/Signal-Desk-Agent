# SignalDesk 一次性外部資料與 Release Gate 清單

程式碼與 synthetic verification 已完成。以下項目需要真實 Windows／第三方帳號／發行身分，無法由 Linux workspace 偽造。請一次提供可提供的答案；所有密碼、token、OAuth secret、PFX 密碼都只放在你的本機安全檔案或環境變數，**不要貼到聊天或 commit**。

## 1. Windows 實機

- Windows 11 版本與 OS build。
- Visual Studio 2022 版本；是否已安裝 `.NET desktop development`、Windows App SDK / WinUI 與 MSIX packaging tools。
- `.NET 8 SDK`、Python 3.12 是否已安裝。
- GPU 型號、VRAM、NVIDIA driver/CUDA 版本；設計預設是 RTX 4080 SUPER 16GB，請確認或更正。
- 在專案根目錄執行 `.\scripts\build-windows.ps1 -Configuration Release`，提供完整 build log 與 `native\SignalDesk.Shell\AppPackages` 產物資訊。

## 2. 品牌與 package identity

- 正式產品名稱；未指定則使用 `SignalDesk`。
- Publisher display name 與憑證 Subject/CN。
- Microsoft Store package identity（若走 Store）或確認使用 sideload MSIX。
- 版本號與 release channel（internal/beta/stable）。
- 正式 logo/icon：SVG 或高解析 PNG；若沒有，確認沿用目前紫色 `S` 暫代圖示。
- 支援網址、隱私權政策網址與 publisher 聯絡方式（Store release 需要）。
- Code-signing `.pfx` 的本機路徑或 certificate thumbprint。密碼只放本機安全環境，不要傳送。

## 3. Gmail（至少兩個實際帳號驗收）

Gmail 帳號密碼不是輸入資料，也不可提供給 SignalDesk。只需要 Google Cloud 下載的 Desktop OAuth `credentials.json` 本機路徑，登入與同意都由帳號持有人在 Google 官方網頁完成。

- 已啟用 Gmail API 的 Google Cloud project。
- Desktop OAuth client 的 `credentials.json` 本機絕對路徑；不要貼內容。
- OAuth consent screen 是 Testing 或 Production；若為 Testing，列出已加入的 test users。
- 每個帳號的 SignalDesk alias；目前建議既有 `primary` 對應第一個帳號，第二個使用 `nycu`。
- 每個帳號只讀 `gmail.readonly`，或同時允許確認後建立草稿的 `gmail.compose`。
- 兩個帳號各自完成 OAuth、initial sync、history incremental sync、disconnect/reconnect；有 compose scope 的帳號再做一次「建立 Draft 但不 send」驗收。

## 4. 本機 Qwen

- 使用方式：本機 OpenAI-compatible endpoint，或 app 內 Transformers runtime。
- 精確 model repo、revision/commit 與 quantization；未指定則使用設計值 `Qwen/Qwen3.5-4B`、512 context、non-thinking、text-only，先做 runtime parity test。
- 若模型 gated，將 Hugging Face token 放入本機環境；不要貼 token。
- 可用模型磁碟空間、允許的 GPU 常駐策略，以及遊戲／訓練時是否自動休眠。

## 5. Windows 通知來源

- 允許 SignalDesk 使用 User Notification Listener。
- 已安裝並登入 LINE Desktop；Messenger 使用 Desktop App 或指定 Chrome/Edge profile。
- LINE／Messenger 的 Windows 通知預覽已開啟。
- 最終 allowlist App 顯示名稱；預設為 `LINE, Messenger, Google Chrome, Microsoft Edge`。
- 各提供一筆純文字、群組連續訊息、圖片／貼圖 only 的實際 toast 驗收；不需要把私人內容交給開發者，可在本機自行核對 limitation。

## 6. Optional 官方 webhook

若不需要 LINE Official Account／Messenger Page，直接回覆「兩者皆停用」。若要啟用：

- Public HTTPS webhook base URL/domain 與反向代理方式。
- LINE OA：Channel ID、account alias；Channel Secret 只放 `SIGNALDESK_LINE_CHANNEL_SECRET` 本機環境。
- Meta Page：App ID、Page ID 與 review 狀態；App Secret、Verify Token 只放 `SIGNALDESK_META_APP_SECRET`、`SIGNALDESK_META_VERIFY_TOKEN`。
- Provider console 的 callback URL、event subscriptions 與 signature/redelivery smoke-test 結果。

## 7. 產品預設值

- Timezone；預設 `Asia/Taipei`。
- Quiet hours；預設 `23:00–08:00`。
- Daily Digest；預設 `18:00`。
- Focus Digest interval；預設 60 分鐘。
- Raw retention；預設 7 天。
- 是否登入 Windows 自動啟動；預設關閉、由使用者開啟。
- Shadow Mode 觀察期；建議 7–14 天。
- Light/Dark/System；預設跟隨 Windows。

## 8. 真實資料與 release validation

- 至少 300 筆去識別且人工標註的 locked events，或確認 synthetic gate 只作工程測試、暫不對外 release。
- 7–14 天 Shadow Mode 測試窗口與測試者數量。
- 對誤打斷、漏掉重要訊息、假期限、錯誤 reply/task 的人工 review 結果。
- 若 zero-shot/Qwen 未達 release gate，才授權進行 QLoRA；同時提供合法授權的 training split。未達這個條件不會先訓練。

## 建議回覆格式

```text
Windows/build：
品牌/package：
Gmail work：readonly / compose，credentials 路徑：
Gmail personal：readonly / compose，credentials 路徑：
Qwen runtime/model/revision：
通知 allowlist：
官方 webhooks：停用 / LINE / Meta / 兩者
Timezone / quiet / digest / retention / startup：
MSIX：Store / sideload，憑證路徑：
真實 300-event 與 Shadow Mode 計畫：
```
