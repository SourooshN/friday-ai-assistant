# Friday AI Assistant - Ollama Model Installation Script
# Run with: .\scripts\setup\install_models.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Friday AI - Ollama Model Installer" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is running
Write-Host "🔍 Checking Ollama service..." -ForegroundColor Green
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -ErrorAction Stop
    Write-Host "✅ Ollama service is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama service is not running!" -ForegroundColor Red
    Write-Host "   Please start Ollama first: ollama serve" -ForegroundColor Yellow
    exit 1
}

# Define models to install
$models = @(
    @{
        Name = "openhermes:latest"
        Description = "General purpose, conversational AI"
        Size = "7B"
        Required = $true
    },
    @{
        Name = "mistral:latest"
        Description = "Planning and orchestration tasks"
        Size = "7B"
        Required = $true
    },
    @{
        Name = "codellama:13b"
        Description = "Code generation and analysis"
        Size = "13B"
        Required = $true
    },
    @{
        Name = "nous-hermes:13b"
        Description = "Instruction following and structured tasks"
        Size = "13B"
        Required = $true
    },
    @{
        Name = "deepseek-coder:6.7b"
        Description = "Alternative coding model (recommended)"
        Size = "6.7B"
        Required = $false
    },
    @{
        Name = "llama3:8b"
        Description = "Latest Llama model for general tasks"
        Size = "8B"
        Required = $false
    }
)

# Check existing models
Write-Host "`n📋 Checking installed models..." -ForegroundColor Green
$installedModels = @()
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get
    $installedModels = $response.models | ForEach-Object { $_.name }
} catch {
    Write-Host "⚠️  Could not retrieve installed models" -ForegroundColor Yellow
}

# Display model status
Write-Host "`n📦 Model Installation Status:" -ForegroundColor Cyan
Write-Host "-----------------------------" -ForegroundColor Cyan
foreach ($model in $models) {
    $status = if ($installedModels -contains $model.Name) { "✅ Installed" } else { "❌ Not Installed" }
    $requiredText = if ($model.Required) { "[REQUIRED]" } else { "[OPTIONAL]" }
    
    Write-Host "$status $($model.Name) - $($model.Description) ($($model.Size)) $requiredText"
}

# Install missing required models
Write-Host "`n🚀 Installing models..." -ForegroundColor Green
foreach ($model in $models) {
    if ($installedModels -contains $model.Name) {
        Write-Host "✅ $($model.Name) already installed" -ForegroundColor Green
        continue
    }
    
    if ($model.Required) {
        Write-Host "`n📥 Installing $($model.Name)..." -ForegroundColor Yellow
        Write-Host "   This may take several minutes depending on your internet speed" -ForegroundColor Gray
        
        $startTime = Get-Date
        & ollama pull $model.Name
        
        $duration = (Get-Date) - $startTime
        Write-Host "✅ $($model.Name) installed in $($duration.TotalMinutes.ToString('F1')) minutes" -ForegroundColor Green
    } else {
        $install = Read-Host "`n📦 Install optional model $($model.Name)? (y/n)"
        if ($install -eq 'y') {
            Write-Host "📥 Installing $($model.Name)..." -ForegroundColor Yellow
            & ollama pull $model.Name
            Write-Host "✅ $($model.Name) installed" -ForegroundColor Green
        }
    }
}

# Special handling for deepseek-tng-r1t2-chimera
Write-Host "`n🔍 Checking for deepseek-tng-r1t2-chimera..." -ForegroundColor Green
Write-Host "⚠️  Note: This model may not be available in Ollama's registry" -ForegroundColor Yellow
Write-Host "   You may need to:" -ForegroundColor Yellow
Write-Host "   1. Find an alternative strategic reasoning model" -ForegroundColor White
Write-Host "   2. Use a custom GGUF file with Ollama" -ForegroundColor White
Write-Host "   3. Configure Friday to use available models" -ForegroundColor White

# Test models
Write-Host "`n🧪 Testing installed models..." -ForegroundColor Green
$testPrompt = "Hello, this is a test. Please respond with 'Model working correctly.'"

foreach ($model in $models) {
    if ($installedModels -contains $model.Name -or $model.Required) {
        Write-Host "`nTesting $($model.Name)..." -ForegroundColor Yellow
        
        try {
            $response = & ollama run $model.Name $testPrompt --verbose 2>&1
            if ($response -match "Model working correctly" -or $response -match "working correctly") {
                Write-Host "✅ $($model.Name) is working correctly" -ForegroundColor Green
            } else {
                Write-Host "⚠️  $($model.Name) responded but may need configuration" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "❌ Error testing $($model.Name)" -ForegroundColor Red
        }
    }
}

# Memory usage warning
Write-Host "`n💾 Memory Usage Information:" -ForegroundColor Cyan
Write-Host "-----------------------------" -ForegroundColor Cyan
Write-Host "Each model requires RAM approximately equal to its parameter size:" -ForegroundColor White
Write-Host "- 7B models: ~7-8 GB RAM" -ForegroundColor Gray
Write-Host "- 13B models: ~13-16 GB RAM" -ForegroundColor Gray
Write-Host ""
Write-Host "Friday will intelligently load/unload models as needed." -ForegroundColor Green
Write-Host "Recommended: 16GB+ RAM for smooth operation" -ForegroundColor Yellow

# Configuration tips
Write-Host "`n⚙️  Configuration Tips:" -ForegroundColor Cyan
Write-Host "-----------------------------" -ForegroundColor Cyan
Write-Host "1. Edit config/model_configs.yaml to set model preferences" -ForegroundColor White
Write-Host "2. Adjust temperature and other parameters for each model" -ForegroundColor White
Write-Host "3. Configure model selection rules for different tasks" -ForegroundColor White
Write-Host "4. Set memory limits in .env file if needed" -ForegroundColor White

# Summary
Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "✅ Model Setup Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Friday is ready to use with local AI models! 🚀" -ForegroundColor Green
Write-Host ""
Write-Host "Start Friday with: python main.py" -ForegroundColor Yellow