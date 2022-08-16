"""
### 米游社收货地址相关前端
"""
from nonebot import on_command, get_driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Arg, ArgPlainText, T_State
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent, MessageEvent, MessageSegment
from nonebot.adapters.onebot.v11.message import Message
from .config import mysTool_config as conf
from .data import UserData
from .exchange import *

__cs = ''
if conf.USE_COMMAND_START:
    __cs = conf.COMMAND_START
command = list(get_driver().config.command_start)[0] + __cs

myb_exchange_plan = on_command(
    __cs+'myb_exchange_plan', aliases={__cs+'myb_exchange', __cs+'米游币兑换', __cs+'米游币兑换计划', __cs+'兑换计划', __cs+'兑换'}, priority=4, block=True)
myb_exchange_plan.__help_name__ = "兑换"
myb_exchange_plan.__help_info__ = "跟随指引，配置米游币兑换计划，即可自动兑换米游社商品。在兑换商品前，请先调用商品列表命令查看您想兑换的商品的ID。换取实体商品前，必须要先配置地址id；兑换虚拟商品时，请跟随引导输入要兑换的账户的uid"
myb_exchange_plan.__help_msg__ = f"""\
    具体用法：\
    \n{command} + [商品id] -> 新增兑换计划\
    \n{command} - [商品id] -> 删除兑换计划\
    \n{command} 商品列表 -> 查看所有米游社商品
""".strip()

@myb_exchange_plan.handle()
async def handle_first_receive(event: PrivateMessageEvent, matcher: Matcher, state: T_State, args: Message = CommandArg()):
    qq = event.user_id
    accounts = UserData.read_account_all(qq)
    if accounts:
        if len(accounts) == 1:
            account = accounts[0]
        else:
            myb_exchange_plan.got('phone', prompt='您有多个账号，请输入您想兑换的账号的手机号')
            phone = ArgPlainText('phone')
            if phone == '退出':
                await matcher.finish('已成功退出')
            account = UserData.read_account(qq, phone)
            if not account:
                await matcher.reject('您输入的手机号有误，请重新输入')
    state['account'] = account
    msg = ... # data内查看兑换计划函数
    if args:
        matcher.set_arg("content", args)
    else:
        await matcher.finish(msg+matcher.__help_msg__)

@myb_exchange_plan.got('content')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, bot: Bot, content: Message = Arg()):
    account = state['T-state']
    qq = event.user_id
    arg = content.extract_plain_text().strip()
    good_list = get_good_list('bh3') + get_good_list('ys') + get_good_list('bh2') + get_good_list('wd') + get_good_list('bbs')
    Flag = True
    for good in good_list:
        if good.goodID == arg[1]:
            Flag = False
            break
    if Flag:
        await matcher.finish('您输入的商品id不在可兑换的商品列表内，程序已退出')
    if arg[0] == '+':
        if good.time:
            ... # 写入兑换计划
            exchange_plan = Exchange(account, good.goodID)
            if exchange_plan.result == -1:
                await bot.send_private_msg(user_id=qq, message="商品初始化失败，请重新尝试")
            else:
                ...
            await matcher.finish(f'设置兑换计划成功！将于{good.time}开始兑换，兑换结果会实时通知您')
        else:
            await matcher.finish(f'该商品暂时不可以兑换，请重新设置')
    elif arg[0] == '-':
        ... # data删除兑换计划
        ... # 删除兑换计划定时
        await matcher.finish('兑换计划删除成功')
    else:
        matcher.finish('您的输入有误，请重新输入')

async def exchange(exchange_plan: Exchange, bot: Bot, qq: str):
    result = exchange_plan.start()
    if result[0]:
        await bot.send_private_msg(user_id=qq, message=f"商品{exchange_plan.goodID}兑换成功，可前往米游社查看")
    else:
        await bot.send_private_msg(user_id=qq, message=f"商品{exchange_plan.goodID}兑换失败\n{result[1]}")




get_good_image = on_command(
    __cs+'商品列表', aliases={__cs+'商品图片', __cs+'米游社商品列表', __cs+'米游币商品图片'}, priority=4, block=True)
get_good_image.__help_name__ = "商品列表"
get_good_image.__help_info__ = "获取当日米游社商品信息，目前共有五个分类可选，分别为（崩坏3，原神，崩坏2，未定事件簿，大别野）。请记住您要兑换的商品的ID，以方便下一步兑换"
@get_good_image.handle()
async def _(event:MessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    if arg:
        matcher.set_arg("content", arg)
    
@get_good_image.got("content", prompt='请输入您要查看的商品类别（崩坏3，原神，崩坏2，未定事件簿，大别野），输入退出即可退出')
async def _(event:MessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    arg = arg.extract_plain_text()
    if arg == '原神':
        ...
    if arg in ['崩坏3', '崩坏三', '崩3', '崩三', '崩崩崩', '蹦蹦蹦']:
        ...
    if arg in ['崩坏2', '崩坏二', '崩2', '崩二', '崩崩', '蹦蹦']:
        ...
    if arg in ['未定', '未定事件簿']:
        ...
    if arg in ['大别野', '米游社']:
        ...
    await get_good_image.finish(MessageSegment.image(...)) #图片存储地址