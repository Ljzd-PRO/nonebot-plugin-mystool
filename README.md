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
### 2023.7.19 - v1.1.0
- 增加崩坏：星穹铁道的便笺功能 #140 #143 by @Joseandluue @RemiDre
    > 说明文档：[🔗星穹铁道实时便笺](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Information-StarRailStatus)
- 修复每小时都发送便笺通知的Bug #135
- 人机验证打码平台支持自定义JSON内容 #133
    > 说明文档：[🔗geetest_json](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-Preference#geetest_json)
- 修复商品兑换API（但因加入了人机验证，实际大概率兑换失败）#110
- 不在好友列表的用户数据在删除前将进行备份 #129
    > 备份目录：`data/nonebot_plugin_mystool/deletedUsers`
- 防止因插件数据文件中默认存在 device_config, salt_config 而导致更新后默认配置被原配置覆盖的问题
- 若需要修改 device_config 配置，修改后还设置插件数据文件中 preference.override_device_and_salt 为 true 以覆盖默认值
    > 说明文档：
    > - [🔗网络请求设备信息 `class DeviceConfig`](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-DeviceConfig)
    > - [🔗override_device_and_salt](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-Preference#override_device_and_salt)
- 在兑换开始后的一段时间内不断尝试兑换，直到成功
  > 完整流程：兑换开始后，数个线程同时进行，每个线程在一段时间内重复发送兑换请求  
  > 因此，不建议将 `preference.exchange_thread_count` 设置过大，以免触发请求频繁的返回  
  > 原因：[太早兑换可能被认定不在兑换时间](https://github.com/Ljzd-PRO/Mys_Goods_Tool/discussions/135#discussioncomment-6487717)
- 兑换开始后将不会延迟兑换，用户数据文件中 `preference.exchange_latency` 将作为同一线程下每个兑换请求之间的时间间隔
  > `preference.exchange_latency` 为列表类型，包含两个浮点数，分别为最小延迟和最大延迟，单位为秒，可参考默认值  
  > 建议将 `preference.exchange_latency`, `preference.exchange_thread_count` 设为最新默认值，直接从插件数据文件中删除它们即可
- 兑换请求日志内容增加了发送请求时的时间戳

### 2023.6.23 - v1.0.1
- 修复无法导出Cookies的问题
- 修复因缺少参量质变仪数据而导致不断提醒的Bug
- 修复账号设置中游戏签到开启/关闭状态实际对应的是米游币任务的Bug #121 by @xxtg666

### 2023.6.23 - v1.0.0
#### v1.0.0
- 修复Windows, macOS多进程生成商品图片失败的问题 [#120](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/pull/120) by @Night-stars-1

#### v1.0.0-beta.2
- 支持使用人机验证打码平台处理人机验证任务 [#119](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/pull/119) by @Night-stars-1
- 原神便笺获取失败时更换为使用米游社iOS小组件API获取 [#119](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/pull/119) by @Night-stars-1
- 修复原神便笺和讨论区签到可能因为DS无效而失败的问题

#### v1.0.0-beta.1
- 大量的代码重构，包括米游社API的客户端实现、用户数据相关、插件配置相关、API相关数据模型
- 从显示用户账号绑定的手机号改为显示账号的米游社ID
- 设置、兑换计划功能支持群聊使用
- 登陆绑定只需要进行一次短信验证
- 用户数据文件、插件配置文件 **格式更新，与 v1.0.0 之前的版本不兼容**
- 修复添加兑换任务时出现的UID不存在错误
- 修复商品图片生成完才发出后台正在生成提示的问题
- 异常捕获更加准确
- 改进了一些文本

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
