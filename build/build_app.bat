@echo off
setlocal enabledelayedexpansion

:: §11 — Read all metadata from the single source of truth: build/project.json
set "PROJECT_JSON=%~dp0project.json"

set "TEMP_META=%TEMP%\inputbar_build_meta.txt"
powershell -NoProfile -Command "$j = Get-Content '%PROJECT_JSON%' -Raw | ConvertFrom-Json; Write-Output $j.name; Write-Output $j.version; Write-Output $j.guid" > "%TEMP_META%"

set "_count=0"
for /f "usebackq tokens=*" %%A in ("%TEMP_META%") do (
    set /a "_count+=1"
    if "!_count!"=="1" set "APP_NAME=%%A"
    if "!_count!"=="2" set "APP_VERSION=%%A"
    if "!_count!"=="3" set "APP_GUID=%%A"
)
del "%TEMP_META%" 2>nul

set "BUILD_DIR=build_cmake"
set "RELEASES_DIR=releases"
set "UTILS_DIR=%~dp0..\src\Utils"

title Build %APP_NAME% v%APP_VERSION%

echo ======================================================
echo    BUILD SYSTEM - %APP_NAME% v%APP_VERSION%
echo ======================================================
echo.

:: ── [1/4] Suite de tests ──────────────────────────────────────────────────────
echo [1/4] Suite de tests...
set "_test_total=0"
set "_test_failed=0"
set "_test_failed_names="

for %%F in ("%UTILS_DIR%\test_*.py") do (
    set /a "_test_total+=1"
    echo   ^> %%~nxF
    python "%%F"
    if errorlevel 1 (
        set /a "_test_failed+=1"
        set "_test_failed_names=!_test_failed_names! %%~nxF"
    )
)

if !_test_total! equ 0 (
    echo   Aucun script de test trouve dans src\Utils\
)

if !_test_failed! gtr 0 (
    echo.
    echo ======================================================
    echo    ECHEC DES TESTS -- BUILD BLOQUE
    echo ======================================================
    echo.
    echo !_test_failed! script^(s^) en erreur :
    for %%N in (!_test_failed_names!) do echo   - %%N
    echo.
    echo Corrigez les scripts indiques ci-dessus, puis relancez le build.
    echo.
    pause
    exit /b 1
)

echo   Tous les tests passes (!_test_total!/!_test_total!).
echo.

:: Demander pour l'installateur
set /p GENERATE_SETUP="Voulez-vous generer l'installateur Setup.exe ? (O/N) : "
if /i "%GENERATE_SETUP%"=="O" (
    set "SETUP_OPTION=-DGENERATE_SETUP=ON"
    set "TARGET=generate_setup"
) else (
    set "SETUP_OPTION=-DGENERATE_SETUP=OFF"
    set "TARGET=build_app"
)

:: Nettoyage
if exist "%BUILD_DIR%"          rd /s /q "%BUILD_DIR%"
if exist "..\build_dist"        rd /s /q "..\build_dist"
if exist "..\build_pyinstaller" rd /s /q "..\build_pyinstaller"
mkdir "%BUILD_DIR%"

echo.
echo [2/4] Configuration CMake...
cmake -S configuration -B "%BUILD_DIR%" %SETUP_OPTION% ^
    -DAPP_NAME="%APP_NAME%" ^
    -DPROJECT_VERSION=%APP_VERSION% ^
    -DAPP_GUID=%APP_GUID% ^
    -DRELEASES_DIR=%RELEASES_DIR%

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERREUR] La configuration CMake a echoue. [etape 2/4]
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/4] Compilation / Execution du Build (Cible : %TARGET%)...
cmake --build "%BUILD_DIR%" --target %TARGET% --config Release

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERREUR] Le build a echoue. Verifiez les logs ci-dessus. [etape 3/4]
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [4/4] Nettoyage final...
if exist "%BUILD_DIR%"          rd /s /q "%BUILD_DIR%"
if exist "..\build_dist"        rd /s /q "..\build_dist"
if exist "..\build_pyinstaller" rd /s /q "..\build_pyinstaller"

echo.
echo ======================================================
echo    BUILD TERMINE AVEC SUCCES !
echo ======================================================
echo.
echo Retrouvez vos fichiers dans le dossier : ..\%RELEASES_DIR%
echo - Archive ZIP Portable (%APP_NAME%_v%APP_VERSION%_Portable.zip)
if /i "%GENERATE_SETUP%"=="O" echo - Setup.exe (InputBar_v%APP_VERSION%_Setup.exe)
echo.
pause
