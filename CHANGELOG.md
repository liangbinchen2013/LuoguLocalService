# 更新日志

所有重要变更都会记录在此。

## [v1.0.0] - 2026-06-07

**项目的第一个正式版本！** 实现功能如下：

```
  命令              说明
  --------------------------------------------------
  article          查看文章 <ID>
  articles         查看最新文章（可翻页选择）
  color            管理用户自定义颜色
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


## [v0.2.0] - 2026-06-02

### 新增

- 查看讨论回复评论
- 查看文章评论
- 长内容分页显示
- LaTeX简单映射 (Beta)
- 每日打卡
- 自定义用户颜色
- 查看陶片放逐信息 (Beta)
- 详细日志开关 (Beta)

## [v0.1.0] - 2026-06-01

### 功能实现

项目第一个版本，实现洛谷命令行工具基础核心功能，支持全部常用操作：
```
  命令              说明
  --------------------------------------------------
  article          查看文章 <ID>
  articles         查看最新文章（可翻页选择）
  discuss          查看讨论帖 <ID>
  discusses        查看最新讨论（可翻页选择）
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
