"""
### 米游社收货地址相关前端
"""
import asyncio
import datetime
from nonebot import on_command, get_driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Arg, ArgPlainText, T_State
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent, MessageEvent, MessageSegment
from nonebot.adapters.onebot.v11.message import Message
from nonebot_plugin_apscheduler import scheduler
from .config import mysTool_config as conf
from .config import img_config as img_conf
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
    if args:
        matcher.set_arg("content", args)
    else:
        state['account'] = account
        goodid_list = account.exchange
        msg = ''
        if goodid_list:
            for goodid in goodid_list:
                msg = ... # data内查看兑换计划函数
        else:
            msg = '您还没有兑换计划哦\n\n'
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
            account.exchange.append(good.goodID)
            exchange_plan = Exchange(account, good.goodID)
            if exchange_plan.result == -1:
                await matcher.finish("米商品 {} 为游戏内物品，由于未配置stoken，放弃兑换".format(good.goodID))
            elif exchange_plan.result == -2:
                await matcher.finish("商品 {} 为游戏内物品，由于stoken为\"v2\"类型，且未配置mid，放弃兑换".format(good.goodID))
            elif exchange_plan.result == -3:
                await matcher.finish("暂不支持商品 {} 所属的游戏".format(good.goodID))
            elif exchange_plan.result == -4:
                await matcher.finish("获取商品 {} 的信息时，服务器没有正确返回".format(good.goodID))
            else:
                scheduler.add_job(id=account.phone+good.goodID, replace_existing=True, trigger='date', func=exchange, args=(exchange_plan, bot, qq),next_run_time=datetime.datetime.strptime(good.time, "%Y-%m-%d %H:%M:%S"))
            await matcher.finish(f'设置兑换计划成功！将于{good.time}开始兑换，兑换结果会实时通知您')
        else:
            await matcher.finish(f'该商品暂时不可以兑换，请重新设置')
    elif arg[0] == '-':
        ... # data删除兑换计划
        scheduler.remove_job(job_id=account.phone+good.goodID)
        await matcher.finish('兑换计划删除成功')
    else:
        matcher.finish('您的输入有误，请重新输入')

async def exchange(exchange_plan: Exchange, bot: Bot, qq: str):
    for i in range(3):
        results = []
        flag = False
        results.append(exchange_plan.start())
        await asyncio.sleep(0.2)
    for result in results:
        if result[0]:
            flag = True
            break
    if flag:
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
    
@get_good_image.got("content", prompt='请发送您要查看的商品类别:\n- 崩坏3\n- 原神\n- 崩坏2\n- 未定事件簿\n- 大别野\n—— 发送“退出”以结束')
async def _(event:MessageEvent, matcher: Matcher, arg: Message = ArgPlainText('content')):
    if arg in ['原神', 'ys']:
        arg = 'ys'
    elif arg in ['崩坏3', '崩坏三', '崩3', '崩三', '崩崩崩', '蹦蹦蹦', 'bh3']:
        arg = 'bh3'
    elif arg in ['崩坏2', '崩坏二', '崩2', '崩二', '崩崩', '蹦蹦', 'bh2']:
        arg = 'bh2'
    elif arg in ['未定', '未定事件簿', 'wd']:
        arg = 'wd'
    elif arg in ['大别野', '米游社']:
        arg = 'bbs'
    else:
        await get_good_image.finish('您的输入有误，请重新输入')
    img_path = time.strftime(f'file:///{img_conf.SAVE_PATH}/%m-%d-{arg}.jpg'.replace('\\', '/'),time.localtime())
    await get_good_image.finish(MessageSegment.image(img_path))