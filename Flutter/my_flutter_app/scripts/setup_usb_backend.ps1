# EmergencyIQ: connect physical Android phone to local backend
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

Write-Host "=== EmergencyIQ USB backend setup ==="

# 1. Firewall rule (Wi-Fi fallback)
$ruleName = "EmergencyIQ Backend TCP 8000"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "Adding Windows Firewall inbound rule for port 8000..."
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 `
        -Profile Private, Domain | Out-Null
} else {
    Write-Host "Firewall rule already exists."
}

# 2. USB port reverse (primary method for cable-connected phone)
if (-not (Test-Path $adb)) {
    Write-Error "adb not found at $adb"
    exit 1
}

Write-Host "Connected devices:"
& $adb devices

& $adb reverse --remove-all 2>$null
& $adb reverse tcp:8000 tcp:8000
Write-Host "Port reverse:"
& $adb reverse --list

$wifiIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.InterfaceAlias -match 'Wi-Fi' } |
    Select-Object -First 1 -ExpandProperty IPAddress)

Write-Host ""
Write-Host "Backend should be running: python backend/main.py"
Write-Host "Phone app uses: http://127.0.0.1:8000  (via USB adb reverse)"
if ($wifiIp) {
    Write-Host "Wi-Fi fallback IP: http://${wifiIp}:8000"
}
Write-Host "Done."
