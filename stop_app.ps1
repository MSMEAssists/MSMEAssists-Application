# MSMEAssist - Stop Script (PowerShell)
# Gracefully stops processes running on port 8000 (Backend) and port 5173 (Frontend)

Write-Host "Stopping MSMEAssist processes..." -ForegroundColor Yellow

# Ports to free
$ports = @(8000, 5173)

foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $pids) {
            try {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped process $procId on port $port" -ForegroundColor Green
            } catch {
                Write-Host "Could not stop process $procId" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "Port $port is already clear." -ForegroundColor Gray
    }
}

Write-Host "All MSMEAssist services stopped." -ForegroundColor Green
