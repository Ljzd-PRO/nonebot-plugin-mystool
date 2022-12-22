"""
 __    __     __  __     ______     ______   ______     ______     __
/\ "-./  \   /\ \_\ \   /\  ___\   /\__  _\ /\  __ \   /\  __ \   /\ \
\ \ \-./\ \  \ \____ \  \ \___  \  \/_/\ \/ \ \ \/\ \  \ \ \/\ \  \ \ \____
 \ \_\ \ \_\  \/\_____\  \/\_____\    \ \_\  \ \_____\  \ \_____\  \ \_____\
  \/_/  \/_/   \/_____/   \/_____/     \/_/   \/_____/   \/_____/   \/_____/

# mysTool - 米游社辅助工具插件

**版本 - v0.2.0**

📣 更新：进行了修复与优化。新增原神树脂、洞天宝盆、质量参变仪状态查看和提醒等功能。

## 功能和特性

- 短信验证登录，免抓包获取 Cookie
- 自动完成每日米游币任务
- 自动进行游戏签到
- 可制定米游币商品兑换计划，到点兑换
- 可支持多个 QQ 账号，每个 QQ 账号可绑定多个米哈游账户
- QQ 推送执行结果通知
- 原神树脂、洞天宝盆、质量参变仪已满时推送通知

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

> ⚠️ 注意 此处没有使用 [🔗 插件命令头](https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki/Configuration-Config#command_start)
"""

import pkgutil
from pathlib import Path

from nonebot.plugin import PluginMetadata

VERSION = "v0.2.0"
'''插件版本号'''

__plugin_meta__ = PluginMetadata(
    name="❖米游社小助手插件❖\n版本 - {}\n".format(VERSION),
    description="米游社工具-每日米游币任务、游戏签到、商品兑换、免抓包登录\n",
    usage="""
    \n🔐 {HEAD}登录 ➢ 登录绑定米游社账户\
    \n📦 {HEAD}地址 ➢ 设置收货地址ID\
    \n🗓️ {HEAD}签到 ➢ 手动进行游戏签到\
    \n📅 {HEAD}任务 ➢ 手动执行米游币任务\
    \n🛒 {HEAD}兑换 ➢ 米游币商品兑换相关\
    \n🎁 {HEAD}商品 ➢ 查看米游币商品信息(商品ID)\
    \n📊 {HEAD}便笺 ➢ 查看原神实时便笺(原神树脂、洞天财瓮等)\
    \n⚙️ {HEAD}设置 ➢ 设置是否开启通知、每日任务等相关选项\
    \n🔑 {HEAD}账号设置 ➢ 设置设备平台、是否开启每日计划任务、频道任务\
    \n🔔 {HEAD}通知设置 ➢ 设置是否开启每日米游币任务、游戏签到的结果通知\
    \n📖 {HEAD}帮助 ➢ 查看帮助信息\
    \n🔍 {HEAD}帮助 <功能名> ➢ 查看目标功能详细说明\
    \n⚠️你的数据将经过机器人服务器，请确定你信任服务器所有者再使用。\
    \n\n🔗项目地址：https://github.com/Ljzd-PRO/nonebot-plugin-mystool\
    \n🔗详细使用说明：https://github.com/Ljzd-PRO/nonebot-plugin-mystool/wiki
    """.strip(),
    extra={"version": VERSION}
)

# 加载其它代码

FILE_PATH = Path(__file__).parent.absolute()

for _, file, _ in pkgutil.iter_modules([str(FILE_PATH)]):
    __import__(file, globals(), level=1)
