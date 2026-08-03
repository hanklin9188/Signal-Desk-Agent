[CmdletBinding()]
param(
    [ValidateSet("Triage", "Ocr", "ImagePipeline", "All")]
    [string]$Suite = "All",
    [string]$Version = "development"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
$runtimeRoot = Join-Path $env:LOCALAPPDATA "SignalDesk\model-runtime"
$python = Join-Path $runtimeRoot ".venv\Scripts\python.exe"
$env:HF_HOME = Join-Path $env:LOCALAPPDATA "SignalDesk\models"
$env:HF_HUB_DISABLE_TELEMETRY = "1"
$qwenRevision = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
$ocrRevision = "66317acc4c9fc17bd154591ce650735cd2855f3e"

if (-not (Test-Path $python)) {
    throw "SignalDesk model runtime is missing. Run setup-windows-model-runtime.ps1 first."
}

$outputRoot = Join-Path $projectRoot "runs"
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

if ($Suite -in @("Triage", "All")) {
    & $python (Join-Path $PSScriptRoot "benchmark-triage-model.py") `
        --dataset (Join-Path $projectRoot "benchmarks\calibration\triage.yaml") `
        --output (Join-Path $outputRoot "qwen-triage-$Version.json") `
        --model "Qwen/Qwen3.5-4B" --revision $qwenRevision --quantization nf4
    if ($LASTEXITCODE -ne 0) { throw "Qwen triage calibration failed." }
}

if ($Suite -in @("Ocr", "All")) {
    & $python (Join-Path $PSScriptRoot "benchmark-ocr-model.py") `
        --manifest (Join-Path $projectRoot "benchmarks\multimodal\manifest.jsonl") `
        --root (Join-Path $projectRoot "benchmarks\multimodal") `
        --no-text-image (Join-Path $projectRoot "benchmarks\calibration\no-text-photo.png") `
        --output (Join-Path $outputRoot "ocr-$Version.json") `
        --model "PaddlePaddle/PaddleOCR-VL-1.6" --revision $ocrRevision
    if ($LASTEXITCODE -ne 0) { throw "PaddleOCR-VL calibration failed." }
}

if ($Suite -in @("ImagePipeline", "All")) {
    & $python (Join-Path $PSScriptRoot "benchmark-image-pipeline.py") `
        --project-root $projectRoot `
        --output (Join-Path $outputRoot "image-pipeline-$Version.json")
    if ($LASTEXITCODE -ne 0) { throw "Sequential image pipeline calibration failed." }
}

Write-Host "Privacy-safe calibration completed: $outputRoot"
