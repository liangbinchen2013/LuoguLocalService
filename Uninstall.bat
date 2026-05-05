@echo off
chcp 936
title 洛谷通知服务 卸载程序
echo ==============================================
echo         洛谷通知服务 卸载程序
echo ==============================================
echo.
echo 即将停止服务、取消自启、删除程序目录
echo 按任意键继续...
pause >nul

set "PROG_DIR=C:\Program Files\LuoguNotify"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo [1/3] 停止服务...
taskkill /f /im pythonw.exe >nul 2>nul

echo [2/3] 删除自启动项...
del "%STARTUP%\LuoguNotifyServer.lnk" >nul 2>nul
del "%STARTUP%\LuoguNotifyProxy.lnk" >nul 2>nul

echo [3/3] 删除程序目录...
rmdir /s /q "%PROG_DIR%" >nul 2>nul

echo.
echo 卸载完成！
echo 按任意键退出...
pause >nul