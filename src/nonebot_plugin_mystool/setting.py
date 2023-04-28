"""
### 用户设置相关
"""
from typing import List, Union

from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent, MessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, T_State

from .bbsAPI import GameInfo
from .config import config as conf
from .data import UserAccount, UserData
from .mybMission import GAME_ID
from .utils import COMMAND_BEGIN

setting = on_command(conf.COMMAND_START + '设置', priority=4)
setting.name = "设置"
setting.usage = f'如需配置是否开启每日任务、设备平台、频道任务等相关选项，请使用『{COMMAND_BEGIN}账号设置』命令。\n如需设置米游币任务和游戏签到后是否进行QQ通知，请使用『{COMMAND_BEGIN}通知设置』命令。'


@setting.handle()
async def _(event: MessageEvent):
    msg = f'如需配置是否开启每日任务、设备平台、频道任务等相关选项，请使用『{COMMAND_BEGIN}账号设置』命令\n如需设置米游币任务和游戏签到后是否进行QQ通知，请使用『{COMMAND_BEGIN}通知设置』命令'
    await setting.send(msg)


account_setting = on_command(conf.COMMAND_START + '账号设置', priority=5, block=True)
account_setting.name = "账号设置"
account_setting.usage = "配置游戏自动签到、米游币任务是否开启、设备平台、频道任务相关选项"


@account_setting.handle()
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent], matcher: Matcher, state: T_State):
    """
    账号设置命令触发
    """
    if isinstance(event, GroupMessageEvent):
        await account_setting.finish('⚠️为了保护您的隐私，请添加机器人好友后私聊进行设置操作')
    user_account = UserData.read_account_all(event.user_id)
    state['user_account'] = user_account
    if not user_account:
        await account_setting.finish(f"⚠️你尚未绑定米游社账户，请先使用『{conf.COMMAND_START}登录』进行登录")
    if len(user_account) == 1:
        matcher.set_arg('phone', Message(str(user_account[0].phone)))
    else:
        phones = [str(user_account[i].phone) for i in range(len(user_account))]
        msg = "您有多个账号，您要更改以下哪个账号的设置？\n"
        msg += "📱" + "\n📱".join(phones)
        msg += "\n🚪发送“退出”即可退出"
        await matcher.send(msg)


@account_setting.got('phone')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, phone=Arg('phone')):
    """
    根据手机号设置相应的账户
    """
    if isinstance(phone, Message):
        phone = phone.extract_plain_text().strip()
    if phone == '退出':
        await matcher.finish('🚪已成功退出')
    user_account: List[UserAccount] = state['user_account']
    phones = [str(user_account[i].phone) for i in range(len(user_account))]
    account = None
    if phone in phones:
        account = UserData.read_account(event.user_id, int(phone))
    else:
        await matcher.reject('⚠️您输入的账号不在以上账号内，请重新输入')
    state['account'] = account
    state["prepare_to_delete"] = False
    user_setting = ""
    user_setting += f"1️⃣ 米游币任务自动执行：{'开' if account.mybMission else '关'}\n"
    user_setting += f"2️⃣ 游戏自动签到：{'开' if account.gameSign else '关'}\n"
    platform_show = "iOS" if account.platform == "ios" else "安卓"
    user_setting += f"3️⃣ 设备平台：{platform_show}\n"

    # 筛选出用户数据中的missionGame对应的游戏全称
    user_setting += "4️⃣ 执行米游币任务的频道：『" + \
                    "、".join([game_tuple[1] for game_tuple in list(filter(
                        lambda game_tuple: game_tuple[0] in account.missionGame,
                        GameInfo.ABBR_TO_ID.values()))]) + "』\n"
    user_setting += f"5️⃣ 原神树脂恢复提醒：{'开' if account.checkResin else '关'}\n"
    user_setting += "⚠️6⃣️ 删除账户数据"

    await account_setting.send(user_setting + '\n您要更改哪一项呢？请发送 1 / 2 / 3 / 4 / 5 / 6\n🚪发送“退出”即可退出')


@account_setting.got('arg')
async def _(event: PrivateMessageEvent, state: T_State, arg=ArgPlainText('arg')):
    """
    根据所选更改相应账户的相应设置
    """
    arg = arg.strip()
    account: UserAccount = state['account']
    if arg == '退出':
        await account_setting.finish('🚪已成功退出')
    elif arg == '1':
        account.mybMission = not account.mybMission
        UserData.set_account(account, event.user_id, account.phone)
        await account_setting.finish(f"📅米游币任务自动执行已 {'✅开启' if account.mybMission else '❌关闭'}")
    elif arg == '2':
        account.gameSign = not account.gameSign
        UserData.set_account(account, event.user_id, account.phone)
        await account_setting.finish(f"📅米哈游游戏自动签到已 {'✅开启' if account.gameSign else '❌关闭'}")
    elif arg == '3':
        if account.platform == "ios":
            account.platform = "android"
            platform_show = "安卓"
        else:
            account.platform = "ios"
            platform_show = "iOS"
        UserData.set_account(account, event.user_id, account.phone)
        await account_setting.finish(f"📲设备平台已更改为 {platform_show}")
    elif arg == '4':
        games_show = "、".join([name_tuple[1]
                               for name_tuple in list(
                filter(lambda name_tuple: name_tuple[0] in GAME_ID,
                       GameInfo.ABBR_TO_ID.values())
            )
                               ])
        await account_setting.send(
            "请发送你想要执行米游币任务的频道：\n"
            "❕多个频道请用空格分隔，如 “原神 崩坏3 大别野”\n"
            f"可选的频道『{games_show}』\n"
            "🚪发送“退出”即可退出"
        )
    elif arg == '5':
        account.checkResin = not account.checkResin
        UserData.set_account(account, event.user_id, account.phone)
        await account_setting.finish(f"📅原神树脂恢复提醒已 {'✅开启' if account.checkResin else '❌关闭'}")
    elif arg == '6':
        state["prepare_to_delete"] = True
        await account_setting.reject(f"⚠️确认删除账号 {account.phone} ？发送 \"确认删除\" 以确定。")

    elif arg == '确认删除' and state["prepare_to_delete"]:
        del_result = UserData.del_account(event.user_id, account.phone)
        if del_result:
            await account_setting.finish(f"已删除账号 {account.phone} 的数据")
        else:
            await account_setting.finish(f"删除账号 {account.phone} 的数据失败")
    else:
        await account_setting.reject("⚠️您的输入有误，请重新输入")


@account_setting.got('missionGame')
async def _(event: PrivateMessageEvent, state: T_State, arg=ArgPlainText('missionGame')):
    arg = arg.strip()
    if arg == '退出':
        await account_setting.finish('🚪已成功退出')
    account: UserAccount = state['account']
    games_input = arg.split()
    for game in arg.split():
        if game not in [name_tuple[1]
                        for name_tuple in GameInfo.ABBR_TO_ID.values()]:
            await account_setting.reject("⚠️您的输入有误，请重新输入")

    # 查找输入的内容是否有不在游戏(频道)列表里的
    incorrect = list(filter(lambda game: game not in [name_tuple[1]
                                                      for name_tuple in GameInfo.ABBR_TO_ID.values()], games_input))
    if incorrect:
        await account_setting.reject("⚠️您的输入有误，请重新输入")
    else:
        account.missionGame = []

        # 查找输入的每个游戏全名的对应缩写
        for game_input in games_input:
            account.missionGame.append(list(filter(
                lambda game_tuple: game_tuple[1] == game_input, GameInfo.ABBR_TO_ID.values()))[0][0])
    UserData.set_account(account, event.user_id, account.phone)
    arg = arg.replace(" ", "、")
    await account_setting.finish(f"💬执行米游币任务的频道已更改为『{arg}』")


global_setting = on_command(conf.COMMAND_START + '通知设置', priority=5, block=True)
global_setting.name = "通知设置"
global_setting.usage = "设置每日签到后是否进行QQ通知"


@global_setting.handle()
async def _(event: MessageEvent, matcher: Matcher):
    """
    通知设置命令触发
    """
    await matcher.send(
        f"自动通知每日计划任务结果：{'🔔开' if UserData.is_notice(event.user_id) else '🔕关'}\n请问您是否需要更改呢？\n请回复“是”或“否”\n🚪发送“退出”即可退出")


@global_setting.got('choice')
async def _(event: PrivateMessageEvent, matcher: Matcher, choice: Message = ArgPlainText('choice')):
    """
    根据选择变更通知设置
    """
    if choice == '退出':
        await matcher.finish("🚪已成功退出")
    elif choice == '是':
        UserData.set_notice(not UserData.is_notice(event.user_id), event.user_id)
        await matcher.finish(f"自动通知每日计划任务结果 已 {'🔔开启' if UserData.is_notice(event.user_id) else '🔕关闭'}")
    elif choice == '否':
        await matcher.finish("没有做修改哦~")
    else:
        await matcher.reject("⚠️您的输入有误，请重新输入")
