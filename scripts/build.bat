@echo off
setlocal enabledelayedexpansion

REM Exit on error
if not defined ERRORLEVEL set ERRORLEVEL=0

REM Colors for output (using Windows color codes)
set "RED=[91m"
set "GREEN=[92m"
set "BLUE=[94m"
set "NC=[0m"

REM Function to print step information
:print_step
echo %BLUE%==^> %~1%NC%
goto :eof

REM Function to print success message
:print_success
echo %GREEN%==^> Success: %~1%NC%
goto :eof

REM Function to print error message
:print_error
echo %RED%==^> Error: %~1%NC% >&2
goto :eof

REM Get the script's directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Load environment variables from .env.local
if exist .env.local (
    call :print_step "Loading environment variables from .env.local..."
    for /f "usebackq tokens=1,2 delims==" %%a in (".env.local") do (
        if not "%%a"=="" if not "%%b"=="" (
            set "%%a=%%b"
        )
    )
    call :print_success "Environment variables loaded"
) else (
    call :print_error ".env.local file not found"
    exit /b 1
)

REM Clean up existing environments and cache
call :print_step "Cleaning up existing environments..."
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
for /d /r . %%d in (.pytest_cache) do @if exist "%%d" rd /s /q "%%d" 2>nul
for /d /r . %%d in (dist) do @if exist "%%d" rd /s /q "%%d" 2>nul
for /d /r . %%d in (.venv) do @if exist "%%d" rd /s /q "%%d" 2>nul
for /d /r . %%d in (*.egg-info) do @if exist "%%d" rd /s /q "%%d" 2>nul
call :print_success "Environment cleanup complete"

REM Create and activate virtual environment
call :print_step "Creating virtual environment..."
python -m venv .venv
if %ERRORLEVEL% neq 0 (
    call :print_error "Failed to create virtual environment"
    exit /b 1
)
call .venv\Scripts\activate.bat

REM Upgrade pip and install build tools
call :print_step "Upgrading pip and installing build tools..."
python -m pip install --upgrade pip setuptools wheel
if %ERRORLEVEL% neq 0 (
    call :print_error "Failed to upgrade pip and install build tools"
    exit /b 1
)

REM Function to install a package and its dependencies
:install_package
set "package_dir=%~1"
set "package_name=%~2"
set "extras=%~3"
call :print_step "Installing %package_name%..."
cd /d "%package_dir%"

if exist "pyproject.toml" (
    if not "%extras%"=="" (
        pip install -e ".[%extras%]"
    ) else (
        pip install -e .
    )
    if !ERRORLEVEL! neq 0 (
        call :print_error "Failed to install %package_name%"
        cd /d "%PROJECT_ROOT%"
        exit /b 1
    )
) else (
    call :print_error "No pyproject.toml found in %package_dir%"
    cd /d "%PROJECT_ROOT%"
    exit /b 1
)

cd /d "%PROJECT_ROOT%"
goto :eof

REM Install packages in order of dependency
call :print_step "Installing packages in development mode..."

REM Install core first (base package with telemetry support)
call :install_package "libs\core" "core" ""

REM Install pylume (base dependency)
call :install_package "libs\pylume" "pylume" ""

REM Install computer (depends on pylume)
call :install_package "libs\computer" "computer" ""

REM Install omniparser
call :install_package "libs\som" "som" ""

REM Install agent with all its dependencies and extras
call :install_package "libs\agent" "agent" "all"

REM Install computer-server
call :install_package "libs\computer-server" "computer-server" ""

REM Install mcp-server
call :install_package "libs\mcp-server" "mcp-server" ""

REM Install development tools from root project
call :print_step "Installing development dependencies..."
pip install -e ".[dev,test,docs]"
if %ERRORLEVEL% neq 0 (
    call :print_error "Failed to install development dependencies"
    exit /b 1
)

REM Create a .env file for VS Code to use the virtual environment
call :print_step "Creating .env file for VS Code..."
echo PYTHONPATH=%PROJECT_ROOT%\libs\core;%PROJECT_ROOT%\libs\computer;%PROJECT_ROOT%\libs\agent;%PROJECT_ROOT%\libs\som;%PROJECT_ROOT%\libs\pylume;%PROJECT_ROOT%\libs\computer-server;%PROJECT_ROOT%\libs\mcp-server > .env

call :print_success "All packages installed successfully!"
call :print_step "Your virtual environment is ready. To activate it:"
echo   .venv\Scripts\activate.bat

endlocal
