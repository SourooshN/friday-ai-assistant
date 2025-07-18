# Friday AI Assistant Launcher

Write-Host "Starting Friday AI Assistant..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

# Check if Ollama is running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -ErrorAction Stop
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚠ Warning: Ollama doesn't seem to be running!" -ForegroundColor Yellow
    Write-Host "Please start Ollama in another terminal: ollama serve" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit 0
    }
}

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "⚠ Warning: .env file not found!" -ForegroundColor Yellow
    Write-Host "Creating from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

Write-Host ""
Write-Host "Launching Friday..." -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Blue

# Start Friday
python main.py

# Keep window open on exit
Write-Host ""
Write-Host "Friday has stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"