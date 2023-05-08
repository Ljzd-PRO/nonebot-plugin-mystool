"""
### 米游社收货地址相关
"""
import asyncio
from typing import Union, Dict

from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, T_State

from .api import get_address
from .config import config as conf
from .plugin_data import plugin_data_obj as plugin_data, write_plugin_data
from .user_data import UserAccount
from .utils import COMMAND_BEGIN

address_matcher = on_command(conf.COMMAND_START + '地址', priority=4, block=True)

address_matcher.name = '地址'
address_matcher.usage = '跟随指引，获取地址ID，用于兑换米游币商品。在获取地址ID前，如果你还没有设置米游社收获地址，请前往官网或App设置'


@address_matcher.handle()
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent], matcher: Matcher, state: T_State):
    if isinstance(event, GroupMessageEvent):
        await address_matcher.finish("⚠️为了保护您的隐私，请添加机器人好友后私聊进行地址设置。")
    user_data = plugin_data.users[event.user_id]
    user_account = user_data.accounts
    state['user_account'] = user_account
    if not user_account:
        await address_matcher.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    else:
        await address_matcher.send(
            "请跟随指引设置收货地址ID，如果你还没有设置米游社收获地址，请前往官网或App设置。\n🚪过程中发送“退出”即可退出")
    if len(user_account) == 1:
        matcher.set_arg('phone', Message(str(next(user_account.values()).phone_number)))
    else:
        phones = map(lambda x: str(x.phone_number), user_account.values())
        msg = "您有多个账号，您要设置以下哪个账号的收货地址？\n"
        msg += "📱" + "\n📱".join(phones)
        await matcher.send(msg)


@address_matcher.got('phone')
async def _(_: PrivateMessageEvent, state: T_State, phone=Arg()):
    if isinstance(phone, Message):
        phone = phone.extract_plain_text().strip()
    if phone == '退出':
        await address_matcher.finish('🚪已成功退出')

    user_account: Dict[str, UserAccount] = state['user_account']
    account_filter = filter(lambda x: str(x.phone_number) == phone, user_account.values())
    account = next(account_filter, None)
    if account is None:
        await address_matcher.reject('⚠️您发送的账号不在以上账号内，请重新发送')
    state['account'] = account

    address_status, address_list = await get_address(account)
    state['address_list'] = address_list
    if not address_status:
        if address_status.login_expired:
            await address_matcher.finish(f"⚠️账户 {account.bbs_uid} 登录失效，请重新登录")
        await address_matcher.finish("⚠️获取失败，请稍后重新尝试")

    if address_list:
        await address_matcher.send("以下为查询结果：")
        for address in address_list:
            address_string = f"""\
            \n省 ➢ {address.province_name}\
            \n市 ➢ {address.city_name}\
            \n区/县 ➢ {address.county_name}\
            \n详细地址 ➢ {address.addr_ext}\
            \n联系电话 ➢ {address.phone}\
            \n联系人 ➢ {address.connect_name}\
            \n地址ID ➢ {address.id}\
            """.strip()
            await address_matcher.send(address_string)
            await asyncio.sleep(0.2)
    else:
        await address_matcher.finish("⚠️您还没有配置地址，请先前往米游社配置地址！")


@address_matcher.got('address_id', prompt='请发送你要选择的地址ID')
async def _(_: PrivateMessageEvent, state: T_State, address_id=ArgPlainText()):
    if address_id == "退出":
        await address_matcher.finish("🚪已成功退出")

    address_filter = filter(lambda x: x.address_id == address_id, state['address_list'])
    address = next(address_filter, None)
    if address is not None:
        account: UserAccount = state["account"]
        account.address = address
        write_plugin_data()
        await address_matcher.finish(f"🎉已成功设置账户 {account.bbs_uid} 的地址")
    else:
        await address_matcher.reject("⚠️您发送的地址ID与查询结果不匹配，请重新发送")
