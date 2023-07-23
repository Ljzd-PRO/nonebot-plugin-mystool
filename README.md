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

## 📣 更新内容
### 2023.7.23 - v1.1.0
- 增加崩坏：星穹铁道的便笺功能 #140 #143 by @Joseandluue @RemiDre
    > 说明文档：[🔗星穹铁道实时便笺](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Information-StarRailStatus)
- 修复每小时都发送便笺通知的Bug #135
- 人机验证打码平台支持自定义JSON内容 #133
    > 说明文档：[🔗geetest_json](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-Preference#geetest_json)
- 修复商品兑换API #110
- 不在好友列表的用户数据在删除前将进行备份 #129
    > 备份目录：`data/nonebot_plugin_mystool/deletedUsers`
- 防止因插件数据文件中默认存在 device_config, salt_config 而导致更新后默认配置被原配置覆盖的问题
- 若需要修改 device_config 配置，修改后还设置插件数据文件中 preference.override_device_and_salt 为 true 以覆盖默认值
    > 说明文档：
    > - [🔗网络请求设备信息 `class DeviceConfig`](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-DeviceConfig)
    > - [🔗override_device_and_salt](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-Preference#override_device_and_salt)
- 在兑换开始后的一段时间内不断尝试兑换，直到成功 #110
- 兑换开始后将不会延迟兑换，用户数据文件中 `preference.exchange_latency` 将作为同一线程下每个兑换请求之间的时间间隔 #110
- 兑换请求日志内容增加了发送请求时的时间戳

### 2023.6.23 - v1.0.1
- 修复无法导出Cookies的问题
- 修复因缺少参量质变仪数据而导致不断提醒的Bug
- 修复账号设置中游戏签到开启/关闭状态实际对应的是米游币任务的Bug #121 by @xxtg666

## 功能和特性

- 短信验证登录，免抓包获取 Cookie
- 自动完成每日米游币任务
- 自动进行游戏签到
- 可制定米游币商品兑换计划，到点兑换（因加入了人机验证，成功率较低）
- 可支持多个 QQ 账号，每个 QQ 账号可绑定多个米哈游账户
- QQ 推送执行结果通知
- 原神、崩坏：星穹铁道状态便笺通知

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
