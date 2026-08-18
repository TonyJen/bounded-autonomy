# emulate.ps1 — compile the firmware and run the headless Wokwi smoke test.
#
# Prerequisites (one time):
#   winget install Arduino.CLI            (or download arduino-cli zip)
#   arduino-cli core install esp32:esp32  (needs the espressif index URL)
#   arduino-cli lib install "DHT sensor library" ArduinoJson ESP32Servo U8g2
#   wokwi-cli on PATH + WOKWI_CLI_TOKEN set (wokwi.com/dashboard/ci)
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

if (-not (Test-Path (Join-Path $fw "config.h"))) {
  Write-Host "Creating config.h from config.h.example — edit it before a live run."
  Copy-Item (Join-Path $fw "config.h.example") (Join-Path $fw "config.h")
}

Write-Host "== compile =="
arduino-cli compile --fqbn esp32:esp32:esp32 --output-dir (Join-Path $fw "build") $fw
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "compile OK"
if ($CompileOnly) { exit 0 }

Write-Host "== headless smoke run ($SmokeSeconds s) =="
Write-Host "Expect serial markers: '[gg] boot', WiFi connect, '[gg] heartbeat ack'"
$proc = Start-Process wokwi-cli -ArgumentList $fw -NoNewWindow -PassThru `
  -RedirectStandardOutput (Join-Path $fw "build\smoke.log")
Start-Sleep -Seconds $SmokeSeconds
if (-not $proc.HasExited) { Stop-Process $proc -Force }

$log = Get-Content (Join-Path $fw "build\smoke.log") -Raw
$checks = @("[gg] boot", "heartbeat ack")
$failed = $checks | Where-Object { $log -notmatch [regex]::Escape($_) }
if ($failed) {
  Write-Host "SMOKE FAILED — missing markers: $($failed -join ', ')"
  exit 1
}
Write-Host "SMOKE OK — boot + heartbeat observed"
