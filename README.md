```
 __    __     __  __     ______     ______   ______     ______     __
/\ "-./  \   /\ \_\ \   /\  ___\   /\__  _\ /\  __ \   /\  __ \   /\ \
\ \ \-./\ \  \ \____ \  \ \___  \  \/_/\ \/ \ \ \/\ \  \ \ \/\ \  \ \ \____
 \ \_\ \ \_\  \/\_____\  \/\_____\    \ \_\  \ \_____\  \ \_____\  \ \_____\
  \/_/  \/_/   \/_____/   \/_____/     \/_/   \/_____/   \/_____/   \/_____/
```

<div>
  <img alt="CodeFactor" src="https://www.codefactor.io/repository/github/ljzd-pro/nonebot-plugin-mystool/badge?style=for-the-badge">
  <img alt="最新发行版" src="https://img.shields.io/github/v/release/Ljzd-PRO/nonebot-plugin-mysTool?logo=python&style=for-the-badge">
  <img alt="最后提交" src="https://img.shields.io/github/last-commit/Ljzd-PRO/nonebot-plugin-mysTool?style=for-the-badge">
</div>

# mysTool - 米游社辅助工具插件

**版本 - v1.0.0-beta.1**

### 📣 更新内容

#### 2023.6.10

改动较大，目前是 Beta 版，可能不稳定

- 大量的代码重构，包括米游社API的客户端实现、用户数据相关、插件配置相关、API相关数据模型
- 修复在 Windows 下无法多进程生成商品图片的问题
- 从显示用户账号绑定的手机号改为显示账号的米游社ID
- 设置、兑换计划功能支持群聊使用
- 登陆绑定只需要进行一次短信验证
- 用户数据文件、插件配置文件 **格式更新，与 v1.0.0 之前的版本不兼容**
- 修复添加兑换任务时出现的UID不存在错误
- 修复商品图片生成完才发出后台正在生成提示的问题
- 异常捕获更加准确
- 改进了一些文本

#### 2023.5.18
- 多进程生成商品图片（多核），加快图片生成速度
- 修复部分商品兑换时间错误的问题（如米游社商品晚了一周）

#### 2023.5.4
- 增加对星穹铁道的签到功能的支持 - [#89](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/pull/89) by @ayakasuki
- 修复插件命令优先度问题 - [#88](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/pull/88) by @ayakasuki
- 部分文本错误修正 - [#90](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/pull/90) by @black-zero358

...

#### 2023.3.30
- 修复 `/兑换` 命令可能与其他插件命令冲突的问题，同时 [🔗用法变更](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Information-Exchange#增加删除兑换计划)
- ...

## 功能和特性

- 短信验证登录，免抓包获取 Cookie
- 自动完成每日米游币任务
- 自动进行游戏签到
- 可制定米游币商品兑换计划，到点兑换
- 可支持多个 QQ 账号，每个 QQ 账号可绑定多个米哈游账户
- QQ 推送执行结果通知
- 原神树脂、洞天宝钱、质量参变仪已满时推送通知

## 使用说明

### 🛠️ NoneBot2 机器人部署和插件安装

请查看 -> [🔗Installation](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Installation)

### 📖 插件具体使用说明

请查看 -> [🔗Wiki 文档](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki)

### ❓ 获取插件帮助信息

#### 插件命令

```
/帮助
```

> ⚠️ 注意 此处没有使用 [🔗 插件命令头](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-Config#commandstart)

## 其他

### [📃源码说明](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Source-Structure)
### 适配 [绪山真寻Bot](https://github.com/HibiKier/zhenxun_bot) 的分支
- https://github.com/MWTJC/zhenxun-plugin-mystool
- https://github.com/ayakasuki/nonebot-plugin-mystool
