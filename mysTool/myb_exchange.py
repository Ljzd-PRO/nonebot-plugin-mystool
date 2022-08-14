"""
### 米游社收货地址相关前端
"""
from .config import mysTool_config as conf
from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent

__cs = ''
if conf.USE_COMMAND_START:
    __cs = conf.COMMAND_START

myb_exchange_plan = on_command(
    __cs+'myb_exchange_plan', aliases={__cs+'myb_exchange', __cs+'米游币兑换', __cs+'米游币兑换计划', __cs+'兑换计划', __cs+'兑换'}, priority=4, block=True)
myb_exchange_plan.__help_name__ = "兑换"
myb_exchange_plan.__help_info__ = "跟随指引，配置米游币兑换计划，即可自动兑换米游社商品。换取实体商品前，必须要先配置地址id；兑换虚拟商品时，请跟随引导输入要兑换的账户的uid"

myb_exchange_info = on_command(
    __cs+'myb_exchange_info', aliases={__cs+'myb_info', __cs+'查看米游币兑换', __cs+'查看米游币兑换计划', __cs+'查看兑换计划', __cs+'兑换计划'}, priority=4, block=True)
myb_exchange_info.__help_name__ = "兑换计划"
myb_exchange_info.__help_info__ = "查看已经配置的米游社兑换计划"

myb_exchange_delete = on_command(
    __cs+'myb_exchange_delete', aliases={__cs+'myb_delete', __cs+'米游币兑换删除', __cs+'米游币兑换计划删除', __cs+'删除兑换'}, priority=4, block=True)
myb_exchange_info.__help_name__ = "删除兑换"
myb_exchange_info.__help_info__ = "删除已经配置的米游社兑换计划"