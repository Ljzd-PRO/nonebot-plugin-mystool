from nonebot.plugin import PluginMetadata
from . import login, address, timing

__plugin_meta__ = PluginMetadata(
    name="原神签到、米游币获取、米游币兑换插件",
    description="通过手机号获取cookie，每日自动原神签到、获取米游币，可制定米游币兑换计划",
    usage=(
        "get_cookie 跟随指引获取cookie\n"
        "get_address 获取地址ID\n"
        "get_myb 订阅每日自动获取米游币计划\n"
        "get_yuanshen 订阅每日自动原神签到计划\n"
        "myb_info 查看米游币数量\n"
        "yuanshen_info 查看当日原神签到奖励，当月原石、摩拉获取\n"
        "myb_exchange 制定米游币兑换计划\n"
        "myb_exchange_info 查看当前米游币兑换计划\n"
        "myb_delete 删除你的所有兑换计划\n"
    )
)
