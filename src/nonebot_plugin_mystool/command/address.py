import asyncio
from typing import Union

from nonebot import on_command
from nonebot.internal.params import ArgStr
from nonebot.matcher import Matcher
from nonebot.params import T_State

from ..api.common import get_address
from ..command.common import CommandRegistry
from ..model import CommandUsage
from ..model import PluginDataManager, plugin_config, UserAccount
from ..utils import COMMAND_BEGIN, GeneralMessageEvent, GeneralPrivateMessageEvent, \
    GeneralGroupMessageEvent

__all__ = [
    "address_matcher"
]

address_matcher = on_command(plugin_config.preference.command_start + '地址', priority=4, block=True)

CommandRegistry.set_usage(
    address_matcher,
    CommandUsage(
        name="地址",
        description="跟随指引，获取地址ID，用于兑换米游币商品。在获取地址ID前，如果你还没有设置米游社收获地址，请前往官网或App设置"
    )
)


@address_matcher.handle()
async def _(event: Union[GeneralMessageEvent], matcher: Matcher, state: T_State):
    if isinstance(event, GeneralGroupMessageEvent):
        await address_matcher.finish("⚠️为了保护您的隐私，请私聊进行地址设置。")
    user = PluginDataManager.plugin_data.users.get(event.get_user_id())
    user_account = user.accounts if user else None
    if not user_account:
        await address_matcher.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    else:
        await address_matcher.send(
            "请跟随指引设置收货地址ID，如果你还没有设置米游社收获地址，请前往官网或App设置。\n🚪过程中发送“退出”即可退出")
    if len(user_account) == 1:
        account = next(iter(user_account.values()))
        state["bbs_uid"] = account.bbs_uid
    else:
        msg = "您有多个账号，您要设置以下哪个账号的收货地址？\n"
        msg += "\n".join(map(lambda x: f"🆔{x}", user_account))
        await matcher.send(msg)


@address_matcher.got('bbs_uid')
async def _(event: Union[GeneralPrivateMessageEvent], state: T_State, bbs_uid=ArgStr()):
    if bbs_uid == '退出':
        await address_matcher.finish('🚪已成功退出')

    user_account = PluginDataManager.plugin_data.users[event.get_user_id()].accounts
    if bbs_uid not in user_account:
        await address_matcher.reject('⚠️您发送的账号不在以上账号内，请重新发送')
    account = user_account[bbs_uid]
    state['account'] = account

    address_status, address_list = await get_address(account)
    state['address_list'] = address_list
    if not address_status:
        if address_status.login_expired:
            await address_matcher.finish(f"⚠️账户 {account.display_name} 登录失效，请重新登录")
        await address_matcher.finish("⚠️获取失败，请稍后重新尝试")

    if address_list:
        address_text = map(
            lambda x: f"省 ➢ {x.province_name}\n"
                      f"市 ➢ {x.city_name}\n"
                      f"区/县 ➢ {x.county_name}\n"
                      f"详细地址 ➢ {x.addr_ext}\n"
                      f"联系电话 ➢ {x.phone}\n"
                      f"联系人 ➢ {x.connect_name}\n"
                      f"地址ID ➢ {x.id}",
            address_list
        )
        msg = "以下为查询结果：" \
              "\n\n" + "\n- - -\n".join(address_text)
        await address_matcher.send(msg)
        await asyncio.sleep(0.2)
    else:
        await address_matcher.finish("⚠️您还没有配置地址，请先前往米游社配置地址！")


@address_matcher.got('address_id', prompt='请发送你要选择的地址ID')
async def _(_: Union[GeneralPrivateMessageEvent], state: T_State, address_id=ArgStr()):
    if address_id == "退出":
        await address_matcher.finish("🚪已成功退出")

    address_filter = filter(lambda x: x.id == address_id, state['address_list'])
    address = next(address_filter, None)
    if address is not None:
        account: UserAccount = state["account"]
        account.address = address
        PluginDataManager.write_plugin_data()
        await address_matcher.finish(f"🎉已成功设置账户 {account.display_name} 的地址")
    else:
        await address_matcher.reject("⚠️您发送的地址ID与查询结果不匹配，请重新发送")
