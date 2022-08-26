"""
### 米游社收货地址相关前端
"""
import asyncio
import datetime

from nonebot import get_bot, get_driver, on_command
from nonebot.adapters.onebot.v11 import (Bot, MessageEvent, MessageSegment,
                                         PrivateMessageEvent)
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, CommandArg, T_State
from nonebot_plugin_apscheduler import scheduler

from .config import mysTool_config as conf
from .data import UserData
from .exchange import *
from .gameSign import GameInfo

driver = get_driver()

command = list(get_driver().config.command_start)[0] + conf.COMMAND_START

myb_exchange_plan = on_command(
    conf.COMMAND_START+'myb_exchange_plan', aliases={conf.COMMAND_START+'myb_exchange', conf.COMMAND_START+'米游币兑换', conf.COMMAND_START+'米游币兑换计划', conf.COMMAND_START+'兑换计划', conf.COMMAND_START+'兑换'}, priority=4, block=True)
myb_exchange_plan.__help_name__ = "兑换"
myb_exchange_plan.__help_info__ = "跟随指引，配置米游币兑换计划，即可自动兑换米游社商品。在兑换商品前，请先调用商品列表命令查看您想兑换的商品的ID。换取实体商品前，必须要先配置地址id；兑换虚拟商品时，请跟随引导输入要兑换的账户的uid"
myb_exchange_plan.__help_msg__ = f"""\
    具体用法：\
    \n{command} + [商品id] -> 新增兑换计划\
    \n{command} - [商品id] -> 删除兑换计划\
    \n{command} 商品列表 -> 查看米游社商品
""".strip()


@myb_exchange_plan.handle()
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, args=CommandArg()):
    if args:
        matcher.set_arg("content", args)
    qq_account = int(event.user_id)
    user_account = UserData.read_account_all(qq_account)
    state['qq_account'] = qq_account
    state['user_account'] = user_account
    if not user_account:
        await myb_exchange_plan.finish("你没有配置cookie，请先配置cookie！")
    if len(user_account) == 1:
        matcher.set_arg('phone', user_account[0].phone)
    else:
        phones = [str(user_account[i].phone) for i in range(len(user_account))]
        await matcher.send(f"您有多个账号，您要配置以下哪个账号的兑换计划？\n{'，'.join(phones)}")


@myb_exchange_plan.got('phone')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, phone: Message = ArgPlainText('phone')):
    if phone == '退出':
        await matcher.finish('已成功退出')
    user_account = state['user_account']
    qq = event.user_id
    phones = [str(user_account[i].phone) for i in range(len(user_account))]
    if phone in phones:
        account = UserData.read_account(qq, int(phone))
    else:
        myb_exchange_plan.reject('您输入的账号不在以上账号内，请重新输入')
    state['phone'] = int(phone)
    state['account'] = account
    if not matcher.get_arg('content'):
        state['account'] = account
        exchange_list = account.exchange
        msg = ''
        if exchange_list:
            for exchange_plan in exchange_list:
                good = await get_good_detail(exchange_plan[0])
                msg += f"-商品名：{good.name}\n-商品id：{good.goodID}\n-商品价格：{good.price}\n-兑换时间：{good.time}\n{'-兑换账号{}'.format(exchange_plan[1]) if exchange_plan[1] else ''}\n"
            msg += '\n'
        else:
            msg = '您还没有兑换计划哦~\n\n'
        await matcher.finish(msg+myb_exchange_plan.__help_msg__)


@myb_exchange_plan.got('content')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, bot: Bot):
    content = matcher.get_arg('content').extract_plain_text()
    account = state['account']
    arg = content.strip().split()
    phone = state['phone']
    good_dict = {
        'bh3': await get_good_list('bh3'),
        'ys': await get_good_list('ys'),
        'bh2': await get_good_list('bh2'),
        'wd': await get_good_list('wd'),
        'bbs': await get_good_list('bbs')
    }
    Flag = True
    break_flag = False
    for game, good_list in good_dict.items():
        for good in good_list:
            if good.goodID == arg[1]:
                Flag = False
                break_flag = True
                break
        if break_flag:
            break
    if Flag:
        await matcher.finish('您输入的商品id不在可兑换的商品列表内，程序已退出')
    if arg[0] == '+':
        if good.time:
            if good.isVisual:
                state['good'] = good
                game_records = await get_game_record(account)
                await matcher.send("您兑换的是虚拟物品哦，请输入对应账户的uid")
                send_flag = False
                if isinstance(game_records, int):
                    pass
                else:
                    for record in game_records:
                        if GameInfo.ABBR_TO_ID[record.gameID][0] == game:
                            if not send_flag:
                                send_flag = True
                                await matcher.send(f'有以下{GameInfo.ABBR_TO_ID[record.gameID][1]}账号供您参考（当然也可以您不选择这些uid）：')
                            await matcher.send(f'{record.regionName}-{record.nickname}-{record.uid}')
            else:
                matcher.get_arg('uid', None)
        else:
            await matcher.finish(f'该商品暂时不可以兑换，请重新设置')
    elif arg[0] == '-':
        if account.exchange:
            for exchange_good in account.exchange:
                if exchange_good[0] == good.goodID:
                    account.exchange.remove(exchange_good)
                    UserData.set_account(account, event.user_id, phone)
                    scheduler.remove_job(job_id=str(
                        account.phone)+'_'+good.goodID)
                    await matcher.finish('兑换计划删除成功')
            await matcher.finish(f"您没有设置商品ID为{good.goodID}的兑换哦")
        else:
            await matcher.finish("您还没有配置兑换计划哦")
    else:
        matcher.finish('您的输入有误，请重新输入')


@myb_exchange_plan.got('uid')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, bot: Bot, uid=ArgPlainText()):
    account = state['account']
    if not uid:
        if not account.address:
            await matcher.finish('您还没有配置地址哦，请先配置地址')
    good = state['good']
    phone = state['phone']
    qq = event.user_id
    for exchange_plan in account.exchange:
        if exchange_plan[0] == good.goodID:
            await matcher.send('您已经配置过该商品的兑换哦！此次配置将会覆盖原来的记录')
            account.exchange.remove(exchange_plan)
    account.exchange.append((good.goodID, uid))
    UserData.set_account(account, event.user_id, phone)
    exchange_plan = await Exchange(account, good.goodID, uid).async_init()
    if exchange_plan.result == -1:
        await matcher.finish(f"账户{account.phone}登录失效，请重新登录")
    elif exchange_plan.result == -2:
        await matcher.finish("商品 {} 为游戏内物品，由于未配置stoken，放弃兑换".format(good.goodID))
    elif exchange_plan.result == -3:
        await matcher.finish("商品 {} 为游戏内物品，由于stoken为\"v2\"类型，且未配置mid，放弃兑换".format(good.goodID))
    elif exchange_plan.result == -4:
        await matcher.finish("暂不支持商品 {} 所属的游戏，放弃兑换".format(good.goodID))
    elif exchange_plan.result == -5:
        await matcher.finish("获取商品 {} 的信息时，网络连接失败或服务器返回不正确，放弃兑换".format(good.goodID))
    elif exchange_plan.result == -6:
        await matcher.finish("获取商品 {} 的信息时，获取用户游戏账户数据失败，放弃兑换".format(good.goodID))
    else:
        scheduler.add_job(id=str(account.phone)+'_'+good.goodID, replace_existing=True, trigger='date', func=exchange,
                          args=(exchange_plan, qq), next_run_time=datetime.datetime.strptime(good.time, "%Y-%m-%d %H:%M:%S"))
    await matcher.finish(f'设置兑换计划成功！将于{good.time}开始兑换，兑换结果会实时通知您')


async def exchange(exchange_plan: Exchange, qq: str):
    bot = get_bot()
    for i in range(5):
        results = []
        flag = False
        results.append(exchange_plan.start())
        await asyncio.sleep(0.1)
    for result in results:
        if result[0]:
            flag = True
            break
    if flag:
        await bot.send_private_msg(user_id=qq, message=f"商品{exchange_plan.goodID}兑换成功，可前往米游社查看")
    else:
        await bot.send_private_msg(user_id=qq, message=f"商品{exchange_plan.goodID}兑换失败\n{result[1]}")
    for exchange_plan__ in exchange_plan.account.exchange:
        if exchange_plan__[0] == exchange_plan.goodID:
            exchange_plan.account.exchange.remove(exchange_plan__)
    UserData.set_account(exchange_plan.account, qq,
                         exchange_plan.account.phone)


get_good_image = on_command(
    conf.COMMAND_START+'商品列表', aliases={conf.COMMAND_START+'商品图片', conf.COMMAND_START+'米游社商品列表', conf.COMMAND_START+'米游币商品图片'}, priority=4, block=True)
get_good_image.__help_name__ = "商品列表"
get_good_image.__help_info__ = "获取当日米游社商品信息，目前共有五个分类可选，分别为（崩坏3，原神，崩坏2，未定事件簿，大别野）。请记住您要兑换的商品的ID，以方便下一步兑换"


@get_good_image.handle()
async def _(event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    if arg:
        matcher.set_arg("content", arg)


@get_good_image.got("content", prompt='请发送您要查看的商品类别:\n- 崩坏3\n- 原神\n- 崩坏2\n- 未定事件簿\n- 大别野\n—— 发送“退出”以结束')
async def _(event: MessageEvent, matcher: Matcher, arg: Message = ArgPlainText('content')):
    if arg in ['原神', 'ys']:
        arg = ('ys', '原神')
    elif arg in ['崩坏3', '崩坏三', '崩3', '崩三', '崩崩崩', '蹦蹦蹦', 'bh3']:
        arg = ('bh3', '崩坏3')
    elif arg in ['崩坏2', '崩坏二', '崩2', '崩二', '崩崩', '蹦蹦', 'bh2']:
        arg = ('bh2', '崩坏2')
    elif arg in ['未定', '未定事件簿', 'wd']:
        arg = ('wd', '未定事件簿')
    elif arg in ['大别野', '米游社']:
        arg = ('bbs', '米游社')
    else:
        await get_good_image.finish('您的输入有误，请重新输入')
    good_list = await get_good_list(arg[0])
    if good_list:
        img_path = time.strftime(
            f'file:///{conf.goodListImage.SAVE_PATH}/%m-%d-{arg[0]}.jpg', time.localtime())
        await get_good_image.finish(MessageSegment.image(img_path))
    else:
        await get_good_image.finish(f"{arg[1]}部分目前没有可兑换商品哦~")


@driver.on_startup
async def load_exchange_data():
    all_accounts = UserData.read_all()
    for qq in all_accounts.keys():
        accounts = UserData.read_account_all(qq)
        for account in accounts:
            exchange_list = account.exchange
            for exchange_good in exchange_list:
                good_detail = await get_good_detail(exchange_good[0])
                exchange_plan = await Exchange(account, exchange_good[0], exchange_good[1]).async_init()
                scheduler.add_job(id=str(account.phone)+'_'+exchange_good[0], replace_existing=True, trigger='date', func=exchange, args=(
                    exchange_plan, qq), next_run_time=datetime.datetime.strptime(good_detail.time, "%Y-%m-%d %H:%M:%S"))
