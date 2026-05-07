param(
    [string]$SessionDir = ".",

    [int]$Fps = 0,

    [ValidateSet("", "jpg", "png")]
    [string]$Format = "",

    [string]$Output = "",

    [string]$FfmpegPath = "ffmpeg",

    [switch]$NoOverwrite
)

$ErrorActionPreference = "Stop"

$resolvedSession = Resolve-Path -LiteralPath $SessionDir
$sessionPath = $resolvedSession.Path
$metadataPath = Join-Path $sessionPath "session.json"
$metadata = $null

if (Test-Path -LiteralPath $metadataPath) {
    $metadata = Get-Content -Raw -LiteralPath $metadataPath | ConvertFrom-Json
}

if (-not $Format) {
    if ($metadata -and $metadata.file_extension) {
        $Format = [string]$metadata.file_extension
    } else {
        $jpgFirstFrame = Join-Path $sessionPath "frame_000001.jpg"
        $pngFirstFrame = Join-Path $sessionPath "frame_000001.png"
        if (Test-Path -LiteralPath $jpgFirstFrame) {
            $Format = "jpg"
        } elseif (Test-Path -LiteralPath $pngFirstFrame) {
            $Format = "png"
        } else {
            throw "Could not detect frame format in $sessionPath"
        }
    }
}

if ($Fps -le 0) {
    if ($metadata -and $metadata.recommended_fps) {
        $Fps = [int]$metadata.recommended_fps
    } else {
        $Fps = 30
    }
}

if (-not $Output) {
    $Output = Join-Path $sessionPath "timelapse.mp4"
}

$firstFrame = Join-Path $sessionPath ("frame_000001." + $Format)
if (-not (Test-Path -LiteralPath $firstFrame)) {
    throw "Could not find first frame: $firstFrame"
}

$inputPattern = Join-Path $sessionPath ("frame_%06d." + $Format)
$overwriteFlag = if ($NoOverwrite) { "-n" } else { "-y" }

Write-Host "Session: $sessionPath"
Write-Host "Frames:  $inputPattern"
Write-Host "FPS:     $Fps"
Write-Host "Output:  $Output"

& $FfmpegPath `
    $overwriteFlag `
    -framerate $Fps `
    -i $inputPattern `
    -c:v libx264 `
    -pix_fmt yuv420p `
    $Output

if ($LASTEXITCODE -ne 0) {
    throw "FFmpeg failed with exit code $LASTEXITCODE"
}

Write-Host "Saved video: $Output"
