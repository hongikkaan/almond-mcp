@echo off
rem FOR /F starts CMD: do not re-enter the AutoRun hook in that child.
if defined __AUTO_VENV_RESOLVING exit /b 0
if defined VIRTUAL_ENV if /i not "%VIRTUAL_ENV%"=="%AUTO_VENV_ACTIVE%" exit /b 0
set "__AUTO_VENV_FOUND="
set "__AUTO_VENV_ROOT="
set "__AUTO_VENV_WORKTREE="
set "__AUTO_VENV_GIT="
if defined AUTO_VENV_DISABLE goto apply
for %%G in (git.exe) do set "__AUTO_VENV_GIT=%%~$PATH:G"
if not defined __AUTO_VENV_GIT if exist "%ProgramFiles%\Git\cmd\git.exe" set "__AUTO_VENV_GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined __AUTO_VENV_GIT goto apply
call :repository
if not defined __AUTO_VENV_ROOT goto apply
for %%V in (".venv" "venv" "data\development\.venv" "src\engine\.venv") do if not defined __AUTO_VENV_FOUND if exist "%__AUTO_VENV_ROOT%\%%~V\pyvenv.cfg" if exist "%__AUTO_VENV_ROOT%\%%~V\Scripts\python.exe" for %%D in ("%__AUTO_VENV_ROOT%\%%~V") do set "__AUTO_VENV_FOUND=%%~fD"

:apply
set "AUTO_VENV_WORKTREE_ROOT=%__AUTO_VENV_WORKTREE%"
set "AUTO_VENV_REPO_ROOT=%__AUTO_VENV_ROOT%"
set "AUTO_VENV_PYTHON="
if defined __AUTO_VENV_FOUND set "AUTO_VENV_PYTHON=%__AUTO_VENV_FOUND%\Scripts\python.exe"
if /i "%AUTO_VENV_ACTIVE%"=="%__AUTO_VENV_FOUND%" goto done
if not defined AUTO_VENV_ACTIVE goto activate
set "PATH=%AUTO_VENV_BASE_PATH%"
set "PYTHONHOME=%AUTO_VENV_OLD_PYTHONHOME%"
set "VIRTUAL_ENV="
set "AUTO_VENV_ACTIVE="
set "AUTO_VENV_BASE_PATH="
set "AUTO_VENV_OLD_PYTHONHOME="
:activate
if not defined __AUTO_VENV_FOUND goto done
set "AUTO_VENV_BASE_PATH=%PATH%"
set "AUTO_VENV_OLD_PYTHONHOME=%PYTHONHOME%"
set "AUTO_VENV_ACTIVE=%__AUTO_VENV_FOUND%"
set "VIRTUAL_ENV=%__AUTO_VENV_FOUND%"
set "PYTHONHOME="
set "PATH=%__AUTO_VENV_FOUND%\Scripts;%PATH%"
:done
set "__AUTO_VENV_FOUND="
set "__AUTO_VENV_ROOT="
set "__AUTO_VENV_WORKTREE="
set "__AUTO_VENV_GIT="
exit /b 0

:repository
set "__AUTO_VENV_RESOLVING=1"
set "__AUTO_VENV_CODEPAGE="
set "__AUTO_VENV_COMMON="
set "__AUTO_VENV_VERIFY_ROOT="
set "__AUTO_VENV_VERIFY_COMMON="
rem Git prints UTF-8 paths. Restore the caller's code page before returning.
for /f "tokens=2 delims=:" %%C in ('"%SystemRoot%\System32\chcp.com"') do for /f "tokens=*" %%P in ("%%C") do set "__AUTO_VENV_CODEPAGE=%%P"
if not defined __AUTO_VENV_CODEPAGE goto repository_failed
"%SystemRoot%\System32\chcp.com" 65001 >nul
for /f "delims=" %%R in ('"%__AUTO_VENV_GIT%" rev-parse --show-toplevel 2^>nul') do for %%D in ("%%R") do set "__AUTO_VENV_WORKTREE=%%~fD"
if not defined __AUTO_VENV_WORKTREE goto repository_failed
for /f "delims=" %%R in ('"%__AUTO_VENV_GIT%" rev-parse --path-format^=absolute --git-common-dir 2^>nul') do for %%D in ("%%R") do set "__AUTO_VENV_COMMON=%%~fD"
if not defined __AUTO_VENV_COMMON goto repository_failed
rem Read the main checkout's config, including its config.worktree.
pushd "%__AUTO_VENV_COMMON%" >nul
if errorlevel 1 goto repository_failed
for /f "delims=" %%R in ('"%__AUTO_VENV_GIT%" --git-dir^=. config --path --get core.worktree 2^>nul') do set "__AUTO_VENV_ROOT=%%R"
if defined __AUTO_VENV_ROOT for %%D in ("%__AUTO_VENV_ROOT%") do set "__AUTO_VENV_ROOT=%%~fD"
popd
if not defined __AUTO_VENV_ROOT for %%D in ("%__AUTO_VENV_COMMON%") do if /i "%%~nxD"==".git" for %%P in ("%%~fD\..") do set "__AUTO_VENV_ROOT=%%~fP"
if not defined __AUTO_VENV_ROOT goto repository_failed
if not exist "%__AUTO_VENV_ROOT%\." goto repository_failed
pushd "%__AUTO_VENV_ROOT%" >nul
if errorlevel 1 goto repository_failed
for /f "delims=" %%R in ('"%__AUTO_VENV_GIT%" rev-parse --show-toplevel 2^>nul') do for %%D in ("%%R") do set "__AUTO_VENV_VERIFY_ROOT=%%~fD"
for /f "delims=" %%R in ('"%__AUTO_VENV_GIT%" rev-parse --path-format^=absolute --git-common-dir 2^>nul') do for %%D in ("%%R") do set "__AUTO_VENV_VERIFY_COMMON=%%~fD"
popd
if /i not "%__AUTO_VENV_VERIFY_ROOT%"=="%__AUTO_VENV_ROOT%" goto repository_failed
if /i not "%__AUTO_VENV_VERIFY_COMMON%"=="%__AUTO_VENV_COMMON%" goto repository_failed
goto repository_done
:repository_failed
set "__AUTO_VENV_ROOT="
set "__AUTO_VENV_WORKTREE="
:repository_done
if defined __AUTO_VENV_CODEPAGE "%SystemRoot%\System32\chcp.com" %__AUTO_VENV_CODEPAGE% >nul
set "__AUTO_VENV_CODEPAGE="
set "__AUTO_VENV_COMMON="
set "__AUTO_VENV_VERIFY_ROOT="
set "__AUTO_VENV_VERIFY_COMMON="
set "__AUTO_VENV_RESOLVING="
exit /b 0
