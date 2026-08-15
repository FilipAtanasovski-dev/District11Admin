@echo off
setlocal

title Restaurant App

:: ============================================================
:: SETTINGS
:: ============================================================

set "CONFIG_FILE=%~dp0server_ip.txt"

:: ============================================================
:: LOAD PREVIOUSLY SAVED IP
:: ============================================================

set "SAVED_IP="

if exist "%CONFIG_FILE%" (
    set /p "SAVED_IP="<"%CONFIG_FILE%"
)

:: ============================================================
:: ASK FOR SERVER IP
:: ============================================================

echo.
echo ============================================================
echo                 RESTAURANT APP LAUNCHER
echo ============================================================
echo.

if defined SAVED_IP (
    echo Enter the IP address of the computer running
    echo the Restaurant Server.
    echo.
    echo Press ENTER to use the saved IP.
    echo.
    set /p "SERVER_IP=Server IP [%SAVED_IP%]: "

    if not defined SERVER_IP (
        set "SERVER_IP=%SAVED_IP%"
    )
) else (
    echo Enter the IP address of the computer running
    echo the Restaurant Server.
    echo.
    echo Example: 192.168.0.30
    echo.
    set /p "SERVER_IP=Server IP: "
)

:: Remove accidental spaces
set "SERVER_IP=%SERVER_IP: =%"

:: ============================================================
:: CHECK THAT AN IP WAS ENTERED
:: ============================================================

if not defined SERVER_IP (
    echo.
    echo ERROR: No server IP was entered.
    echo.
    pause
    exit /b
)

:: ============================================================
:: SAVE IP FOR FUTURE USE
:: ============================================================

echo %SERVER_IP%>"%CONFIG_FILE%"

:: ============================================================
:: BUILD APPLICATION URL
:: ============================================================

set "URL=http://%SERVER_IP%:8000"

echo.
echo ============================================================
echo.
echo Server IP: %SERVER_IP%
echo Server URL: %URL%
echo.
echo IP saved for future use.
echo.
echo Starting Restaurant App...
echo ============================================================
echo.

:: ============================================================
:: GOOGLE CHROME
:: ============================================================

if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" --kiosk "%URL%"
    exit /b
)

if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    start "" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
    start "" "%LocalAppData%\Google\Chrome\Application\chrome.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: MICROSOFT EDGE
:: ============================================================

if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --kiosk "%URL%" --edge-kiosk-type=fullscreen
    exit /b
)

if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" --kiosk "%URL%" --edge-kiosk-type=fullscreen
    exit /b
)

:: ============================================================
:: BRAVE
:: ============================================================

if exist "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe" (
    start "" "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe" --kiosk "%URL%"
    exit /b
)

if exist "%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe" (
    start "" "%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe" (
    start "" "%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: VIVALDI
:: ============================================================

if exist "%ProgramFiles%\Vivaldi\Application\vivaldi.exe" (
    start "" "%ProgramFiles%\Vivaldi\Application\vivaldi.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\Vivaldi\Application\vivaldi.exe" (
    start "" "%LocalAppData%\Vivaldi\Application\vivaldi.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: OPERA
:: ============================================================

if exist "%ProgramFiles%\Opera\launcher.exe" (
    start "" "%ProgramFiles%\Opera\launcher.exe" --kiosk "%URL%"
    exit /b
)

if exist "%ProgramFiles(x86)%\Opera\launcher.exe" (
    start "" "%ProgramFiles(x86)%\Opera\launcher.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\Programs\Opera\launcher.exe" (
    start "" "%LocalAppData%\Programs\Opera\launcher.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: OPERA GX
:: ============================================================

if exist "%ProgramFiles%\Opera GX\launcher.exe" (
    start "" "%ProgramFiles%\Opera GX\launcher.exe" --kiosk "%URL%"
    exit /b
)

if exist "%ProgramFiles(x86)%\Opera GX\launcher.exe" (
    start "" "%ProgramFiles(x86)%\Opera GX\launcher.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\Programs\Opera GX\launcher.exe" (
    start "" "%LocalAppData%\Programs\Opera GX\launcher.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: TORCH
:: ============================================================

if exist "%ProgramFiles%\Torch\Application\torch.exe" (
    start "" "%ProgramFiles%\Torch\Application\torch.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\Torch\Application\torch.exe" (
    start "" "%LocalAppData%\Torch\Application\torch.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: YANDEX
:: ============================================================

if exist "%ProgramFiles%\Yandex\YandexBrowser\Application\browser.exe" (
    start "" "%ProgramFiles%\Yandex\YandexBrowser\Application\browser.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\Yandex\YandexBrowser\Application\browser.exe" (
    start "" "%LocalAppData%\Yandex\YandexBrowser\Application\browser.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: WATERFOX
:: ============================================================

if exist "%ProgramFiles%\Waterfox\waterfox.exe" (
    start "" "%ProgramFiles%\Waterfox\waterfox.exe" --kiosk "%URL%"
    exit /b
)

if exist "%ProgramFiles(x86)%\Waterfox\waterfox.exe" (
    start "" "%ProgramFiles(x86)%\Waterfox\waterfox.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\Waterfox\waterfox.exe" (
    start "" "%LocalAppData%\Waterfox\waterfox.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: MOZILLA FIREFOX
:: ============================================================

if exist "%ProgramFiles%\Mozilla Firefox\firefox.exe" (
    start "" "%ProgramFiles%\Mozilla Firefox\firefox.exe" --kiosk "%URL%"
    exit /b
)

if exist "%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe" (
    start "" "%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe" --kiosk "%URL%"
    exit /b
)

if exist "%LocalAppData%\Mozilla Firefox\firefox.exe" (
    start "" "%LocalAppData%\Mozilla Firefox\firefox.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: ARC
:: ============================================================

if exist "%LocalAppData%\Programs\Arc\Arc.exe" (
    start "" "%LocalAppData%\Programs\Arc\Arc.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: MAXTHON
:: ============================================================

if exist "%ProgramFiles%\Maxthon\Application\Maxthon.exe" (
    start "" "%ProgramFiles%\Maxthon\Application\Maxthon.exe" --kiosk "%URL%"
    exit /b
)

if exist "%ProgramFiles(x86)%\Maxthon\Application\Maxthon.exe" (
    start "" "%ProgramFiles(x86)%\Maxthon\Application\Maxthon.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: CENT BROWSER
:: ============================================================

if exist "%ProgramFiles%\CentBrowser\Application\chrome.exe" (
    start "" "%ProgramFiles%\CentBrowser\Application\chrome.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: COMODO DRAGON
:: ============================================================

if exist "%ProgramFiles%\Comodo\Dragon\dragon.exe" (
    start "" "%ProgramFiles%\Comodo\Dragon\dragon.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: PALE MOON
:: ============================================================

if exist "%ProgramFiles%\Pale Moon\palemoon.exe" (
    start "" "%ProgramFiles%\Pale Moon\palemoon.exe" --kiosk "%URL%"
    exit /b
)

if exist "%ProgramFiles(x86)%\Pale Moon\palemoon.exe" (
    start "" "%ProgramFiles(x86)%\Pale Moon\palemoon.exe" --kiosk "%URL%"
    exit /b
)

:: ============================================================
:: INTERNET EXPLORER
:: ============================================================

if exist "%ProgramFiles%\Internet Explorer\iexplore.exe" (
    start "" "%ProgramFiles%\Internet Explorer\iexplore.exe" "%URL%"
    exit /b
)

:: ============================================================
:: NO BROWSER FOUND
:: ============================================================

echo.
echo ============================================================
echo       RESTAURANT APP - NO SUPPORTED BROWSER FOUND
echo ============================================================
echo.
echo Please install Google Chrome or Microsoft Edge.
echo.
echo Application address:
echo %URL%
echo.
pause

endlocal