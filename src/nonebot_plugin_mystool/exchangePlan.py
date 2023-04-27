"""
### 米游社商品兑换前端以及计划任务相关
"""
import asyncio
import io
import os
import time
from copy import deepcopy
from datetime import datetime
from typing import List, Set, Union

from nonebot import get_bot, on_command
from nonebot.adapters.onebot.v11 import (MessageEvent, MessageSegment,
                                         PrivateMessageEvent, GroupMessageEvent)
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, ArgPlainText, T_State, CommandArg, Command
from nonebot_plugin_apscheduler import scheduler

from .bbsAPI import get_game_record
from .config import config as conf
from .data import UserData
from .exchange import (Exchange, Good, UserAccount, get_good_detail,
                       get_good_list, game_list_to_image)
from .gameSign import GameInfo
from .utils import NtpTime, COMMAND_BEGIN, logger, driver, get_last_command_sep


class ExchangeStart:
    """
    异步多线程兑换
    """

    def __init__(self, account: UserAccount, qq: int, exchange_plan: Exchange, thread: int) -> None:
        self.plans: List[Exchange] = []
        self.tasks: Set[asyncio.Task] = set()
        self.finishedCount = 0
        self.account = account
        self.qq = qq

        for _ in range(thread):
            self.plans.append(deepcopy(exchange_plan))

    async def start(self):
        """
        执行兑换
        """
        # 在后台启动兑换操作
        for plan in self.plans:
            self.tasks.add(asyncio.create_task(plan.start()))
        # 等待兑换线程全部结束
        for task in self.tasks:
            await task

        bot = get_bot()

        success_tasks: List[asyncio.Task] = list(filter(lambda task: isinstance(
            task.result(), tuple) and task.result()[0], self.tasks))
        if success_tasks:
            await bot.send_private_msg(
                user_id=self.qq, message=f"🎉用户 📱{self.account.phone}\n🛒商品 {self.plans[0].goodID} 兑换成功，可前往米游社查看")
        else:
            msg = f"⚠️用户 📱{self.account.phone}\n🛒商品 {self.plans[0].goodID} 兑换失败\n返回结果：\n"
            num = 0
            for task in self.tasks:
                num += 1
                msg += f"{num}: "
                if isinstance(task.result(), tuple):
                    msg += str(task.result()[1])
                else:
                    msg += f"异常，程序返回结果为 {task.result()}"
                msg += "\n"
            await bot.send_private_msg(user_id=self.qq, message=msg)
        for plan in self.account.exchange:
            if plan == (self.plans[0].goodID, self.plans[0].gameUID):
                self.account.exchange.remove(plan)
        UserData.set_account(self.account, self.qq,
                             self.account.phone)


myb_exchange_plan = on_command(f"{conf.COMMAND_START}兑换",
                               aliases={(f"{conf.COMMAND_START}兑换", "+"), (f"{conf.COMMAND_START}兑换", "-")}, priority=5, block=True)
myb_exchange_plan.name = "兑换"
myb_exchange_plan.usage = f"跟随指引，配置米游币商品自动兑换计划。添加计划之前，请先前往米游社设置好收货地址，并使用『{COMMAND_BEGIN}地址』选择你要使用的地址。所需的商品ID可通过命令『{COMMAND_BEGIN}商品』获取。注意，不限兑换时间的商品将不会在此处显示。 "
myb_exchange_plan.extra_usage = """\
具体用法：
{HEAD}兑换{SEP}+ <商品ID> ➢ 新增兑换计划
{HEAD}兑换{SEP}- <商品ID> ➢ 删除兑换计划
{HEAD}商品 ➢ 查看米游社商品
『{SEP}』为分隔符，使用NoneBot配置中的其他分隔符亦可\
"""


@myb_exchange_plan.handle()
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent], matcher: Matcher, state: T_State, command=Command(),
            command_arg=CommandArg()):
    """
    主命令触发

    :command: 主命令和二级命令的元组
    :command_arg: 二级命令的参数，即商品ID，为Message
    """
    if command_arg and len(command) == 1:
        # 如果没有二级命令，但是有参数，则说明用户没有意向使用本功能。
        # 例如：/兑换码获取，识别到的参数为"码获取"，而用户可能有意使用其他插件。
        await matcher.finish()
    elif len(command) > 1 and command[1] in ["+", "-"]:
        if not command_arg:
            await matcher.reject('⚠️您的输入有误，缺少商品ID，请重新输入\n\n' + matcher.extra_usage.format(HEAD=COMMAND_BEGIN,
                                                                                          SEP=get_last_command_sep()))
        elif not str(command_arg).isdigit():
            await matcher.reject(
                '⚠️商品ID必须为数字，请重新输入\n\n' + matcher.extra_usage.format(HEAD=COMMAND_BEGIN, SEP=get_last_command_sep()))

    if isinstance(event, GroupMessageEvent):
        await matcher.finish("⚠️为了保护您的隐私，请添加机器人好友后私聊进行操作")
    qq_account = int(event.user_id)
    user_account = UserData.read_account_all(qq_account)
    if not user_account:
        await matcher.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}{conf.COMMAND_START}登录』进行登录")
    state['qq_account'] = qq_account
    state['user_account'] = user_account

    # 如果使用了二级命令 + - 则跳转进下一步，通过phone选择账户进行设置
    if len(command) > 1:
        state['command_2'] = command[1]
        matcher.set_arg("good_id", command_arg)
        if len(user_account) == 1:
            matcher.set_arg('phone', Message(str(user_account[0].phone)))
        else:
            phones = [str(user_account[i].phone)
                      for i in range(len(user_account))]
            msg = "您有多个账号，您要配置以下哪个账号的兑换计划？\n"
            msg += "📱" + "\n📱".join(phones)
            msg += "\n🚪发送“退出”即可退出"
            await matcher.send(msg)
    # 如果未使用二级命令，则进行查询操作，并结束交互
    else:
        msg = ""
        for account in user_account:
            for plan in account.exchange:
                good = await get_good_detail(plan[0])
                if not good:
                    await matcher.finish("⚠️获取商品详情失败，请稍后再试")
                msg += f"""\
                \n-- 商品 {good.name}\
                \n- 🔢商品ID：{good.good_id}\
                \n- 💰商品价格：{good.price} 米游币\
                \n- 📅兑换时间：{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(good.time))}\
                \n- 📱账户：{account.phone}""".strip()
                msg += "\n\n"
        if not msg:
            msg = '您还没有兑换计划哦~\n\n'
        await matcher.finish(msg + matcher.extra_usage.format(HEAD=COMMAND_BEGIN, SEP=get_last_command_sep()))


@myb_exchange_plan.got('phone')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, phone=ArgStr('phone')):
    """
    请求用户输入手机号以对账户设置兑换计划
    """
    user_account: List[UserAccount] = state['user_account']

    if phone == '退出':
        await matcher.finish('🚪已成功退出')
    try:
        state["account"] = list(
            filter(lambda account: account.phone == int(phone), user_account))[0]
    except IndexError:
        await matcher.reject('⚠️您发送的账号不在以上账号内，请重新发送')
    except ValueError:
        await matcher.reject('⚠️您发送的账号不是手机号，请重新发送')


@myb_exchange_plan.got('good_id')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, good_id=ArgPlainText('good_id')):
    """
    处理三级命令，即商品ID
    """
    account: UserAccount = state['account']
    command_2 = state['command_2']
    if command_2 == '+':
        good_dict = {
            'bh3': await get_good_list('bh3'),
            'ys': await get_good_list('ys'),
            'bh2': await get_good_list('bh2'),
            'xq': await get_good_list('xq'),
            'wd': await get_good_list('wd'),
            'bbs': await get_good_list('bbs')
        }
        flag = True
        break_flag = False
        good = None
        game = None
        for game, good_list in good_dict.items():
            for good in good_list:
                if good.good_id == good_id:
                    flag = False
                    break_flag = True
                    break
            if break_flag:
                break
        if flag:
            await matcher.finish('⚠️您发送的商品ID不在可兑换的商品列表内，程序已退出')
        state['good'] = good
        uids = []
        if good.time:
            # 若为实物商品，也进入下一步骤，但是传入uid为None
            if good.is_visual:
                game_records = await get_game_record(account)

                if isinstance(game_records, int):
                    pass
                else:
                    game_name = list(filter(lambda abbr: abbr[0] == game, GameInfo.ABBR_TO_ID.values()))[0][1]
                    msg = f'您米游社账户下的『{game_name}』账号：'
                    for record in game_records:
                        if GameInfo.ABBR_TO_ID[record.game_id][0] == game:
                            msg += f'\n🎮 {record.region_name} - {record.nickname} - UID {record.uid}'
                        uids.append(record.uid)
                    if uids:
                        await matcher.send("您兑换的是虚拟物品，请发送想要接收奖励的游戏账号UID：\n🚪发送“退出”即可退出")
                        await asyncio.sleep(0.5)
                        await matcher.send(msg)
                    else:
                        await matcher.finish(f"您还没有绑定『{game_name}』账号哦，暂时不能进行兑换，请先前往米游社绑定后重试")
            else:
                if not account.address:
                    await matcher.finish('⚠️您还没有配置地址哦，请先配置地址')
            state['uids'] = uids
            matcher.set_arg('uid', Message())
        else:
            await matcher.finish(f'⚠️该商品暂时不可以兑换，请重新设置')

    elif command_2 == '-':
        if account.exchange:
            for exchange_good in account.exchange:
                if exchange_good[0] == good_id:
                    account.exchange.remove(exchange_good)
                    UserData.set_account(account, event.user_id, account.phone)
                    scheduler.remove_job(job_id=str(
                        account.phone) + '_' + good_id)
                    await matcher.finish('兑换计划删除成功')
            await matcher.finish(f"您没有设置商品ID为 {good_id} 的兑换哦~")
        else:
            await matcher.finish("您还没有配置兑换计划哦~")

    else:
        await matcher.reject(
            '⚠️您的输入有误，请重新输入\n\n' + matcher.extra_usage.format(HEAD=COMMAND_BEGIN, SEP=get_last_command_sep()))


@myb_exchange_plan.got('uid')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, uid=ArgPlainText('uid')):
    """
    初始化商品兑换任务，如果传入UID为None则为实物商品，仍可继续
    """
    account: UserAccount = state['account']
    good: Good = state['good']
    uids: List[str] = state['uids']
    if good.is_visual:
        if uid == '退出':
            await matcher.finish('🚪已成功退出')
        if uid not in uids:
            await matcher.reject('⚠️您输入的UID不在上述账号内，请重新输入')

    if (good.good_id, uid) in account.exchange:
        await matcher.finish('⚠️您已经配置过该商品的兑换哦！')
    else:
        account.exchange.append((good.good_id, uid))

    # 初始化兑换任务
    exchange_plan = await Exchange(account, good.good_id, uid).async_init()
    if exchange_plan.result == -1:
        await matcher.finish(f"⚠️账户 {account.phone} 登录失效，请重新登录")
    elif exchange_plan.result == -2:
        await matcher.finish(f"⚠️商品 {good.good_id} 为游戏内物品，由于未配置stoken，放弃兑换")
    elif exchange_plan.result == -3:
        await matcher.finish(f"⚠️商品 {good.good_id} 为游戏内物品，由于stoken为\"v2\"类型，且未配置mid，放弃兑换")
    elif exchange_plan.result == -4:
        await matcher.finish(f"⚠️暂不支持商品 {good.good_id} 所属的游戏，放弃兑换")
    elif exchange_plan.result == -5:
        await matcher.finish(f"⚠️获取商品 {good.good_id} 的信息时，网络连接失败或服务器返回不正确，放弃兑换")
    elif exchange_plan.result == -6:
        await matcher.finish(f"⚠️获取商品 {good.good_id} 的信息时，获取用户游戏账户数据失败，放弃兑换")
    else:
        scheduler.add_job(id=str(account.phone) + '_' + good.good_id, replace_existing=True, trigger='date',
                          func=ExchangeStart(
                              account, event.user_id, exchange_plan, conf.EXCHANGE_THREAD).start,
                          next_run_time=datetime.fromtimestamp(good.time))

    UserData.set_account(account, event.user_id, account.phone)

    await matcher.finish(
        f'🎉设置兑换计划成功！将于 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(good.time))} 开始兑换，到时将会私聊告知您兑换结果')


get_good_image = on_command(conf.COMMAND_START + '商品', priority=5, block=True)
get_good_image.name = "商品"
get_good_image.usage = "获取当日米游币商品信息。添加自动兑换计划需要商品ID，请记下您要兑换的商品的ID。"


@get_good_image.handle()
async def _(_: MessageEvent, matcher: Matcher, arg=CommandArg()):
    # 若有使用二级命令，即传入了想要查看的商品类别，则跳过询问
    if arg:
        matcher.set_arg("content", arg)


@get_good_image.got("content", prompt="""\
        \n请发送您要查看的商品类别:\
        \n- 崩坏3\
        \n- 原神\
        \n- 崩坏2\
        \n- 崩坏：星穹铁道\
        \n- 未定事件簿\
        \n- 米游社\
        \n若是商品图片与米游社商品不符或报错 请发送“更新”哦~\
        \n—— 🚪发送“退出”以结束""".strip())
async def _(event: MessageEvent, matcher: Matcher, arg=ArgPlainText("content")):
    """
    根据传入的商品类别，发送对应的商品列表图片
    """
    if arg == '退出':
        await matcher.finish('🚪已成功退出')
    elif arg in ['原神', 'ys']:
        arg = ('ys', '原神')
    elif arg in ['崩坏3', '崩坏三', '崩3', '崩三', '崩崩崩', '蹦蹦蹦', 'bh3']:
        arg = ('bh3', '崩坏3')
    elif arg in ['崩坏2', '崩坏二', '崩2', '崩二', '崩崩', '蹦蹦', 'bh2']:
        arg = ('bh2', '崩坏2')
    elif arg in ['崩坏：星穹铁道', '星铁', '星穹铁道', '铁道', '轨子', '星穹', 'xq']:
        arg = ('xq', '崩坏：星穹铁道')
    elif arg in ['未定', '未定事件簿', 'wd']:
        arg = ('wd', '未定事件簿')
    elif arg in ['大别野', '米游社']:
        arg = ('bbs', '米游社')
    elif arg == '更新':
        await get_good_image.send('⏳正在生成商品信息图片...')
        await generate_image(is_auto=False)
        await get_good_image.finish('商品信息图片刷新成功')
    else:
        await get_good_image.reject('⚠️您的输入有误，请重新输入')
    good_list = await get_good_list(arg[0])
    if good_list:
        img_path = time.strftime(
            f'{conf.goodListImage.SAVE_PATH}/%m-%d-{arg[0]}.jpg', time.localtime())
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                image_bytes = io.BytesIO(f.read())
            await get_good_image.finish(MessageSegment.image(image_bytes))
        else:
            await get_good_image.send('⏳请稍等，商品图片正在生成哦~')
            await generate_image(is_auto=False)
            img_path = time.strftime(
                f'{conf.goodListImage.SAVE_PATH}/%m-%d-{arg[0]}.jpg', time.localtime())
            await get_good_image.finish(MessageSegment.image('file:///' + img_path))
    else:
        await get_good_image.finish(f"{arg[1]} 部分目前没有可兑换商品哦~")


@driver.on_startup
async def _():
    """
    启动机器人时自动初始化兑换任务
    """
    all_accounts = UserData.read_all()
    for qq in all_accounts.keys():
        qq = int(qq)
        accounts = UserData.read_account_all(qq)
        for account in accounts:
            exchange_list = account.exchange
            for exchange_good in exchange_list:
                good_detail = await get_good_detail(exchange_good[0])
                if good_detail == -1:
                    # 若商品不存在则删除
                    account.exchange.remove(exchange_good)
                    UserData.set_account(account, qq, account.phone)
                    continue
                if not good_detail.time:
                    # 若商品已下架则删除
                    account.exchange.remove(exchange_good)
                    UserData.set_account(account, qq, account.phone)
                    continue
                if good_detail.time < NtpTime.time():
                    # 若重启时兑换超时则删除该兑换
                    account.exchange.remove(exchange_good)
                    UserData.set_account(account, qq, account.phone)
                else:
                    exchange_plan = await Exchange(account, exchange_good[0], exchange_good[1]).async_init()
                    scheduler.add_job(id=str(account.phone) + '_' + exchange_good[0], replace_existing=True,
                                      trigger='date', func=ExchangeStart(
                            account, qq, exchange_plan, conf.EXCHANGE_THREAD).start,
                                      next_run_time=datetime.fromtimestamp(good_detail.time))


@driver.on_startup
async def generate_image(is_auto=True):
    """
    生成米游币商品信息图片。

    :param is_auto: True为每日自动生成，False为用户手动更新
    """
    for root, _, files in os.walk(conf.goodListImage.SAVE_PATH, topdown=False):
        for name in files:
            date = time.strftime('%m-%d', time.localtime())
            # 若图片开头为当日日期，则退出函数不执行
            if name.startswith(date):
                if is_auto:
                    return
            # 删除旧图片，以方便生成当日图片
            if name.endswith('.jpg'):
                os.remove(os.path.join(root, name))
    for game in "bh3", "ys", "bh2", "xq", "wd", "bbs":
        good_list = await get_good_list(game)
        if good_list:
            img_path = time.strftime(
                f'{conf.goodListImage.SAVE_PATH}/%m-%d-{game}.jpg', time.localtime())
            image_bytes = await game_list_to_image(good_list)
            if not image_bytes:
                return
            with open(img_path, 'wb') as f:
                f.write(image_bytes)
        else:
            logger.info(f"{conf.LOG_HEAD}{game}分区暂时没有商品，跳过生成...")
