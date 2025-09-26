# HH v4 PowerShell Aliases (ASCII-only messages to avoid encoding issues)
# How to load (dot-source) from project root for current session:
#   . .\scripts\hh-aliases.ps1 ; if ($?) { hh-help }
# Chaining rule:
#   cmd1 ; if ($?) { cmd2 }
#[Console] UTF-8 for correct output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
# Example: python module.py ; if ($?) { Start-Sleep -Seconds 2 }

# === DAEMON MANAGEMENT ===
function Start-HHDaemon {
    Write-Host "Starting HH daemon..." -ForegroundColor Green
    # Chg_ALIAS_NO_AUTOSTART_2509: do not auto-start web server here; scheduler_daemon manages it
    python cli_v4.py daemon start --background ; if ($?) { Start-Sleep -Seconds 2 }
}

function Stop-HHDaemon {
    Write-Host "Stopping HH daemon..." -ForegroundColor Yellow  
    python cli_v4.py daemon stop ; if ($?) { Start-Sleep -Seconds 2 }
}

function Get-HHStatus {
    Write-Host "Checking HH system status..." -ForegroundColor Blue
    python cli_v4.py status ; if ($?) { Start-Sleep -Seconds 2 }
}

function Restart-HHDaemon {
    Write-Host "Restarting HH daemon..." -ForegroundColor Cyan
    Stop-HHDaemon
    Start-Sleep -Seconds 3
    Start-HHDaemon
}

# === TESTING ===
function Test-HH {
    param([string]$Type = "consolidated")
    Write-Host "Running $Type tests..." -ForegroundColor Magenta
    python cli_v4.py test $Type -v ; if ($?) { Start-Sleep -Seconds 2 }
}

function Test-HHQuick {
    Write-Host "Running quick load test..." -ForegroundColor Magenta
    python scripts/min_load_test.py ; if ($?) { Start-Sleep -Seconds 2 }
}

function Test-HHVisual {
    Write-Host "Running consolidated visual panel test..." -ForegroundColor Magenta  
    python tests/consolidated_visual_test.py ; if ($?) { Start-Sleep -Seconds 2 }
}

# === LOGS AND DIAGNOSTICS ===
function Get-HHLogs {
    param([int]$Lines = 100)
    Write-Host "Showing last $Lines log lines..." -ForegroundColor White
    Get-Content 'logs/app.log' -Tail $Lines -Encoding utf8
}

function Get-HHSystem {
    Write-Host "System monitoring..." -ForegroundColor Blue
    python cli_v4.py system --detailed ; if ($?) { Start-Sleep -Seconds 2 }
}

# === STATISTICS ===  
function Get-HHStats {
    param([int]$Days = 7)
    Write-Host "Statistics for last $Days days..." -ForegroundColor Green
    python cli_v4.py stats --days $Days ; if ($?) { Start-Sleep -Seconds 2 }
}

# === EXPORT ===
function Export-HHVacancies {
    param(
        [string]$Path = "reports/export_$(Get-Date -Format 'ddMMyyyy').xlsx",
        [int]$Limit = 1000,
        [string]$DateFrom = (Get-Date).AddDays(-30).ToString("yyyy-MM-dd")
    )
    Write-Host "Exporting to $Path..." -ForegroundColor Cyan
    python cli_v4.py export "$Path" --limit $Limit --date-from $DateFrom ; if ($?) { Start-Sleep -Seconds 2 }
}

# === CLEANUP ===
function Start-HHCleanup {
    param([switch]$DryRun)
    if ($DryRun) {
        Write-Host "Dry-run cleanup..." -ForegroundColor Yellow
        python cli_v4.py cleanup --dry-run ; if ($?) { Start-Sleep -Seconds 2 }
    } else {
        Write-Host "Running cleanup..." -ForegroundColor Yellow
        python cli_v4.py cleanup ; if ($?) { Start-Sleep -Seconds 2 }
    }
}

# === USEFUL URLS ===
function Open-HHPanel {
    $config = Get-Content 'config/config_v4.json' -Encoding utf8 | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($config -and $config.web_interface) {
        $url = "http://$($config.web_interface.host):$($config.web_interface.port)"
        Write-Host "Opening panel: $url" -ForegroundColor Green
        
        # Check availability before opening
        try {
            $response = Invoke-WebRequest -Uri "$url/api/version" -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                Start-Process $url
                Write-Host "Panel opened in browser" -ForegroundColor Green
            } else {
                Write-Host "Warning: panel status $($response.StatusCode), opening anyway..." -ForegroundColor Yellow
                Start-Process $url
            }
        } catch {
            Write-Host "Error: panel not responding. Starting web server first..." -ForegroundColor Red
            Start-Process -FilePath "python" -ArgumentList "-m web.server" -WindowStyle Hidden
            Start-Sleep -Seconds 3
            Start-Process $url
            Write-Host "Web server started, panel should be available at: $url" -ForegroundColor Cyan
        }
    } else {
        Write-Host "Default panel: http://localhost:8000" -ForegroundColor Green  
        Start-Process "http://localhost:8000"
    }
}

# === HELP ===
function Get-HHHelp {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Host "HH v4 Command Aliases:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "MANAGEMENT:" -ForegroundColor Yellow
    Write-Host "  hh-start         - Start daemon with web panel"
    Write-Host "  hh-stop          - Stop daemon"  
    Write-Host "  hh-restart       - Restart daemon"
    Write-Host "  hh-status        - System status"
    Write-Host ""
    Write-Host "TESTING:" -ForegroundColor Yellow
    Write-Host "  hh-test          - Full consolidated tests"
    Write-Host "  hh-test-quick    - Quick load test"
    Write-Host "  hh-test-visual   - Visual test with screenshots"
    Write-Host ""
    Write-Host "MONITORING:" -ForegroundColor Yellow  
    Write-Host "  hh-logs [N]      - Last N log lines (default: 100)"
    Write-Host "  hh-system        - Detailed system diagnostics"
    Write-Host "  hh-stats [N]     - Stats for last N days (default: 7)"
    Write-Host ""
    Write-Host "DATA:" -ForegroundColor Yellow
    Write-Host "  hh-export        - Export vacancies (auto-name, 1000 records)"
    Write-Host "  hh-cleanup       - Cleanup temporary files"
    Write-Host ""
    Write-Host "PANEL:" -ForegroundColor Yellow
    Write-Host "  hh-panel         - Open web panel in browser"  
    Write-Host "  hh-help          - Show this help"
    Write-Host ""
    Write-Host "All commands follow rule '; if ($?) { Start-Sleep -Seconds 2 }' for stable chaining" -ForegroundColor Green
    Write-Host "Dot sourcing: . .\scripts\hh-aliases.ps1 (once per session)" -ForegroundColor Green
}

# Creating short aliases
Set-Alias hh-start Start-HHDaemon
Set-Alias hh-stop Stop-HHDaemon
Set-Alias hh-status Get-HHStatus
Set-Alias hh-restart Restart-HHDaemon
Set-Alias hh-test Test-HH
Set-Alias hh-test-quick Test-HHQuick
Set-Alias hh-test-visual Test-HHVisual
Set-Alias hh-logs Get-HHLogs
Set-Alias hh-system Get-HHSystem
Set-Alias hh-stats Get-HHStats
Set-Alias hh-export Export-HHVacancies
Set-Alias hh-cleanup Start-HHCleanup
Set-Alias hh-panel Open-HHPanel
Set-Alias hh-help Get-HHHelp

Write-Host "HH v4 aliases loaded! Type 'hh-help' for commands" -ForegroundColor Green
