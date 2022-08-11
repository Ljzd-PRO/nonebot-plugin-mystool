from nonebot import on_command
from nonebot.params import T_State, ArgPlainText
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from .data import UserData
import asyncio

setting = on_command(
    'setting', aliases={'设置', '签到设置', '播报配置'}, priority=4, block=True)
setting.__help__ = {
    "usage":     "setting",
    "introduce": "配置签到、播报相关选项"
}

@setting.handle()
async def handle_first_receive(event: PrivateMessageEvent, state: T_State):
    state['qq_account'] = event.user_id
    await setting.send('配置您的签到选项请发送1，播报选项请发送2，输入退出即可退出')

@setting.got('choice')
async def _(event: PrivateMessageEvent, state: T_State, choice: str = ArgPlainText('choice')):
    accounts = UserData.read_account_all(state['qq_acount'])
    if len(accounts) == 0:
        setting.finish('请先配置账号')
    elif len(accounts) == 1:
        account = accounts[0]
    else:
        phone = setting.got('phone', prompt='您有多个账号，请输入您要配置的账号')
        try:
            account = UserData.read_account(state['qq_account'], phone)
        except:
            setting.finish('您输入的账号未配置过，程序已退出')
    if choice == '退出':
        setting.finish('已成功退出')
    elif choice == '1':
        change = await setting.got(f"您现在的每日签到已{'开启' if account.gameSign else '关闭'}，输入“是”进行更改，输入“否”退出")
        if change == '是':
            account.gameSign = not account.gameSign
            setting.finish(f"每日签到计划已{'开启' if account.gameSign else '关闭'}")
        else:
            setting.finish('配置未进行更改')
    elif choice == '2':
        change = await setting.got(f"您现在的每日签到播报已{'开启' if account.notice else '关闭'}，输入“是”进行更改，输入“否”退出")
        if change == '是':
            account.notice = not account.notice
            setting.finish(f"每日签到播报已{'开启' if account.notice else '关闭'}")
        else:
            setting.finish('配置未进行更改')