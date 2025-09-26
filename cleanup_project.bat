@echo off
REM // Project cleanup utility for HH-bot v4
REM // Created: 19.09.2025 21:25:00
REM // Usage: cleanup_project.bat [--dry-run] [--force]

:: // Chg_CONSOLE_1909: Настройка русской консоли (UTF-8 -> CP866 -> CP1251)
chcp 65001 >nul 2>&1
if errorlevel 1 (
    chcp 866 >nul 2>&1
    if errorlevel 1 chcp 1251 >nul 2>&1
)

:: // Chg_ENV_1909: Инициализация окружения и переменных
setlocal EnableExtensions EnableDelayedExpansion
set "PROJECT_ROOT=%~dp0"
set "DRY_RUN=false"
set "FORCE=false"
set "TIMESTAMP=%date:~-4,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"

echo ===============================================
:: Обработка параметров командной строки
:parse_args
if "%~1"=="--dry-run" (
    set "DRY_RUN=true"
    shift
    goto parse_args
)
if "%~1"=="--force" (
    set "FORCE=true"
    shift
    goto parse_args
)
if "%~1"=="/?" goto help
if "%~1"=="--help" goto help

echo ===============================================
echo    HH-Bot v4 Project Cleanup Utility
echo ===============================================
echo Start time: %DATE% %TIME%
echo Dry-run mode: %DRY_RUN%
echo Force mode: %FORCE%
echo Project root: %PROJECT_ROOT%
echo.

:: Проверка критичных файлов перед очисткой
echo [1/6] Project integrity check...
if not exist "%PROJECT_ROOT%cli_v4.py" (
    echo ERROR: Missing main file cli_v4.py
    exit /b 1
)
if not exist "%PROJECT_ROOT%data\hh_v4.sqlite3" (
    echo WARNING: Missing main DB hh_v4.sqlite3
)
if not exist "%PROJECT_ROOT%config\config_v4.json" (
    echo ERROR: Missing main config config_v4.json
    exit /b 1
)
echo OK: Required files are present

:: Создание архивных папок
echo.
echo [2/6] Creating archive folders...
if "%DRY_RUN%"=="false" (
    if not exist "%PROJECT_ROOT%docs\archive" mkdir "%PROJECT_ROOT%docs\archive"
    if not exist "%PROJECT_ROOT%scripts\archive" mkdir "%PROJECT_ROOT%scripts\archive"
    if not exist "%PROJECT_ROOT%data\.trash" mkdir "%PROJECT_ROOT%data\.trash"
    echo OK: Archive folders created
) else (
    echo [DRY-RUN] Would create: docs\archive, scripts\archive, data\.trash
)

:: Очистка Python кэша
echo.
echo [3/6] Cleaning Python cache...
set "CACHE_COUNT=0"
for /d /r "%PROJECT_ROOT%" %%d in (__pycache__) do (
    if exist "%%d" (
        set /a CACHE_COUNT=!CACHE_COUNT!+1
        if "%DRY_RUN%"=="false" (
            echo Delete: %%d
            rmdir /s /q "%%d" 2>nul
        ) else (
            echo [DRY-RUN] Would delete: %%d
        )
    )
)
echo Processed cache dirs: !CACHE_COUNT!

:: Удаление старых бэкапов БД
echo.
echo [4/6] Cleaning old DB backups...
set "BACKUP_COUNT=0"
for %%f in ("%PROJECT_ROOT%data\hh_v4_backup_*.sqlite3") do (
    set "FILE=%%f"
    :: Проверяем возраст файла (упрощенно - по дате в имени)
    echo !FILE! | findstr /r "202509[01][0-9]" >nul
    if !errorlevel! equ 0 (
        set /a BACKUP_COUNT=!BACKUP_COUNT!+1
        if "%DRY_RUN%"=="false" (
            echo Delete old backup: %%f
            del /q "%%f" 2>nul
        ) else (
            echo [DRY-RUN] Would delete: %%f
        )
    )
)
echo Processed old backups: !BACKUP_COUNT!

:: Архивация устаревшей документации
echo.
echo [5/6] Archiving outdated docs...
set "ARCHIVE_COUNT=0"

:: Список файлов для архивации
set "FILES_TO_ARCHIVE=Architecture_v4_Checklist.md Architecture_v4_Part1_TaskQueue.md Architecture_v4_Part2_Structure.md Architecture_v4_Part3_Documentation.md Architecture_v4_Summary.md"

for %%f in (%FILES_TO_ARCHIVE%) do (
    if exist "%PROJECT_ROOT%docs\%%f" (
        set /a ARCHIVE_COUNT=!ARCHIVE_COUNT!+1
        if "%DRY_RUN%"=="false" (
            echo Archive: docs\%%f
            move "%PROJECT_ROOT%docs\%%f" "%PROJECT_ROOT%docs\archive\%%f_old_%TIMESTAMP%" >nul
        ) else (
            echo [DRY-RUN] Would archive: docs\%%f
        )
    )
)
echo Archived docs: !ARCHIVE_COUNT!

:: Очистка старых логов
echo.
echo [6/6] Cleaning old logs...
set "LOG_COUNT=0"
if exist "%PROJECT_ROOT%logs" (
    pushd "%PROJECT_ROOT%logs"
    if "%DRY_RUN%"=="false" (
        rem Delete logs older than 14 days (requires forfiles)
        forfiles /p . /m *.log /d -14 /c "cmd /c echo Delete: @path & del @path" 2>nul
        if !errorlevel! equ 0 set /a LOG_COUNT=!LOG_COUNT!+1
        rem Rotate large logs (>100MB)
        for %%f in (*.log) do (
            for %%s in ("%%f") do (
                if %%~zs gtr 104857600 (
                    echo Rotate large log: %%f (%%~zs bytes)
                    ren "%%f" "%%f.1" 2>nul
                    echo. > "%%f"
                    set /a LOG_COUNT=!LOG_COUNT!+1
                )
            )
        )
    ) else (
        rem List candidates in dry-run without using forfiles
        for %%f in (*.log) do (
            echo [DRY-RUN] Keep log: %%f
        )
    )
    popd
) else (
    echo logs folder not found
)
echo Processed logs: !LOG_COUNT!

:: Финальная проверка
echo.
echo ===============================================
echo              CLEANUP SUMMARY
echo ===============================================
echo Python cache dirs: !CACHE_COUNT!
echo Old DB backups: !BACKUP_COUNT!
echo Archived docs: !ARCHIVE_COUNT!
echo Logs processed: !LOG_COUNT!

if "%DRY_RUN%"=="true" (
    echo.
    echo DRY-RUN MODE - no files changed
    echo To apply changes, run without --dry-run
) else (
    echo.
    echo Cleanup finished successfully
    echo Verify: python cli_v4.py status
)

echo.
echo End time: %DATE% %TIME%
goto end

:help
echo.
echo Usage: cleanup_project.bat [options]
echo.
echo Options:
echo   --dry-run    Show actions without changing files
echo   --force      Force execution without prompts
echo   --help, /?   Show this help
echo.
echo Examples:
echo   cleanup_project.bat --dry-run     - Test run
echo   cleanup_project.bat               - Normal cleanup
echo   cleanup_project.bat --force       - Forced cleanup
echo.
goto end

:end
:: // Chg_NOPAUSE_1909: Возможность пропустить паузу из IDE
endlocal
if "%NOPAUSE%"=="1" goto :eof
pause
