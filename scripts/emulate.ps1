# emulate.ps1 — compile the firmware and run the headless Wokwi smoke test.
#
# Prerequisites (one time):
#   arduino-cli with the esp32:esp32 core and libs "DHT sensor library",
#     ArduinoJson, ESP32Servo, U8g2 — anywhere on PATH, or point at it:
#     $env:ARDUINO_CLI = "D:\path\to\arduino-cli.exe"
#   wokwi-cli + WOKWI_CLI_TOKEN (wokwi.com/dashboard/ci) for the smoke run
#   cloudflared on PATH (for the tunnel profile)
#
# Usage:
#   scripts\emulate.ps1 -CompileOnly      # just verify the sketch builds
#   scripts\emulate.ps1                   # compile + headless smoke run
param(
  [switch]$CompileOnly,
  [int]$SmokeSeconds = 45
)

$ErrorActionPreference = "Stop"
$fw = Join-Path $PSScriptRoot "..\firmware\grok_guardian"

function Find-Tool([string]$name, [string]$envVar, [string[]]$fallbacks) {
  if ($envVar -and (Test-Path $envVar)) { return $envVar }
  $onPath = Get-Command $name -ErrorAction SilentlyContinue
  if ($onPath) { return $onPath.Source }
  foreach ($f in $fallbacks) { if (Test-Path $f) { return $f } }
  throw "$name not found. Install it or set `$env:$($envVar -replace 'env:','') — see comment header."
}

$arduinoCli = Find-Tool "arduino-cli" $env:ARDUINO_CLI @(
  (Join-Path $PSScriptRoot "..\tools\arduino-cli\arduino-cli.exe"),
  "D:\tmp\arduino-cli\arduino-cli.exe"
)
Write-Host "arduino-cli: $arduinoCli"

if (-not (Test-Path (Join-Path $fw "config.h"))) {
  Write-Host "Creating config.h from config.h.example — edit it before a live run."
  Copy-Item (Join-Path $fw "config.h.example") (Join-Path $fw "config.h")
}

Write-Host "== compile =="
& $arduinoCli compile --fqbn esp32:esp32:esp32 --output-dir (Join-Path $fw "build") $fw
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "compile OK"
if ($CompileOnly) { exit 0 }

$wokwiCli = Find-Tool "wokwi-cli" $env:WOKWI_CLI @()

Write-Host "== headless smoke run ($SmokeSeconds s) =="
Write-Host "Expect serial markers: '[gg] boot', WiFi connect, '[gg] heartbeat ack'"
$logPath = Join-Path $fw "build\smoke.log"
$proc = Start-Process $wokwiCli -ArgumentList "`"$fw`"" -NoNewWindow -PassThru `
  -RedirectStandardOutput $logPath
Start-Sleep -Seconds $SmokeSeconds
if (-not $proc.HasExited) { Stop-Process $proc -Force }

$log = Get-Content $logPath -Raw
$checks = @("[gg] boot", "heartbeat ack")
$failed = $checks | Where-Object { $log -notmatch [regex]::Escape($_) }
if ($failed) {
  Write-Host "SMOKE FAILED — missing markers: $($failed -join ', ')"
  exit 1
}
Write-Host "SMOKE OK — boot + heartbeat observed"
