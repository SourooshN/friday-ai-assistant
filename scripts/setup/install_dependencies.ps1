# Friday AI Assistant - Dependency Installation Script
# Run with: .\scripts\setup\install_dependencies.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Friday AI Assistant - Setup Wizard" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "⚠️  WARNING: Not running as Administrator. Some features may not install correctly." -ForegroundColor Yellow
    Write-Host "   Recommendation: Run PowerShell as Administrator" -ForegroundColor Yellow
    Write-Host ""
}

# Check Python version
Write-Host "🔍 Checking Python installation..." -ForegroundColor Green
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
    $majorVersion = [int]$matches[1]
    $minorVersion = [int]$matches[2]
    $patchVersion = [int]$matches[3]
    
    Write-Host "✅ Python $majorVersion.$minorVersion.$patchVersion detected" -ForegroundColor Green
    
    if ($majorVersion -eq 3 -and $minorVersion -ge 11) {
        if ($minorVersion -ge 12) {
            Write-Host "⚠️  Note: Python 3.12+ detected. Some packages may have compatibility issues." -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Python 3.11+ required. Found: $pythonVersion" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check Ollama
Write-Host "`n🔍 Checking Ollama installation..." -ForegroundColor Green
try {
    $ollamaVersion = ollama --version 2>&1
    Write-Host "✅ Ollama detected: $ollamaVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama not found. Please install from https://ollama.ai" -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "`n📦 Creating virtual environment..." -ForegroundColor Green
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "`n✅ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`n🔄 Activating virtual environment..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip, setuptools, and wheel
Write-Host "`n📦 Upgrading pip, setuptools, and wheel..." -ForegroundColor Green
python -m pip install --upgrade pip setuptools wheel

# Install core dependencies in stages to handle conflicts better
Write-Host "`n📦 Installing core dependencies (Stage 1: Essential packages)..." -ForegroundColor Green
pip install ollama pyyaml click loguru python-dotenv

Write-Host "`n📦 Installing core dependencies (Stage 2: LangChain and AI packages)..." -ForegroundColor Green
# Install numpy first with the compatible version
pip install "numpy==1.26.4"
# Then install langchain
pip install "langchain==0.3.7" "langchain-community==0.3.5" "openai==1.56.2"

Write-Host "`n📦 Installing core dependencies (Stage 3: Vector stores and memory)..." -ForegroundColor Green
pip install chromadb faiss-cpu redis

Write-Host "`n📦 Installing remaining dependencies..." -ForegroundColor Green
# Install the rest of the requirements
pip install -r requirements.txt --no-deps 2>$null
pip install -r requirements.txt

# Install additional Windows-specific dependencies
Write-Host "`n📦 Installing Windows-specific packages..." -ForegroundColor Green
pip install pywin32 windows-curses

# Create necessary directories
Write-Host "`n📁 Creating data directories..." -ForegroundColor Green
$dataDirs = @(
    "data/logs",
    "data/memory",
    "data/exports",
    "data/temp",
    "models/vosk",
    "drivers"
)

foreach ($dir in $dataDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "✅ Created: $dir" -ForegroundColor Green
    }
}

# Download Vosk model with better error handling
$downloadVosk = Read-Host "`n🎤 Download Vosk speech recognition model? (y/n)"
if ($downloadVosk -eq 'y') {
    Write-Host "📥 Downloading Vosk model..." -ForegroundColor Green
    Write-Host "   Note: This is a large file (1.8GB) and may take some time" -ForegroundColor Yellow
    
    $voskUrl = "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
    $voskZip = "models/vosk/vosk-model.zip"
    
    try {
        # Try with progress bar
        $ProgressPreference = 'Continue'
        Invoke-WebRequest -Uri $voskUrl -OutFile $voskZip -UseBasicParsing
        
        Write-Host "📦 Extracting Vosk model..." -ForegroundColor Green
        Expand-Archive -Path $voskZip -DestinationPath "models/vosk" -Force
        Remove-Item $voskZip
        Write-Host "✅ Vosk model downloaded and extracted" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Failed to download Vosk model automatically" -ForegroundColor Yellow
        Write-Host "   You can manually download it from:" -ForegroundColor Yellow
        Write-Host "   $voskUrl" -ForegroundColor Cyan
        Write-Host "   Extract to: models/vosk/" -ForegroundColor Cyan
        
        # Offer alternative smaller model
        $downloadSmaller = Read-Host "`n   Try smaller model (40MB) instead? (y/n)"
        if ($downloadSmaller -eq 'y') {
            $smallVoskUrl = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
            try {
                Invoke-WebRequest -Uri $smallVoskUrl -OutFile $voskZip -UseBasicParsing
                Expand-Archive -Path $voskZip -DestinationPath "models/vosk" -Force
                Remove-Item $voskZip
                Write-Host "✅ Small Vosk model downloaded" -ForegroundColor Green
            } catch {
                Write-Host "❌ Download failed. Please download manually." -ForegroundColor Red
            }
        }
    }
}

# Install browser drivers with error handling
$installDrivers = Read-Host "`n🌐 Install browser drivers for web automation? (y/n)"
if ($installDrivers -eq 'y') {
    Write-Host "📥 Installing browser driver manager..." -ForegroundColor Green
    pip install webdriver-manager
    
    Write-Host "✅ Browser driver manager installed" -ForegroundColor Green
    Write-Host "   Drivers will be downloaded automatically when needed" -ForegroundColor Yellow
}

# Create .env file from template
if (-not (Test-Path ".env")) {
    Write-Host "`n📝 Creating .env file from template..." -ForegroundColor Green
    Copy-Item ".env.example" ".env"
    Write-Host "✅ .env file created - please edit with your settings" -ForegroundColor Green
} else {
    Write-Host "`n✅ .env file already exists" -ForegroundColor Green
}

# Install pre-commit hooks (optional)
$installPreCommit = Read-Host "`n🔧 Install pre-commit hooks for code quality? (y/n)"
if ($installPreCommit -eq 'y') {
    pip install pre-commit
    pre-commit install
    Write-Host "✅ Pre-commit hooks installed" -ForegroundColor Green
}

# Test imports
Write-Host "`n🧪 Testing key imports..." -ForegroundColor Green
$testScript = @"
import sys
failed_imports = []

packages = [
    'ollama',
    'langchain',
    'chromadb',
    'speech_recognition',
    'pyautogui',
    'selenium',
    'docker',
    'git'
]

for package in packages:
    try:
        __import__(package)
        print(f'✅ {package}')
    except ImportError as e:
        print(f'❌ {package}: {str(e)}')
        failed_imports.append(package)

if failed_imports:
    print(f'\n⚠️  Some packages failed to import: {", ".join(failed_imports)}')
    print('   These may require additional system dependencies')
"@

python -c $testScript

# Summary
Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "✅ Installation Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env file with your configuration" -ForegroundColor White
Write-Host "2. Run: .\scripts\setup\install_models.ps1" -ForegroundColor White
Write-Host "3. Start Friday: python main.py" -ForegroundColor White
Write-Host ""
Write-Host "If you encountered any errors:" -ForegroundColor Yellow
Write-Host "- Check the Python version compatibility" -ForegroundColor White
Write-Host "- Try installing packages individually" -ForegroundColor White
Write-Host "- For voice features, ensure pyaudio dependencies are met" -ForegroundColor White
Write-Host ""
Write-Host "Happy coding with Friday! 🚀" -ForegroundColor Cyan