#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch both backend (FastAPI) and frontend (Vite) dev servers
    concurrently in the foreground with a single command.
.DESCRIPTION
    Starts the FastAPI backend (port 8000) and Vite frontend (port 5173)
    in the same terminal. Press Ctrl-C to stop both gracefully.
.NOTES
    Run from the project root:  .\start.ps1
#>

Write-Host "Starting ResumePipeline dev servers..." -ForegroundColor Green
Write-Host ""

# Resolve the project root (directory where this script lives)
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- Start backend process ---
Write-Host "[INFO] Starting backend (FastAPI) on http://localhost:8000 ..." -ForegroundColor Green
$backend = Start-Process -FilePath "uv" `
    -ArgumentList "run uvicorn app.main:app --port 8000 --reload" `
    -WorkingDirectory "$ProjectRoot\backend" `
    -PassThru -NoNewWindow

Start-Sleep -Seconds 2

# --- Start frontend process ---
Write-Host "[INFO] Starting frontend (Vite) on http://localhost:5173 ..." -ForegroundColor Green
$frontend = Start-Process -FilePath "npm" `
    -ArgumentList "run dev" `
    -WorkingDirectory "$ProjectRoot\frontend" `
    -PassThru -NoNewWindow

# --- Status banner ---
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Press Ctrl-C to stop both servers" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

# --- Wait for either process to exit (Ctrl-C triggers termination) ---
try {
    $backend.WaitForExit()
}
finally {
    # Ensure both processes are killed on Ctrl-C / shutdown
    if (-not $backend.HasExited) { $backend.Kill() }
    if (-not $frontend.HasExited) { $frontend.Kill() }
    Write-Host "[INFO] Shutting down..." -ForegroundColor Green
}
