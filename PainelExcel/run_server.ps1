$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

Write-Output "Starting Flask app in $scriptDir"
Start-Process -FilePath "python" -ArgumentList "app.py" -WorkingDirectory $scriptDir
Start-Sleep -Seconds 1

$urls = 'http://127.0.0.1:5000'
$chromePaths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($chrome) {
    Start-Process -FilePath $chrome -ArgumentList "--new-window", $urls
} else {
    try {
        Start-Process -FilePath "chrome" -ArgumentList "--new-window", $urls -ErrorAction Stop
    } catch {
        # fallback to default browser
        Start-Process $urls
    }
}
