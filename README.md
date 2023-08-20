```
 __    __     __  __     ______     ______   ______     ______     __
/\ "-./  \   /\ \_\ \   /\  ___\   /\__  _\ /\  __ \   /\  __ \   /\ \
\ \ \-./\ \  \ \____ \  \ \___  \  \/_/\ \/ \ \ \/\ \  \ \ \/\ \  \ \ \____
 \ \_\ \ \_\  \/\_____\  \/\_____\    \ \_\  \ \_____\  \ \_____\  \ \_____\
  \/_/  \/_/   \/_____/   \/_____/     \/_/   \/_____/   \/_____/   \/_____/
```

[![CodeFactor](https://www.codefactor.io/repository/github/ljzd-pro/nonebot-plugin-mystool/badge?style=for-the-badge)](https://www.codefactor.io/repository/github/ljzd-pro/nonebot-plugin-mystool)
[![最新发行版](https://img.shields.io/github/v/release/Ljzd-PRO/nonebot-plugin-mysTool?logo=python&style=for-the-badge)](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/releases/latest)
[![最后提交](https://img.shields.io/github/last-commit/Ljzd-PRO/nonebot-plugin-mysTool/dev?style=for-the-badge)](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/commits/dev)

# mysTool - 米游社辅助工具插件

## 📣 更新内容
### 2023.8.21 - v1.3.0
- 修复米游币任务中**讨论区签到失败**的问题 #173
- **讨论区签到**增加通过打码平台自动完成**人机验证**的支持 #157
  > [插件偏好设置 - geetest_url](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-Preference#geetest_url)
- 修复每日米游币任务、游戏签到、便笺提醒**无法私聊推送消息**的问题 #173
- **修复实时便笺**提醒的一些逻辑问题 #152 #171
- 完善实时便笺功能的推送文本
- 尝试修复米游社内实时便笺接口
- 修复使用绑定功能的情况下每日任务重复执行的问题
- 修复只有第一个绑定关系有效的问题
- 增加兑换计划商品不存在、已下架的检查，防止插件导入失败 #172

### 2023.8.4 - v1.2.0
- 修复原神签到返回DS无效的问题 #150 #134
- 修复崩坏三签到返回 “签到功能维护中，请耐心等待” 的问题 #139 #131 #130
- 修复使用QQ频道适配器的情况下可能因为发送消息失败而无法继续的问题 
- 取消了自动删除非好友的用户数据的功能
- 增加对QQ频道的支持 #128
  > 说明文档：[🔗QQGuild 适配器](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Installation#QQGuild-适配器)
- 增加用户数据绑定关联功能（如QQ频道账号与QQ聊天账号的数据绑定）
  > 说明文档：[🔗用户数据绑定关联](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Information-UserBind)
- 增加原神便笺树脂提醒阈值的设置选项 #151 by @Joseandluue
  > 说明文档：[🔗对绑定的某个米哈游账户进行设置](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Information-Setting#%E5%AF%B9%E7%BB%91%E5%AE%9A%E7%9A%84%E6%9F%90%E4%B8%AA%E7%B1%B3%E5%93%88%E6%B8%B8%E8%B4%A6%E6%88%B7%E8%BF%9B%E8%A1%8C%E8%AE%BE%E7%BD%AE)
- 修复 `preference.override_device_and_salt` 关闭无效的问题

## 功能和特性

- 支持QQ聊天和QQ频道
- 短信验证登录，免抓包获取 Cookie
- 自动完成每日米游币任务
- 自动进行游戏签到
- 可制定米游币商品兑换计划，到点兑换（因加入了人机验证，成功率较低）
- 可支持多个 QQ 账号，每个 QQ 账号可绑定多个米哈游账户
- QQ 推送执行结果通知
- 原神、崩坏：星穹铁道状态便笺通知
- 可为每日米游币任务、游戏签到配置人机验证打码平台

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

### 贡献
<a href="https://github.com/Ljzd-PRO/nonebot-plugin-mystool/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Ljzd-PRO/nonebot-plugin-mystool&max=1000" alt="贡献者"/>
</a>

### 源码说明
[📃Source-Structure](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Source-Structure)

### 适配 [绪山真寻Bot](https://github.com/HibiKier/zhenxun_bot) 的分支
- https://github.com/MWTJC/zhenxun-plugin-mystool
- https://github.com/ayakasuki/nonebot-plugin-mystool
