# PowerShell script for TypeToneSense deployment

param(
    [string]$Environment = "development",
    [switch]$Update,
    [switch]$Clean
)

# Configuration
$VenvPath = ".venv"
$RequirementsFile = "requirements.txt"
$PythonCmd = "python"
$AppFile = "app.py"

# Colors for output
$Colors = @{
    Success = "Green"
    Error = "Red"
    Info = "Cyan"
    Warning = "Yellow"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-Command {
    param(
        [string]$Command
    )
    try {
        if (Get-Command $Command -ErrorAction Stop) {
            return $true
        }
    }
    catch {
        return $false
    }
}

# Check Python installation
if (-not (Test-Command $PythonCmd)) {
    Write-ColorOutput "Error: Python not found. Please install Python 3.11 or later." $Colors.Error
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path $VenvPath)) {
    Write-ColorOutput "Creating virtual environment..." $Colors.Info
    & $PythonCmd -m venv $VenvPath
    if (-not $?) {
        Write-ColorOutput "Error creating virtual environment" $Colors.Error
        exit 1
    }
}

# Activate virtual environment
Write-ColorOutput "Activating virtual environment..." $Colors.Info
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    . $ActivateScript
}
else {
    Write-ColorOutput "Error: Virtual environment activation script not found" $Colors.Error
    exit 1
}

# Update dependencies if requested
if ($Update) {
    Write-ColorOutput "Updating dependencies..." $Colors.Info
    & pip install --upgrade pip
    & pip install -r $RequirementsFile --upgrade
    if (-not $?) {
        Write-ColorOutput "Error updating dependencies" $Colors.Error
        exit 1
    }
}
else {
    Write-ColorOutput "Installing dependencies..." $Colors.Info
    & pip install -r $RequirementsFile
    if (-not $?) {
        Write-ColorOutput "Error installing dependencies" $Colors.Error
        exit 1
    }
}

# Run tests
Write-ColorOutput "Running tests..." $Colors.Info
& pytest
if (-not $?) {
    Write-ColorOutput "Warning: Tests failed" $Colors.Warning
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Clean build files if requested
if ($Clean) {
    Write-ColorOutput "Cleaning build files..." $Colors.Info
    Get-ChildItem -Path . -Include *.pyc,*.pyo,*.pyd,*.so -Recurse | Remove-Item
    if (Test-Path "__pycache__") {
        Remove-Item -Recurse -Force "__pycache__"
    }
    if (Test-Path ".pytest_cache") {
        Remove-Item -Recurse -Force ".pytest_cache"
    }
}

# Set environment variables
$env:FLASK_APP = $AppFile
$env:FLASK_ENV = $Environment

# Start application
if ($Environment -eq "development") {
    Write-ColorOutput "Starting development server..." $Colors.Info
    & flask run --debug
}
else {
    Write-ColorOutput "Starting production server..." $Colors.Info
    & waitress-serve --port=8000 "app:app"
}