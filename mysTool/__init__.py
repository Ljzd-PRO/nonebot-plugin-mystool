from nonebot.plugin import PluginMetadata
from . import login, address, timing, setting, addfriend, help


__plugin_meta__ = PluginMetadata(
    name="---米游社小助手插件---\n",
    description="通过手机号获取cookie，每日自动原神签到、获取米游币，可制定米游币兑换计划\n",
    usage=
    """
    /cookie 跟随指引获取cookie\
    \n/address 获取地址ID\
    \n/setting 配置签到、播报相关选项\
    \n/yssign 手动进行原神签到\
    \n/bbssign 手动进行米游社签到\
    \n/help 查看帮助\
    \n/help + 用法 查看某一用法具体帮助
    """.strip()
)