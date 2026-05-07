param(
    [string]$BlenderExe = "blender"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")

Push-Location $root
try {
    python scripts\validate_package.py
    & $BlenderExe --command extension validate
    & $BlenderExe --command extension build
} finally {
    Pop-Location
}
