# run_tests.ps1 — compile and run the firmware host unit tests.
#
# Uses any C++17 compiler: zig c++, g++, or clang++. Set $env:CXX to point
# at one explicitly, or rely on PATH / known fallbacks.
# ArduinoJson comes from the arduino-cli sketchbook (override with
# $env:ARDUINOJSON).
param()

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$fw = Join-Path $here "..\grok_guardian"

$cxx = $null
foreach ($candidate in @($env:CXX, "zig", "g++", "clang++")) {
  if (-not $candidate) { continue }
  $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
  if ($cmd) { $cxx = $cmd.Source; break }
  if (Test-Path $candidate) { $cxx = $candidate; break }
}
if (-not $cxx) {
  $fallback = "D:\tmp\zig-x86_64-windows-0.15.2\zig.exe"
  if (Test-Path $fallback) { $cxx = $fallback }
}
if (-not $cxx) { throw "No C++ compiler found (tried zig, g++, clang++)." }

$aj = if ($env:ARDUINOJSON) { $env:ARDUINOJSON } else {
  Join-Path $env:USERPROFILE "Documents\Arduino\libraries\ArduinoJson\src" }
if (-not (Test-Path (Join-Path $aj "ArduinoJson.h"))) {
  throw "ArduinoJson headers not found at $aj — set `$env:ARDUINOJSON."
}

$out = Join-Path $here "build"
New-Item -ItemType Directory -Force $out | Out-Null
$exe = Join-Path $out "host_tests.exe"

$sources = @(
  (Join-Path $here "test_host.cpp"),
  (Join-Path $here "shim\shim.cpp"),
  (Join-Path $fw "sensors.cpp"),
  (Join-Path $fw "actuators.cpp"),
  (Join-Path $fw "net.cpp")
)

$isZig = (Split-Path $cxx -Leaf) -like "zig*"
$cmd = if ($isZig) { @($cxx, "c++") } else { @($cxx) }
$args_ = @("-std=c++17", "-O1", "-w",
  "-DARDUINOJSON_ENABLE_STD_STREAM=1",
  "-I", (Join-Path $here "shim"),
  "-I", $fw,
  "-I", $aj) + $sources + @("-o", $exe)

Write-Host "compiler: $cxx"
& $cmd[0] @($cmd[1..($cmd.Count-1)]) @args_
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $exe
exit $LASTEXITCODE
