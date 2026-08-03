# Deployment

## 1. Development Environment

- Windows 11 host。
- RTX 4080 SUPER 16GB。
- WSL 可用於 Python training，但 Windows notification listener 必須在 Windows native process。
- Native shell 使用 Visual Studio / Windows App SDK。
- Python service 可在 Windows 或 WSL；production 建議 Windows native loopback，降低跨環境路徑問題。

## 2. Model Runtime

### Baseline

Transformers direct inference：

- correctness first；
- single-user；
-短 queue。

### Serving Engine

需求出現後再測：

- vLLM；
- SGLang；
- model-specific compatible runtime。

不得假設新 architecture 在所有 quantization/runtime 已完整支援；每個 backend 必須有 parity test。

## 3. Config

```text
context=512
input<=384
output<=128
thinking=false
text-only
```

## 4. GPU Modes

### Always-on

- model resident；
- lowest latency。

### Scheduled

- only during work hours。

### Auto-sleep

- unload after idle；
- queue events；
- batch on wake。

### Pause

- gaming/training detected or manual hotkey；
- rules continue；
- model queue persists。

## 5. Packaging

### One-command Windows build

第一次在 Windows 準備工具鏈：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows-prerequisites.ps1 -Install
```

安裝完成後重新開啟 PowerShell。若只在自己的電腦安裝測試，建立僅供開發的本機憑證：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\new-development-certificate.ps1
```

記下腳本顯示的 thumbprint，再執行：

```powershell
.\scripts\build-windows.ps1 -Configuration Release -CertificateThumbprint <THUMBPRINT>
```

建置完成後，用一般 PowerShell 執行下列指令；腳本會顯示一次 UAC 系統管理員確認、把公開測試憑證加入本機電腦的 Trusted People，安裝相依套件與 MSIX，最後啟動 SignalDesk：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows-package.ps1
```

只編譯、不產生可安裝簽章時可執行：

在 Windows PowerShell 執行：

```powershell
.\scripts\build-windows.ps1 -Configuration Release
```

腳本會建立 Python 3.12 環境、封裝 `service\signaldesk.exe`、產生 package assets、編譯 WinUI shell 並輸出 MSIX/Appx bundle。若要正式簽章，額外傳入憑證路徑；憑證密碼只可透過本機安全管道提供，不可提交到 repository。

`new-development-certificate.ps1` 不會產生含私鑰的 PFX 檔；`install-windows-package.ps1` 只把公開測試憑證加入本機電腦的 Trusted People。公開發行時改用 Microsoft Store signing 或正式 code-signing identity，不可沿用 `CN=SignalDesk.Development`；完成開發後可依 thumbprint 移除這個本機測試憑證。

### v0.x

- developer scripts；
- native shell；
- Python environment；
- separate model setup。

### v1.0

- MSIX shell；
- signed binaries；
- embedded/local service；
- first-run wizard；
- model checksum；
- update channel；
- uninstall data choice。

正式 UI 是原生 WinUI，不以 WebView 或瀏覽器作主介面。本機 FastAPI 網頁只保留作診斷工具。

## 6. Health

Endpoints：

```text
/healthz
/readyz
/connectors
/model/health
/metrics
```

No private content in health output.

## 7. Backup / Export

- settings export；
- rules export；
- anonymized feedback export；
- raw messages excluded by default。
