param(
    [switch]$SkipModelDownload,
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
$runtimeRoot = Join-Path $env:LOCALAPPDATA "SignalDesk\model-runtime"
$venvRoot = Join-Path $runtimeRoot ".venv"
$python = Join-Path $venvRoot "Scripts\python.exe"
$hfHome = Join-Path $env:LOCALAPPDATA "SignalDesk\models"
$diagnostics = Join-Path $env:LOCALAPPDATA "SignalDesk\diagnostics\models"
$qwenModel = "Qwen/Qwen3.5-4B"
$qwenRevision = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
$ocrModel = "PaddlePaddle/PaddleOCR-VL-1.6"
$ocrRevision = "66317acc4c9fc17bd154591ce650735cd2855f3e"

New-Item -ItemType Directory -Force -Path $runtimeRoot, $hfHome, $diagnostics | Out-Null
if (-not (Test-Path $python)) {
    py -3.12 -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 model runtime creation failed." }
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $python -m pip install --index-url https://download.pytorch.org/whl/cu130 torch torchvision
if ($LASTEXITCODE -ne 0) { throw "CUDA PyTorch installation failed." }
$installTarget = "$projectRoot[model,vision,quantization,gmail]"
& $python -m pip install --upgrade $installTarget
if ($LASTEXITCODE -ne 0) { throw "SignalDesk model dependencies installation failed." }

$env:HF_HOME = $hfHome
$env:HF_HUB_DISABLE_TELEMETRY = "1"
& $python -c "import json,torch; assert torch.cuda.is_available(), 'CUDA unavailable'; print(json.dumps({'cuda': True, 'gpu': torch.cuda.get_device_name(0), 'torch': torch.__version__}))"
if ($LASTEXITCODE -ne 0) { throw "CUDA verification failed." }

if (-not $SkipModelDownload) {
    & $python -c "from huggingface_hub import snapshot_download; snapshot_download('$qwenModel', revision='$qwenRevision'); snapshot_download('$ocrModel', revision='$ocrRevision')"
    if ($LASTEXITCODE -ne 0) { throw "Model download failed." }
}

$runtimeConfig = [ordered]@{
    SIGNALDESK_MODEL_BACKEND = "transformers"
    SIGNALDESK_MODEL_ID = $qwenModel
    SIGNALDESK_MODEL_REVISION = $qwenRevision
    SIGNALDESK_VISION_BACKEND = "paddleocr-vl"
    SIGNALDESK_OCR_MODEL_ID = $ocrModel
    SIGNALDESK_OCR_MODEL_REVISION = $ocrRevision
}
$runtimeConfig | ConvertTo-Json | Set-Content `
    -LiteralPath (Join-Path $runtimeRoot "runtime.json") -Encoding UTF8

if (-not $SkipSmokeTest) {
    $sample = Join-Path $projectRoot "benchmarks\multimodal\assets\mm-001.png"
    & $python -m signaldesk.model_benchmark --family qwen --model $qwenModel `
        --revision $qwenRevision --image $sample --quantization bf16 `
        --warmup 0 --iterations 1 --max-new-tokens 96 `
        --expected-text "Aug 9, 2026" `
        --output (Join-Path $diagnostics "qwen3.5-4b-bf16.json")
    if ($LASTEXITCODE -ne 0) { throw "Qwen smoke test failed." }
    & $python -m signaldesk.model_benchmark --family paddle --model $ocrModel `
        --revision $ocrRevision --image $sample --quantization bf16 `
        --warmup 0 --iterations 1 --max-new-tokens 128 `
        --expected-text "Aug 9, 2026" `
        --output (Join-Path $diagnostics "paddleocr-vl-1.6-bf16.json")
    if ($LASTEXITCODE -ne 0) { throw "PaddleOCR-VL smoke test failed." }
}

Write-Host "SignalDesk Windows model runtime is ready."
Write-Host "Runtime: $runtimeRoot"
Write-Host "Models: $hfHome"
