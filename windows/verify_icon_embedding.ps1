Add-Type -AssemblyName System.Drawing

function Extract-Icon($exePath, $outPngPath) {
    if (-not (Test-Path $exePath)) {
        Write-Host "FEHLT: $exePath"
        return $false
    }
    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($exePath)
    $bmp = $icon.ToBitmap()
    $bmp.Save($outPngPath, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Host "Icon aus $exePath extrahiert -> $outPngPath ($($bmp.Width)x$($bmp.Height))"
    $bmp.Dispose()
    $icon.Dispose()
    return $true
}

$root = Split-Path -Parent $PSScriptRoot
Extract-Icon "$root\dist\kanzlei_ai\kanzlei_ai.exe" "$root\windows\_verify_exe_icon.png"
Extract-Icon "$root\dist\installer\KanzleiAI_Setup.exe" "$root\windows\_verify_installer_icon.png"
