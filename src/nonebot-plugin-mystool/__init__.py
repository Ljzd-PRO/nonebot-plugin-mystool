"""
 __    __     __  __     ______     ______   ______     ______     __
/\ "-./  \   /\ \_\ \   /\  ___\   /\__  _\ /\  __ \   /\  __ \   /\ \
\ \ \-./\ \  \ \____ \  \ \___  \  \/_/\ \/ \ \ \/\ \  \ \ \/\ \  \ \ \____
 \ \_\ \ \_\  \/\_____\  \/\_____\    \ \_\  \ \_____\  \ \_____\  \ \_____\
  \/_/  \/_/   \/_____/   \/_____/     \/_/   \/_____/   \/_____/   \/_____/

# mysTool - 米游社辅助工具插件

米游社工具-每日米游币任务、游戏签到、商品兑换、免抓包登录

## 功能和特性

- 短信验证登录，免抓包获取 Cookie
- 自动完成每日米游币任务
- 自动进行游戏签到
- 可制定米游币商品兑换计划，到点兑换
- 可支持多个 QQ 账号，每个 QQ 账号可绑定多个米哈游账户
- QQ 推送执行结果通知

## 使用说明

### ⚙️ NoneBot 机器人部署和插件安装

请查看 -> [🔗Installation](https://github.com/Ljzd-PRO/nonebot-plugin-mysTool/wiki/Installation)

### 📖 插件具体使用说明

请查看 -> [🔗Wiki 文档](https://github.com/Ljzd-PRO/nonebot-plugin-mysTool/wiki)
"""
from nonebot.plugin import PluginMetadata
from . import addfriend
from . import address
from . import help
from . import login
from . import myb_exchange
from . import setting
from . import timing
from . import utils

__plugin_meta__ = PluginMetadata(
    name="---米游社小助手插件---\n",
    description="米游社工具-每日米游币任务、游戏签到、商品兑换、免抓包登录\n",
    usage="""
    /登录 -> 跟随指引获取cookie\
    \n/地址填写 -> 获取地址ID\
    \n/设置 -> 配置签到、播报相关选项\
    \n/游戏签到 -> 手动进行米哈游游戏签到\
    \n/米游社任务 -> 手动进行米游社签到\
    \n/兑换 -> 进行米游社商品兑换\
    \n/商品列表 -> 查看米游社当前商品\
    \n/帮助 -> 查看帮助\
    \n/帮助 <功能名> -> 查看某一用法具体帮助
    """.strip(),
    extra="项目地址：https://github.com/Ljzd-PRO/nonebot-plugin-mysTool\n欢迎提出建议和意见！"
)
