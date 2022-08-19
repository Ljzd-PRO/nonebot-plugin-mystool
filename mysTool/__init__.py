from nonebot.plugin import PluginMetadata
from . import addfriend, address, help, login, myb_exchange, setting, timing, utils


__plugin_meta__ = PluginMetadata(
    name="---米游社小助手插件---\n",
    description="通过手机号获取cookie，每日自动进行原神等米哈游游戏签到、获取米游币，可制定米游币兑换计划\n",
    usage=
    """
    /登录-跟随指引获取cookie\
    \n/地址填写-获取地址ID\
    \n/设置-配置签到、播报相关选项\
    \n/游戏签到-手动进行米哈游游戏签到\
    \n/米游社任务-手动进行米游社签到\
    \n/兑换-进行米游社商品兑换\
    \n/商品列表-查看米游社当前商品\
    \n/帮助-查看帮助\
    \n/帮助-<功能名> 查看某一用法具体帮助
    """.strip(),
    extra="项目地址：https://github.com/Ljzd-PRO/nonebot-plugin-mysTool\n欢迎提出建议和意见！"
)