"""
### 用户设置相关
"""
from typing import List, Union, Dict

from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent, MessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, T_State

from .base_api import GameInfo, get_game_list
from .plugin_data import plugin_data_obj as plugin_data, write_plugin_data
from .user_data import UserAccount
from .utils import COMMAND_BEGIN

setting = on_command(plugin_data.preference.command_start + '设置', priority=4, block=True)
setting.name = "设置"
setting.usage = f'如需配置是否开启每日任务、设备平台、频道任务等相关选项，请使用『{COMMAND_BEGIN}账号设置』命令。\n如需设置米游币任务和游戏签到后是否进行QQ通知，请使用『{COMMAND_BEGIN}通知设置』命令。'


@setting.handle()
async def _(_: MessageEvent):
    msg = f'如需配置是否开启每日任务、设备平台、频道任务等相关选项，请使用『{COMMAND_BEGIN}账号设置』命令\n如需设置米游币任务和游戏签到后是否进行QQ通知，请使用『{COMMAND_BEGIN}通知设置』命令'
    await setting.send(msg)


account_setting = on_command(plugin_data.preference.command_start + '账号设置', priority=5, block=True)
account_setting.name = "账号设置"
account_setting.usage = "配置游戏自动签到、米游币任务是否开启、设备平台、频道任务相关选项"


@account_setting.handle()
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent], matcher: Matcher, state: T_State):
    """
    账号设置命令触发
    """
    if isinstance(event, GroupMessageEvent):
        await account_setting.finish('⚠️为了保护您的隐私，请添加机器人好友后私聊进行设置操作')
    user = plugin_data.users.get(event.user_id)
    user_account = user.accounts if user else None
    state['user_account'] = user_account
    if not user_account:
        await account_setting.finish(
            f"⚠️你尚未绑定米游社账户，请先使用『{plugin_data.preference.command_start}登录』进行登录")
    if len(user_account) == 1:
        matcher.set_arg('phone', Message(str(next(user_account.values()).phone_number)))
    else:
        phones = map(lambda x: str(x.phone_number), user_account.values())
        msg = "您有多个账号，您要更改以下哪个账号的设置？\n"
        msg += "📱" + "\n📱".join(phones)
        msg += "\n🚪发送“退出”即可退出"
        await matcher.send(msg)


@account_setting.got('phone')
async def _(_: PrivateMessageEvent, matcher: Matcher, state: T_State, phone=Arg('phone')):
    """
    根据手机号设置相应的账户
    """
    if isinstance(phone, Message):
        phone = phone.extract_plain_text().strip()
    if phone == '退出':
        await matcher.finish('🚪已成功退出')

    user_account: Dict[str, UserAccount] = state['user_account']
    account_filter = filter(lambda x: str(x.phone_number) == phone, user_account.values())
    account = next(account_filter, None)
    if account is None:
        await account_setting.reject('⚠️您发送的账号不在以上账号内，请重新发送')
    state['account'] = account
    state["prepare_to_delete"] = False

    game_status, game_list = await get_game_list()
    state['game_list'] = game_list
    if not game_status:
        await account_setting.finish("⚠️获取游戏列表失败，请稍后再试")

    user_setting = ""
    user_setting += f"1️⃣ 米游币任务自动执行：{'开' if account.enable_mission else '关'}\n"
    user_setting += f"2️⃣ 游戏自动签到：{'开' if account.enable_mission else '关'}\n"
    platform_show = "iOS" if account.platform == "ios" else "安卓"
    user_setting += f"3️⃣ 设备平台：{platform_show}\n"

    # 筛选出用户数据中的missionGame对应的游戏全称
    user_setting += "4️⃣ 执行米游币任务的频道：『" + \
                    "、".join(map(lambda x: x.name, game_list)) + "』\n"
    user_setting += f"5️⃣ 原神树脂恢复提醒：{'开' if account.enable_resin else '关'}\n"
    user_setting += "⚠️6⃣️ 删除账户数据"

    await account_setting.send(user_setting + '\n您要更改哪一项呢？请发送 1 / 2 / 3 / 4 / 5 / 6\n🚪发送“退出”即可退出')


@account_setting.got('arg')
async def _(_: PrivateMessageEvent, state: T_State, arg=ArgPlainText('arg')):
    """
    根据所选更改相应账户的相应设置
    """
    arg = arg.strip()
    account: UserAccount = state['account']
    user_account: Dict[str, UserAccount] = state['user_account']
    if arg == '退出':
        await account_setting.finish('🚪已成功退出')
    elif arg == '1':
        account.enable_mission = not account.enable_mission
        write_plugin_data()
        await account_setting.finish(f"📅米游币任务自动执行已 {'✅开启' if account.enable_mission else '❌关闭'}")
    elif arg == '2':
        account.enable_game_sign = not account.enable_game_sign
        write_plugin_data()
        await account_setting.finish(f"📅米哈游游戏自动签到已 {'✅开启' if account.enable_game_sign else '❌关闭'}")
    elif arg == '3':
        if account.platform == "ios":
            account.platform = "android"
            platform_show = "安卓"
        else:
            account.platform = "ios"
            platform_show = "iOS"
        write_plugin_data()
        await account_setting.finish(f"📲设备平台已更改为 {platform_show}")
    elif arg == '4':
        game_list: List[GameInfo] = state['game_list']
        games_show = "、".join(map(lambda x: x.name, game_list))
        await account_setting.send(
            "请发送你想要执行米游币任务的频道：\n"
            "❕多个频道请用空格分隔，如 “原神 崩坏3 大别野”\n"
            f"可选的频道『{games_show}』\n"
            "🚪发送“退出”即可退出"
        )
    elif arg == '5':
        account.enable_resin = not account.enable_resin
        write_plugin_data()
        await account_setting.finish(f"📅原神树脂恢复提醒已 {'✅开启' if account.enable_resin else '❌关闭'}")
    elif arg == '6':
        state["prepare_to_delete"] = True
        await account_setting.reject(f"⚠️确认删除账号 {account.phone_number} ？发送 \"确认删除\" 以确定。")
    elif arg == '确认删除' and state["prepare_to_delete"]:
        user_account.pop(account.bbs_uid)
        await account_setting.finish(f"已删除账号 {account.phone_number} 的数据")
    else:
        await account_setting.reject("⚠️您的输入有误，请重新输入")


@account_setting.got('missionGame')
async def _(_: PrivateMessageEvent, state: T_State, arg=ArgPlainText('missionGame')):
    arg = arg.strip()
    if arg == '退出':
        await account_setting.finish('🚪已成功退出')
    account: UserAccount = state['account']
    game_list: List[GameInfo] = state['game_list']
    games_input = arg.split()
    mission_games = set()
    for game in games_input:
        game_filter = filter(lambda x: x.name == game, game_list)
        game_obj = next(game_filter, None)
        if game_obj is None:
            await account_setting.reject("⚠️您的输入有误，请重新输入")
        else:
            mission_games.add(game_obj)

    account.mission_games = mission_games
    write_plugin_data()
    arg = arg.replace(" ", "、")
    await account_setting.finish(f"💬执行米游币任务的频道已更改为『{arg}』")


global_setting = on_command(plugin_data.preference.command_start + '通知设置', priority=5, block=True)
global_setting.name = "通知设置"
global_setting.usage = "设置每日签到后是否进行QQ通知"


@global_setting.handle()
async def _(event: MessageEvent, matcher: Matcher):
    """
    通知设置命令触发
    """
    user = plugin_data.users[event.user_id]
    await matcher.send(
        f"自动通知每日计划任务结果：{'🔔开' if user.enable_notice else '🔕关'}\n请问您是否需要更改呢？\n请回复“是”或“否”\n🚪发送“退出”即可退出")


@global_setting.got('choice')
async def _(event: PrivateMessageEvent, matcher: Matcher, choice: Message = ArgPlainText('choice')):
    """
    根据选择变更通知设置
    """
    user = plugin_data.users[event.user_id]
    if choice == '退出':
        await matcher.finish("🚪已成功退出")
    elif choice == '是':
        user.enable_notice = not user.enable_notice
        await matcher.finish(f"自动通知每日计划任务结果 已 {'🔔开启' if user.enable_notice else '🔕关闭'}")
    elif choice == '否':
        await matcher.finish("没有做修改哦~")
    else:
        await matcher.reject("⚠️您的输入有误，请重新输入")
