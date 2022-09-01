import asyncio

from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, T_State

from .config import mysTool_config as conf
from .data import *
from .data import UserData

COMMAND = list(get_driver().config.command_start)[0] + conf.COMMAND_START

account_setting = on_command(
    conf.COMMAND_START+'游戏设置', aliases={conf.COMMAND_START+'账户设置', conf.COMMAND_START+'签到设置'}, priority=4, block=True)
account_setting.__help_name__ = "游戏设置"
account_setting.__help_info__ = "配置游戏自动签到、米游币任务是否开启相关选项"


@account_setting.handle()
async def handle_first_receive(event: PrivateMessageEvent, matcher: Matcher, state: T_State, arg = ArgPlainText('arg')):
    await account_setting.send(f"播报相关设置请调用 {COMMAND}播报设置 命令哦\n设置过程中随时输入“退出”即可退出")
    qq = int(event.user_id)
    user_account = UserData.read_account_all(qq)
    state['qq'] = qq
    state['user_account'] = user_account
    if not user_account:
        await account_setting.finish("⚠️你尚未绑定米游社账户，请先进行登录")
    if arg:
        matcher.set_arg('phone', arg)
        return
    if len(user_account) == 1:
        matcher.set_arg('phone', str(user_account[0].phone))
    else:
        phones = [str(user_account[i].phone) for i in range(len(user_account))]
        msg = "您有多个账号，您要配置以下哪个账号的兑换计划？\n"
        msg += "📱" + "\n📱".join(phones)
        await matcher.send(msg)


@account_setting.got('phone')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, phone = Arg()):
    if isinstance(phone, Message):
        phone = phone.extract_plain_text().strip()
    if phone == '退出':
        await matcher.finish('已成功退出')
    user_account: List[UserAccount] = state['user_account']
    qq = state['qq']
    phones = [str(user_account[i].phone) for i in range(len(user_account))]
    if phone in phones:
        account = UserData.read_account(qq, int(phone))
    else:
        await matcher.reject('⚠️您输入的账号不在以上账号内，请重新输入')
    state['phone'] = phone
    state['account'] = account
    user_setting = f"1.米游币任务自动执行：{'开' if account.mybMission else '关'}\n2.游戏自动签到：{'开' if account.gameSign else '关'}\n"
    await account_setting.send(user_setting+'您要更改哪一项呢？请输入“1”或“2”')


@account_setting.got('arg')
async def _(event: PrivateMessageEvent, state: T_State, arg = ArgPlainText('arg')):
    account: UserAccount = state['account']
    if arg == '退出':
        await account_setting.finish('已成功退出')
    elif arg == '1':
        account.mybMission = not account.mybMission
        UserData.set_account(account, event.user_id, int(state['phone']))
        await account_setting.send(f"米游币任务自动执行已{'开启' if account.mybMission else '关闭'}")
    elif arg == '2':
        account.gameSign = not account.gameSign
        UserData.set_account(account, event.user_id, state['phone'])
        await account_setting.send(f"米哈游游戏自动签到已{'开启' if account.gameSign else '关闭'}")
    else:
        await account_setting.reject("⚠️您的输入有误，请重新输入")


global_setting = on_command(
    conf.COMMAND_START+'global_setting', aliases={conf.COMMAND_START+'全局设置', conf.COMMAND_START+'播报设置'}, priority=4, block=True)
global_setting.__help_name__ = "播报设置"
global_setting.__help_info__ = "设置每日签到后是否进行qq通知"


@global_setting.handle()
async def _(event: PrivateMessageEvent, matcher: Matcher):
    qq = int(event.user_id)
    await matcher.send(f"每日自动签到相关设置请调用 {COMMAND}签到设置 命令哦\n输入“退出”即可退出")
    await asyncio.sleep(0.5)
    await matcher.send(f"每日签到后自动播报功能：{'开' if UserData.isNotice(qq) else '关'}\n请问您是否需要更改呢？\n请回复“是”或“否”")


@global_setting.got('choice')
async def _(event: PrivateMessageEvent, matcher: Matcher, choice: Message = ArgPlainText('choice')):
    qq = int(event.user_id)
    if choice == '退出':
        await matcher.finish("已成功退出")
    elif choice == '是':
        a = UserData.set_notice(not UserData.isNotice(qq), qq)
        await matcher.finish(f"每日签到后自动播报功能已{'开启' if UserData.isNotice(qq) else '关闭'}")
    elif choice == '否':
        await matcher.finish("没有做修改哦~")
    else:
        await matcher.reject("⚠️您的输入有误，请重新输入")

setting = on_command(
    conf.COMMAND_START+'setting', aliases={conf.COMMAND_START+'设置'}, priority=4, block=True)
setting.__help_name__ = "设置"
setting.__help_info__ = f'如需配置游戏自动签到、米游币任务是否开启相关选项，请调用『{COMMAND}游戏设置』命令。\n如需设置每日签到后是否进行qq通知，请调用『{COMMAND}播报设置』命令。'

@setting.handle()
async def _(event: PrivateMessageEvent):
    msg = f'如需配置游戏自动签到、米游币任务是否开启相关选项，请调用『{COMMAND}游戏设置』命令\n如需设置每日签到后是否进行qq通知，请调用『{COMMAND}播报设置』命令'
    await setting.send(msg)
