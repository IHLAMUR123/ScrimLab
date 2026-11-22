# Consistent SQLite backup for ScrimLab (Windows).
#
#   .\backup.ps1
#   .\backup.ps1 -KeepDays 30
#
# Output: backups\main-YYYYmmdd-HHMMSS.sqlite.gz
param(
    [string]$DbPath = "db/main.sqlite",
    [string]$BackupDir = "backups",
    [int]$KeepDays = 14
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path -LiteralPath $DbPath)) {
    throw "Veritabani bulunamadi: $DbPath"
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tmp = Join-Path $BackupDir "main-$stamp.sqlite"
$gz = "$tmp.gz"

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) { $py = "python" }

# SQLite online backup API: consistent snapshot while the bot is running.
& $py -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" $DbPath $tmp
if ($LASTEXITCODE -ne 0) { throw "SQLite yedegi alinamadi." }

$in = [IO.File]::OpenRead($tmp)
try {
    $out = [IO.File]::Create($gz)
    try {
        $stream = New-Object IO.Compression.GZipStream($out, [IO.Compression.CompressionLevel]::Optimal)
        try {
            $in.CopyTo($stream)
        } finally {
            $stream.Dispose()
        }
    } finally {
        $out.Dispose()
    }
} finally {
    $in.Dispose()
}
Remove-Item -LiteralPath $tmp -Force

if ($KeepDays -gt 0) {
    Get-ChildItem -LiteralPath $BackupDir -Filter "main-*.sqlite.gz" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
        Remove-Item -Force
}

$size = [math]::Round((Get-Item -LiteralPath $gz).Length / 1KB, 1)
Write-Host "Backup: $gz ($size KB)"
