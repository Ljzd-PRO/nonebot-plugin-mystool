from nonebot.plugin import PluginMetadata
from . import login, address, timing, setting, addfriend


__plugin_meta__ = PluginMetadata(
    name="原神签到、米游币获取、米游币兑换插件",
    description="通过手机号获取cookie，每日自动原神签到、获取米游币，可制定米游币兑换计划",
    usage="""\
        cookie 跟随指引获取cookie
        address 获取地址ID
        setting 配置签到、播报相关选项
        yssign 手动进行原神签到
        bbssign 手动进行米游社签到\
    """
)