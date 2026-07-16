# LuoguLocalService
Luogu 本地化服务。

## 项目简介

一款面向洛谷平台的本地辅助工具，支持 CMD 命令行操控洛谷相关功能。

目前所支持的功能：
```
  命令              说明
  --------------------------------------------------
  article          查看文章 <ID>
  articles         查看最新文章（可翻页选择）
  color            管理用户自定义颜色
  create           创建C++代码文件并打开编辑器编辑
  disclaimer       查看免责声明与隐私声明
  discuss          查看讨论帖 <ID>
  discusses        查看最新讨论（可翻页选择）
  exit             退出程序
  feed             查看犇犇动态
  help             显示帮助信息
  home             查看主页运势/动态
  judgement        陶片放逐（处罚日志）
  login            登录洛谷
  logout           退出登录(清除Cookie)
  note             管理用户备注
  problem          查看题目预览 <PID>
  problems         题目列表
  profile          查看用户资料 [UID]
  punch            每日打卡
  quit             退出程序
  search           搜索题目
  sessions         列出所有已保存的会话
  switch           切换当前用户
  verbose          切换详细日志
```

## 项目依赖

**Python**
- pip install requests
- pip install rich
- pip install colorama

## 使用步骤

把三个python文件放到一个目录里，然后打开CMD，进入该目录，执行以下命令：
```
python main.py
```

## 注意

本项目的OCR验证码服务来源于 https://lgocr.lbcoj.top/ 
