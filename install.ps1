# IRUMI Windows Installer
$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $HOME ".irumi\bin"
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$PyUrl = "https://raw.githubusercontent.com/IRUMI163/homebrew-irumi/main/irumi.py"
$TargetPy = Join-Path $InstallDir "irumi.py"
$TargetCmd = Join-Path $InstallDir "irumi.cmd"

Write-Host "IRUMI をダウンロードしています..."
Invoke-WebRequest -Uri $PyUrl -OutFile $TargetPy

$CmdContent = "@echo off`r`npython `"%~dp0irumi.py`" %*"
Set-Content -Path $TargetCmd -Value $CmdContent -Encoding ASCII

# ユーザー環境変数 Path に追加
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$InstallDir*") {
    $NewPath = if ($UserPath.EndsWith(";")) { "$UserPath$InstallDir" } else { "$UserPath;$InstallDir" }
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    $env:Path += ";$InstallDir"
    Write-Host "PATH に $InstallDir を追加しました。"
}

Write-Host "IRUMI のインストールが完了しました！"
Write-Host "ターミナルを再起動するか新しいターミナルを開いて、'irumi -v' を実行してください。"
