"""
### 米游社商品兑换前端以及计划任务相关
"""
import asyncio
import io
import os
import random
import threading
import time
from datetime import datetime
from multiprocessing import Manager
from multiprocessing.pool import Pool
from multiprocessing.synchronize import Lock
from typing import List, Union, Callable, Any, Tuple, Optional, Dict

import nonebot
from apscheduler.events import JobExecutionEvent, EVENT_JOB_EXECUTED
from nonebot import on_command, get_bot
from nonebot.adapters.onebot.v11 import (MessageEvent, MessageSegment,
                                         PrivateMessageEvent, GroupMessageEvent)
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, ArgPlainText, T_State, CommandArg, Command
from nonebot_plugin_apscheduler import scheduler

from .data_model import Good, GameRecord, ExchangeStatus
from .good_image import game_list_to_image
from .plugin_data import PluginDataManager, write_plugin_data
from .simple_api import get_game_record, get_good_detail, get_good_list, good_exchange_sync, get_device_fp, \
    good_exchange
from .user_data import UserAccount, ExchangePlan, ExchangeResult
from .utils import COMMAND_BEGIN, logger, get_last_command_sep

_conf = PluginDataManager.plugin_data
_driver = nonebot.get_driver()

myb_exchange_plan = on_command(f"{_conf.preference.command_start}兑换",
                               aliases={(f"{_conf.preference.command_start}兑换", "+"),
                                        (f"{_conf.preference.command_start}兑换", "-")},
                               priority=5, block=True)
myb_exchange_plan.name = "兑换"
myb_exchange_plan.usage = "跟随指引，配置米游币商品自动兑换计划。添加计划之前，请先前往米游社设置好收货地址，" \
                          "并使用『{HEAD}地址』选择你要使用的地址。" \
                          "所需的商品ID可通过命令『{HEAD}商品』获取。" \
                          "注意，不限兑换时间的商品将不会在此处显示。 "
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
            await matcher.reject(
                '⚠️您的输入有误，缺少商品ID，请重新输入\n\n' + matcher.extra_usage.format(HEAD=COMMAND_BEGIN,
                                                                                        SEP=get_last_command_sep()))
        elif not str(command_arg).isdigit():
            await matcher.reject(
                '⚠️商品ID必须为数字，请重新输入\n\n' + matcher.extra_usage.format(HEAD=COMMAND_BEGIN,
                                                                                 SEP=get_last_command_sep()))

    user = _conf.users.get(event.user_id)
    user_account = user.accounts if user else None
    if not user_account:
        await matcher.finish(
            f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")

    # 如果使用了二级命令 + - 则跳转进下一步，通过phone选择账户进行设置
    if len(command) > 1:
        state['command_2'] = command[1]
        matcher.set_arg("good_id", command_arg)
        if len(user_account) == 1:
            uid = next(iter(user_account.values())).bbs_uid
            matcher.set_arg('bbs_uid', Message(uid))
        else:
            msg = "您有多个账号，您要配置以下哪个账号的兑换计划？\n"
            msg += "\n".join(map(lambda x: f"🆔{x}", user_account))
            msg += "\n🚪发送“退出”即可退出"
            await matcher.send(msg)
    # 如果未使用二级命令，则进行查询操作，并结束交互
    else:
        msg = ""
        for plan in user.exchange_plans:
            good_detail_status, good = await get_good_detail(plan.good)
            if not good_detail_status:
                await matcher.finish("⚠️获取商品详情失败，请稍后再试")
            msg += f"-- 商品：{good.general_name}" \
                   f"\n- 🔢商品ID：{good.goods_id}" \
                   f"\n- 💰商品价格：{good.price} 米游币" \
                   f"\n- 📅兑换时间：{good.time_text}" \
                   f"\n- 🆔账户：{plan.account.bbs_uid}"
            msg += "\n\n"
        if not msg:
            msg = '您还没有兑换计划哦~\n\n'
        await matcher.finish(msg + matcher.extra_usage.format(HEAD=COMMAND_BEGIN, SEP=get_last_command_sep()))


@myb_exchange_plan.got('bbs_uid')
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent], matcher: Matcher, state: T_State,
            uid=ArgStr('bbs_uid')):
    """
    请求用户输入手机号以对账户设置兑换计划
    """
    user_account = _conf.users[event.user_id].accounts
    if uid == '退出':
        await matcher.finish('🚪已成功退出')
    if uid in user_account:
        state["account"] = user_account[uid]
    else:
        await matcher.reject('⚠️您发送的账号不在以上账号内，请重新发送')


@myb_exchange_plan.got('good_id')
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent], matcher: Matcher, state: T_State,
            good_id=ArgPlainText('good_id')):
    """
    处理三级命令，即商品ID
    """
    account: UserAccount = state['account']
    command_2 = state['command_2']
    if command_2 == '+':
        good_dict = {
            'bh3': (await get_good_list('bh3'))[1],
            'ys': (await get_good_list('hk4e'))[1],
            'bh2': (await get_good_list('bh2'))[1],
            'xq': (await get_good_list('hkrpg'))[1],
            'wd': (await get_good_list('nxx'))[1],
            'bbs': (await get_good_list('bbs'))[1]
        }
        flag = True
        break_flag = False
        good = None
        for good_list in good_dict.values():
            goods_on_sell = filter(lambda x: not x.time_end and x.time_limited, good_list)
            for good in goods_on_sell:
                if good.goods_id == good_id:
                    flag = False
                    break_flag = True
                    break
            if break_flag:
                break
        if flag:
            await matcher.finish('⚠️您发送的商品ID不在可兑换的商品列表内，程序已退出')
        state['good'] = good
        if good.time:
            # 若为实物商品，也进入下一步骤，但是传入uid为None
            if good.is_virtual:
                game_records_status, records = await get_game_record(account)

                if game_records_status:
                    if len(records) == 0:
                        matcher.set_arg('uid', Message(records[0].game_role_id))
                    else:
                        msg = f'您米游社账户下的游戏账号：'
                        for record in records:
                            msg += f'\n🎮 {record.region_name} - {record.nickname} - UID {record.game_role_id}'
                        if records:
                            state['records'] = records
                            await matcher.send(
                                "您兑换的是虚拟物品，请发送想要接收奖励的游戏账号UID：\n🚪发送“退出”即可退出")
                            await asyncio.sleep(0.5)
                            await matcher.send(msg)
                        else:
                            await matcher.finish(
                                f"您的米游社账户下还没有绑定游戏账号哦，暂时不能进行兑换，请先前往米游社绑定后重试")
            else:
                if not account.address:
                    await matcher.finish('⚠️您还没有配置地址哦，请先配置地址')
                matcher.set_arg('uid', Message())
        else:
            await matcher.finish(f'⚠️该商品暂时不可以兑换，请重新设置')

    elif command_2 == '-':
        plans = _conf.users[event.user_id].exchange_plans
        if plans:
            for plan in plans:
                if plan.good.goods_id == good_id:
                    plans.remove(plan)
                    write_plugin_data()
                    for i in range(_conf.preference.exchange_thread_count):
                        scheduler.remove_job(job_id=f"exchange-plan-{hash(plan)}-{i}")
                    await matcher.finish('兑换计划删除成功')
            await matcher.finish(f"您没有设置商品ID为 {good_id} 的兑换哦~")
        else:
            await matcher.finish("您还没有配置兑换计划哦~")

    else:
        await matcher.reject(
            '⚠️您的输入有误，请重新输入\n\n' + matcher.extra_usage.format(HEAD=COMMAND_BEGIN,
                                                                         SEP=get_last_command_sep()))


@myb_exchange_plan.got('uid')
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent], matcher: Matcher, state: T_State,
            uid=ArgPlainText('uid')):
    """
    初始化商品兑换任务，如果传入UID为None则为实物商品，仍可继续
    """
    user = _conf.users[event.user_id]
    account: UserAccount = state['account']
    good: Good = state['good']
    if good.is_virtual:
        records: List[GameRecord] = state['records']
        if uid == '退出':
            await matcher.finish('🚪已成功退出')
        record_filter = filter(lambda x: x.game_role_id == uid, records)
        record = next(record_filter, None)
        if not record:
            await matcher.reject('⚠️您输入的UID不在上述账号内，请重新输入')
        plan = ExchangePlan(good=good, address=account.address, game_record=record, account=account)
    else:
        plan = ExchangePlan(good=good, address=account.address, account=account)
    if plan in user.exchange_plans:
        await matcher.finish('⚠️您已经配置过该商品的兑换哦！')
    else:
        user.exchange_plans.add(plan)
        if not plan.account.device_fp:
            logger.info(f"账号 {plan.account.bbs_uid} 未设置 device_fp，正在获取...")
            fp_status, plan.account.device_fp = await get_device_fp(plan.account.device_id_ios)
            if not fp_status:
                await matcher.send(
                    '⚠️从服务器获取device_fp失败！兑换时将在本地生成device_fp。你也可以尝试重新添加兑换计划。')
        write_plugin_data()

    # 初始化兑换任务
    finished.setdefault(plan, [])
    for i in range(_conf.preference.exchange_thread_count):
        scheduler.add_job(
            good_exchange_sync,
            "date",
            id=f"exchange-plan-{hash(plan)}-{i}",
            replace_existing=True,
            args=(plan,),
            run_date=datetime.fromtimestamp(good.time),
            max_instances=_conf.preference.exchange_thread_count
        )

    await matcher.finish(
        f'🎉设置兑换计划成功！将于 {plan.good.time_text} 开始兑换，到时将会私聊告知您兑换结果')


get_good_image = on_command(_conf.preference.command_start + '商品', priority=5, block=True)
get_good_image.name = "商品"
get_good_image.usage = "获取当日米游币商品信息。添加自动兑换计划需要商品ID，请记下您要兑换的商品的ID。"


@get_good_image.handle()
async def _(_: MessageEvent, matcher: Matcher, arg=CommandArg()):
    # 若有使用二级命令，即传入了想要查看的商品类别，则跳过询问
    if arg:
        matcher.set_arg("content", arg)


@get_good_image.got("content", prompt="请发送您要查看的商品类别:"
                                      "\n- 崩坏3"
                                      "\n- 原神"
                                      "\n- 崩坏2"
                                      "\n- 崩坏：星穹铁道"
                                      "\n- 未定事件簿"
                                      "\n- 米游社"
                                      "\n若是商品图片与米游社商品不符或报错 请发送“更新”哦~"
                                      "\n—— 🚪发送“退出”以结束")
async def _(_: MessageEvent, matcher: Matcher, arg=ArgPlainText("content")):
    """
    根据传入的商品类别，发送对应的商品列表图片
    """
    if arg == '退出':
        await matcher.finish('🚪已成功退出')
    elif arg in ['原神', 'ys']:
        arg = ('hk4e', '原神')
    elif arg in ['崩坏3', '崩坏三', '崩3', '崩三', '崩崩崩', '蹦蹦蹦', 'bh3']:
        arg = ('bh3', '崩坏3')
    elif arg in ['崩坏2', '崩坏二', '崩2', '崩二', '崩崩', '蹦蹦', 'bh2']:
        arg = ('bh2', '崩坏2')
    elif arg in ['崩坏：星穹铁道', '星铁', '星穹铁道', '铁道', '轨子', '星穹', 'xq']:
        arg = ('hkrpg', '崩坏：星穹铁道')
    elif arg in ['未定', '未定事件簿', 'wd']:
        arg = ('nxx', '未定事件簿')
    elif arg in ['大别野', '米游社']:
        arg = ('bbs', '米游社')
    elif arg == '更新':
        threading.Thread(target=generate_image, kwargs={"is_auto": False}).start()
        await get_good_image.finish('⏳后台正在生成商品信息图片，请稍后查询')
    else:
        await get_good_image.reject('⚠️您的输入有误，请重新输入')

    img_path = time.strftime(
        f'{_conf.good_list_image_config.SAVE_PATH}/%m-%d-{arg[0]}.jpg', time.localtime())
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            image_bytes = io.BytesIO(f.read())
        await get_good_image.finish(MessageSegment.image(image_bytes))
    else:
        await get_good_image.finish(
            f'{arg[1]} 分区暂时没有可兑换的限时商品。如果这与实际不符，你可以尝试用『{COMMAND_BEGIN}商品 更新』进行更新。')


lock = threading.Lock()
finished: Dict[ExchangePlan, List[bool]] = {}


@lambda func: scheduler.add_listener(func, EVENT_JOB_EXECUTED)
def exchange_notice(event: JobExecutionEvent):
    """
    接收兑换结果
    """
    if event.job_id.startswith("exchange-plan"):
        bot = get_bot()
        loop = asyncio.get_event_loop()

        thread_id = int(event.job_id.split('-')[-1]) + 1
        result: Tuple[ExchangeStatus, Optional[ExchangeResult]] = event.retval
        exchange_status, exchange_result = result

        if not exchange_status:
            hash_value = int(event.job_id.split('-')[-2])
            plans = map(lambda x: x.exchange_plans, _conf.users.values())
            plan_filter = filter(lambda x: hash(x[0]) == hash_value, zip(plans, _conf.users.keys()))
            plan_tuple = next(plan_filter)
            plan, user_id = plan_tuple
            with lock:
                finished[plan].append(False)
                loop.create_task(
                    bot.send_private_msg(
                        user_id=user_id,
                        message=f"⚠️账户 {plan.account.bbs_uid}"
                                f"\n- {plan.good.general_name}"
                                f"\n- 线程 {thread_id}"
                                f"\n- 兑换请求发送失败"
                    )
                )
                if len(finished[plan]) == _conf.preference.exchange_thread_count:
                    del plan
                    write_plugin_data()

        else:
            plan = exchange_result.plan
            user_filter = filter(lambda x: plan in x[1].exchange_plans, _conf.users.items())
            user_id, user = next(user_filter)
            with lock:
                # 如果已经有一个线程兑换成功，就不再接收结果
                if True not in finished[plan]:
                    if exchange_result.result:
                        finished[plan].append(True)
                        loop.create_task(
                            bot.send_private_msg(
                                user_id=user_id,
                                message=f"🎉账户 {plan.account.bbs_uid}"
                                        f"\n- {plan.good.general_name}"
                                        f"\n- 线程 {thread_id}"
                                        f"\n- 兑换成功"
                            )
                        )
                    else:
                        finished[plan].append(False)
                        loop.create_task(
                            bot.send_private_msg(
                                user_id=user_id,
                                message=f"💦账户 {plan.account.bbs_uid}"
                                        f"\n- {plan.good.general_name}"
                                        f"\n- 线程 {thread_id}"
                                        f"\n- 兑换失败"
                            )
                        )

                if len(finished[plan]) == _conf.preference.exchange_thread_count:
                    try:
                        user.exchange_plans.remove(plan)
                    except KeyError:
                        pass
                    else:
                        write_plugin_data()


async def exchange_begin(plan: ExchangePlan):
    """
    到点后执行兑换

    :param plan: 兑换计划
    """
    duration = 0
    random_x, random_y = _conf.preference.exchange_latency
    exchange_status, exchange_result = ExchangeStatus(), None

    # 在兑换开始后的一段时间内，不断尝试兑换，直到成功（因为太早兑换可能被认定不在兑换时间）
    while duration < _conf.preference.exchange_duration:
        latency = random.uniform(random_x, random_y)
        time.sleep(latency)
        exchange_status, exchange_result = await good_exchange(plan)
        if exchange_status and exchange_result.result:
            break
        duration += latency
    return exchange_status, exchange_result


@_driver.on_startup
async def _():
    """
    启动机器人时自动初始化兑换任务
    """
    for user_id, user in _conf.users.items():
        plans = user.exchange_plans
        for plan in plans:
            good_detail_status, good = await get_good_detail(plan.good)
            if good_detail_status.good_not_existed or good.time < time.time():
                # 若商品不存在则删除
                # 若重启时兑换超时则删除该兑换
                user.exchange_plans.remove(plan)
                write_plugin_data()
                continue
            else:
                finished.setdefault(plan, [])
                for i in range(_conf.preference.exchange_thread_count):
                    scheduler.add_job(
                        exchange_begin,
                        "date",
                        id=f"exchange-plan-{hash(plan)}-{i}",
                        replace_existing=True,
                        args=(plan,),
                        run_date=datetime.fromtimestamp(good.time),
                        max_instances=_conf.preference.exchange_thread_count
                    )


def image_process(game: str, lock: Lock = None):
    """
    生成并保存图片的进程函数

    :param game: 游戏名
    :param lock: 进程锁
    :return: 生成成功或无商品返回True，否则返回False
    """
    loop = asyncio.new_event_loop()
    good_list_status, good_list = loop.run_until_complete(get_good_list(game))
    if not good_list_status:
        logger.error(f"{_conf.preference.log_head}获取 {game} 分区的商品列表失败，跳过该分区的商品图片生成")
        return False
    good_list = list(filter(lambda x: not x.time_end and x.time_limited, good_list))
    if good_list:
        logger.info(f"{_conf.preference.log_head}正在生成 {game} 分区的商品列表图片")
        image_bytes = loop.run_until_complete(game_list_to_image(good_list, lock))
        if not image_bytes:
            return False
        date = time.strftime('%m-%d', time.localtime())
        path = _conf.good_list_image_config.SAVE_PATH / f"{date}-{game}.jpg"
        with open(path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"{_conf.preference.log_head}已完成 {game} 分区的商品列表图片生成")
    else:
        logger.info(f"{_conf.preference.log_head}{game}分区暂时没有可兑换的限时商品，跳过该分区的商品图片生成")
    return True


def generate_image(is_auto=True, callback: Callable[[bool], Any] = None):
    """
    生成米游币商品信息图片。该函数会阻塞当前线程

    :param is_auto: True为每日自动生成，False为用户手动更新
    :param callback: 回调函数，参数为生成成功与否
    """
    for root, _, files in os.walk(_conf.good_list_image_config.SAVE_PATH, topdown=False):
        for name in files:
            date = time.strftime('%m-%d', time.localtime())
            # 若图片开头为当日日期，则退出函数不执行
            if name.startswith(date):
                if is_auto:
                    return
            # 删除旧图片
            if name.endswith('.jpg'):
                os.remove(os.path.join(root, name))

    if _conf.good_list_image_config.MULTI_PROCESS:
        lock: Lock = Manager().Lock()
        with Pool() as pool:
            for game in "bh3", "hk4e", "bh2", "hkrpg", "nxx", "bbs":
                pool.apply_async(image_process,
                                 args=(game, lock),
                                 callback=callback)
            pool.close()
            pool.join()
    else:
        for game in "bh3", "hk4e", "bh2", "hkrpg", "nxx", "bbs":
            image_process(game)

    logger.info(f"{_conf.preference.log_head}已完成所有分区的商品列表图片生成")
