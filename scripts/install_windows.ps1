param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found at '$PythonExe'. Create and activate a virtual environment first, or pass -PythonExe with the correct path."
}

$llamaWheelArgs = @(
    "-m", "pip", "install",
    "llama-cpp-python==0.3.2",
    "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cpu",
    "--only-binary=:all:"
)

Write-Host "Using Python: $PythonExe"
Write-Host "Upgrading pip..."
& $PythonExe -m pip install --upgrade pip

Write-Host "Installing verified llama-cpp-python CPU wheel..."
& $PythonExe @llamaWheelArgs

Write-Host "Installing project requirements..."
& $PythonExe -m pip install -r requirements.txt

Write-Host "Installing project in editable mode..."
& $PythonExe -m pip install -e .

Write-Host "Verifying llama-cpp-python import..."
& $PythonExe -c "from llama_cpp import Llama; print('Success: llama-cpp-python is working!')"
