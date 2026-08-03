# SignalDesk Windows 與雙 Gmail 完成設定

這份步驟以目前已蒐集到的電腦狀態為準：Windows 11 x64、Python 3.12 與 .NET 8 runtime 已存在，但缺少 .NET 8 SDK、Visual Studio／WinUI workload 與 Windows SDK。RTX 4080 SUPER 可用，但本機 Qwen 不是啟動 App 的必要條件。

## 先做帳號安全處理

SignalDesk 不接受 Gmail 密碼。若密碼曾被貼在聊天或其他非密碼管理器位置，請先到兩個 Google 帳號修改密碼、登出不認識的工作階段並開啟兩步驟驗證。不要把新密碼、OAuth JSON 內容、token 或 PFX 密碼貼回聊天或放進 repository。

## 1. 安裝 Windows 原生 App 建置工具

在專案根目錄開啟 Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows-prerequisites.ps1 -Install
```

腳本會：

- 安裝本專案需要的 .NET 8 SDK；
- 安裝 Windows SDK 10.0.26100（含 XAML／MSIX build tools）；
- 套用 Microsoft 的 WinUI 開發環境設定，安裝 Visual Studio／WinUI／Windows SDK 元件；
- 重新檢查 Python、SDK 與 Visual Studio 狀態。

安裝可能要求系統管理員同意，也會使用數 GB 空間。完成後關閉並重新開啟 PowerShell。

若只想檢查、不安裝：

```powershell
.\scripts\setup-windows-prerequisites.ps1
```

## 2. 在 Google Cloud 建立一次 OAuth client

只需建立一個 Desktop OAuth client，兩個 Gmail 帳號共用它。

1. 開啟 Google Cloud Console，建立或選擇一個專案。
2. 到 API Library 啟用 Gmail API。
3. 到 Google Auth Platform 設定 Branding、Audience 與 Data Access。
4. Audience 選 External，Publishing status 先保留 Testing。
5. 把要連接的兩個 Google 帳號都加入 Test users。學校帳號若被組織政策阻擋，需請 NYCU Google Workspace 管理員允許這個 OAuth app；帳號密碼無法繞過管理政策。
6. 建立 Credentials → OAuth client ID → Application type 選 Desktop app。
7. 下載 JSON；不要打開貼出內容，也不要 commit。

SignalDesk 預設要求 `gmail.readonly`。這是 Google 定義的 restricted scope；Testing 模式可能顯示測試警告、有人數限制，refresh token 也可能只有 7 天，需要重新授權。只有確定要建立 Gmail 雲端草稿時才勾選 compose；Google 的 `gmail.compose` scope 技術上包含寄信權限，但 SignalDesk 的服務明確沒有 send endpoint。

## 3. 安全放置 OAuth JSON

假設檔案下載到 Downloads：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare-gmail-oauth.ps1 `
  -SourcePath "$env:USERPROFILE\Downloads\client_secret_下載檔名.json"
```

腳本只驗證它是 Desktop app OAuth JSON，不會顯示 client secret，並複製到：

```text
%LOCALAPPDATA%\SignalDesk\oauth\credentials.json
```

檔案 ACL 會限制為目前 Windows 使用者與 SYSTEM。也可以不執行這個腳本，直接在 SignalDesk 的原生檔案選擇器選下載檔。

## 4. 在原生桌面 App 連接兩個 Gmail

1. 開啟「訊息來源」。
2. 用既有 `Gmail · personal` 卡片連接第一個帳號。
3. Google 瀏覽器頁面出現後，選擇第一個 Google 帳號並同意權限。
4. 按「新增 Gmail 帳號」，alias 填 `nycu`，使用同一份 `credentials.json`。
5. 第二次 Google 授權時選擇學校帳號。
6. 回到來源頁確認兩張卡片分別顯示 `Connected as ...`，再各按一次「立即同步」。

OAuth token 依 alias 分開儲存在 Windows Credential Manager，不寫入 SQLite。來源頁可隨時「中斷」刪除 token，或「移除」整個帳號設定。

## 5. 建立本機測試簽章並建置 MSIX

先產生與 manifest publisher 完全一致的本機開發憑證：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\new-development-certificate.ps1
```

複製腳本顯示的 thumbprint：

```powershell
.\scripts\build-windows.ps1 -Configuration Release -CertificateThumbprint <THUMBPRINT>
```

接著安裝並啟動原生桌面 App（會顯示一次 UAC 系統管理員確認）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows-package.ps1
```

產物位於 `native\SignalDesk.Shell\bin\x64\Release` 下的 `AppPackages`。安裝腳本會把公開測試憑證加入本機電腦的 Trusted People；這個憑證只適合自己的 Windows 電腦測試。公開發行仍需 Microsoft Store identity／Store signing 或正式 code-signing 服務。

## 現在可以延後的項目

- Qwen：先維持 `rule` 安全規則模式，整個桌面 App、Gmail、通知、Digest、草稿與提醒仍可運作。
- Messenger Desktop：目前可先以 Chrome／Edge 通知預覽使用。
- LINE Official Account／Messenger Page webhook：一般個人帳號不需要，保持停用。
- 正式 Logo、Publisher、Store identity、支援與隱私網址：只在公開發行前需要。
- 300 筆真實標註與 7–14 天 Shadow Mode：是 release validation，不應偽造；安裝後在本機累積。

## 需要本人完成、無法由程式代替的動作

- 變更已暴露的 Google 密碼並開啟兩步驟驗證；
- 在 Google Cloud 建立 OAuth client；
- 在 Google OAuth 頁面分別登入並同意兩個帳號；
- 接受 Windows 的通知存取權限；
- 若學校帳號被管理政策阻擋，聯絡組織管理員。
