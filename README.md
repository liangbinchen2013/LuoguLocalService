# LuoguLocalService
Luogu 本地化服务。

## 项目简介

一款面向洛谷平台的本地辅助工具，支持 CMD 命令行操控洛谷相关功能。

目前所支持的功能：
```
  命令              说明
  --------------------------------------------------
  article          查看文章 <ID>
  discuss          查看讨论帖 <ID>
  exit             退出程序
  feed             查看犇犇动态
  help             显示帮助信息
  home             查看主页运势/动态
  login            登录洛谷
  logout           退出登录(清除Cookie)
  problem          查看题目预览 <PID>
  profile          查看用户资料 [UID]
  quit             退出程序
```

## 项目依赖

- Python 
- pip install requests
- pip install rich
- pip install colorama

## 注意

本项目的OCR验证码服务来源于 https://ocr.lbcoj.top/ 如果你有实力，可以自己安装识别服务。速度会更快。

服务：[github](https://github.com/gitpetyr/ppllocr/)
