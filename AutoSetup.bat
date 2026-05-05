@echo off
chcp 936
title 洛谷通知服务 安装程序
echo ==============================================
echo         洛谷通知服务 安装程序
echo ==============================================
echo.
echo 操作说明：
echo 1. 将程序文件移动至系统程序目录
echo 2. 请手动安装 LuoguChatNotify.user.js 到油猴
echo 3. 请手动打开浏览器登录洛谷并保持标签常驻
echo 4. 程序自动配置依赖与开机自启动
echo 5. 安装完成后本程序自动删除
echo.
echo 请以管理员身份运行本程序
echo 按任意键开始执行...
pause >nul
echo.

set "PROG_DIR=C:\Program Files\LuoguNotify"
set "CUR_DIR=%~dp0"
set "SELF=%~nx0"

fltmc >nul 2>nul || (
    echo 错误：请右键选择【以管理员身份运行】
    pause >nul
    exit /b
)

if not exist "%PROG_DIR%" mkdir "%PROG_DIR%"

echo [1/4] 移动程序文件到系统目录
move /y "%CUR_DIR%LuoguNotifyServer.py" "%PROG_DIR%\" >nul
move /y "%CUR_DIR%LuoguNotifyProxy.py" "%PROG_DIR%\" >nul
move /y "%CUR_DIR%Uninstall.bat" "%PROG_DIR%\" >nul
echo 文件移动完成

echo.
echo ==============================================
echo 请手动操作：
echo 1. 安装同目录下 LuoguChatNotify.user.js 到油猴
echo 2. 打开浏览器，登录洛谷
echo 3. 保留洛谷标签不要关闭，最小化后台挂着即可接收通知
echo ==============================================
echo.
echo 按任意键继续后续配置...
pause >nul
echo.

echo [2/4] 检测并安装Python依赖库
pip install flask win10toast >nul 2>nul
echo 依赖库安装完成

echo [3/4] 配置开机自启动项
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\Short1.vbs"
echo sLinkFile = "%STARTUP%\LuoguNotifyServer.lnk" >> "%TEMP%\Short1.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\Short1.vbs"
echo oLink.TargetPath = "pythonw.exe" >> "%TEMP%\Short1.vbs"
echo oLink.Arguments = """%PROG_DIR%\LuoguNotifyServer.py""" >> "%TEMP%\Short1.vbs"
echo oLink.WorkingDirectory = "%PROG_DIR%" >> "%TEMP%\Short1.vbs"
echo oLink.Save >> "%TEMP%\Short1.vbs"
cscript /nologo "%TEMP%\Short1.vbs"
del "%TEMP%\Short1.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\Short2.vbs"
echo sLinkFile = "%STARTUP%\LuoguNotifyProxy.lnk" >> "%TEMP%\Short2.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\Short2.vbs"
echo oLink.TargetPath = "pythonw.exe" >> "%TEMP%\Short2.vbs"
echo oLink.Arguments = """%PROG_DIR%\LuoguNotifyProxy.py""" >> "%TEMP%\Short2.vbs"
echo oLink.WorkingDirectory = "%PROG_DIR%" >> "%TEMP%\Short2.vbs"
echo oLink.Save >> "%TEMP%\Short2.vbs"
cscript /nologo "%TEMP%\Short2.vbs"
del "%TEMP%\Short2.vbs"
echo 开机自启动配置完成

echo [4/4] 启动后台服务
start /B pythonw "%PROG_DIR%\LuoguNotifyServer.py"
timeout /t 1 /nobreak >nul
start /B pythonw "%PROG_DIR%\LuoguNotifyProxy.py"

echo.
echo ==============================================
echo 安装配置全部完成
echo 程序目录：%PROG_DIR%
echo 服务已后台静默运行
echo 请自行保持洛谷网页标签常驻后台
echo 本安装程序即将自动删除
echo ==============================================
timeout /t 2 /nobreak >nul

echo del /f /q "%CUR_DIR%%SELF%" > "%TEMP%\DelSelf.bat"
cmd /c "%TEMP%\DelSelf.bat"