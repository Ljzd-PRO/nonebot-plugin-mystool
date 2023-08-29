'''
Author: Night-stars-1 nujj1042633805@gmail.com
Date: 2023-07-09 21:19:23
LastEditors: Night-stars-1 nujj1042633805@gmail.com
LastEditTime: 2023-08-29 23:56:03
Description: 

Copyright (c) 2023 by Night-stars-1, All Rights Reserved. 
'''
"""
### 计划任务相关
"""
import asyncio
import random
import threading
from typing import Union

from nonebot import get_bot, on_command
from nonebot.params import Arg, CommandArg
from nonebot.adapters.onebot.v11 import (MessageSegment,
                                         PrivateMessageEvent, GroupMessageEvent, Message, MessageEvent)
from nonebot.adapters.console import (MessageEvent as ConsoleMessageEvent)
from nonebot.adapters.qqguild import (MessageEvent as GuildMessageEvent)
#from nonebot.adapters.telegram import Bot as TgBot
from nonebot.internal.adapter.bot import Bot
from nonebot_plugin_saa import Image, Text, MessageFactory
from nonebot_plugin_apscheduler import scheduler

from .game_sign_api import BaseGameSign, GenshinImpactSign, StarRailSign
from .myb_missions_api import BaseMission, get_missions_state
from .plugin_data import PluginDataManager, write_plugin_data
from .simple_api import genshin_board, get_game_record, star_board
from .utils import get_file, logger, COMMAND_BEGIN, CommandArgs, ALL_MessageEvent, ALL_Message, ALL_G_MessageEvent
from .data_model import BaseApiStatus

_conf = PluginDataManager.plugin_data_obj

failed_list = {
    "未登录": set(),
    "签到失败": set(),
    "删除账号": set()
}

failed_list_default = failed_list.copy()


manually_game_sign = on_command(_conf.preference.command_start + '签到', aliases={"sign"}, priority=5, block=True)
manually_game_sign.name = '签到'
manually_game_sign.command = 'sign'
manually_game_sign.usage = '手动进行游戏签到，查看本次签到奖励及本月签到天数'

@manually_game_sign.handle()
async def _(bot: Bot, event: ALL_G_MessageEvent):
    """
    手动游戏签到函数
    """
    qq = event.get_user_id() if not isinstance(event, ConsoleMessageEvent) else 1042633805
    logger.info(qq)
    user = _conf.users.get(qq)
    if not user or not user.accounts:
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』或者『{COMMAND_BEGIN}扫码登录』进行登录")
    await manually_game_sign.send("⏳开始游戏签到...")
    await perform_game_sign(bot=bot, qq=qq, is_auto=False, group_event=event)

manually_bbs_sign = on_command(_conf.preference.command_start + '任务', priority=5, block=True)
manually_bbs_sign.name = '任务'
manually_bbs_sign.usage = '手动执行米游币每日任务，可以查看米游币任务完成情况'


@manually_bbs_sign.handle()
async def _(bot: Bot, event: ConsoleMessageEvent):
    """
    手动米游币任务函数
    """
    qq = event.get_user_id() if not isinstance(event, ConsoleMessageEvent) else 1042633805
    user = _conf.users.get(qq)
    if not user or not user.accounts:
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    await manually_game_sign.send("⏳开始执行米游币任务...")
    await perform_bbs_sign(bot=bot, qq=qq, is_auto=False, group_event=event)


manually_resin_check = on_command(_conf.preference.command_start + '便笺', aliases={_conf.preference.command_start + '体力'}, priority=5, block=True, state={"default_args":"原神"})
manually_resin_check.name = '便笺'
manually_resin_check.usage = '手动查看原神实时便笺，即原神树脂、洞天财瓮等信息'
has_checked = {}
for user in _conf.users.values():
    for account in user.accounts.values():
        if account.enable_resin:
            has_checked[account.bbs_uid] = has_checked.get(account.bbs_uid,
                                                           {"resin": False, "coin": False, "transformer": False})

@manually_resin_check.handle()
async def _(bot: Bot, event: ALL_G_MessageEvent, args=CommandArgs()):
    """
    手动查看原神便笺
    """
    qq = event.get_user_id() if not isinstance(event, ConsoleMessageEvent) else 1042633805
    user = _conf.users.get(qq)
    if not user or not user.accounts:
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    if args[0] == "原神":
        await gs_resin_check(bot=bot, qq=qq, is_auto=False, group_event=event)
    elif args[0] == "星穹铁道" or args[0] == "星铁":
        await sr_resin_check(bot=bot, qq=qq, is_auto=False, group_event=event)


async def perform_game_sign(bot: Bot, qq: int, is_auto: bool,
                            group_event: ALL_MessageEvent = None):
    """
    执行游戏签到函数，并发送给用户签到消息。

    :param bot: Bot实例
    :param qq: 用户QQ号
    :param is_auto: `True`为当日自动签到，`False`为用户手动调用签到功能
    :param group_event: 若为群消息触发，则为群消息事件，否则为None
    """
    global failed_list
    if isinstance(group_event, PrivateMessageEvent):
        group_event = None
    user = _conf.users[qq]
    for account in _conf.users.get(qq).accounts.values():
        signed = False
        """是否已经完成过签到"""
        game_record_status, records = await get_game_record(account)
        if not game_record_status:
            if group_event:
                await bot.send(event=group_event, at_sender=True,
                               message=f"⚠️账户 {account.bbs_uid} 获取游戏账号信息失败，请重新尝试")
            else:
                ...
                '''
                await bot.send_private_msg(user_id=qq,
                                           message=f"⚠️账户 {account.bbs_uid} 获取游戏账号信息失败，请重新尝试")
                '''
            if is_auto:
                failed_list['未登录'].add(qq)
            continue
        games_has_record = []
        msg_list = []

        game_tasks = BaseGameSign.AVAILABLE_GAME_SIGNS.copy()
        for class_type in game_tasks:
            signer = class_type(account, records)
            if not signer.has_record:
                continue
            else:
                games_has_record.append(signer)
            get_info_status, info = await signer.get_info(account.platform)
            if not get_info_status:
                if group_event:
                    await bot.send(event=group_event, at_sender=True,
                                   message=f"⚠️账户 {account.bbs_uid} 获取签到记录失败, 请重新登录")
                else:
                    ...
                    '''
                    await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.bbs_uid} 获取签到记录失败")
                    '''
                if is_auto:
                    failed_list['未登录'].add(qq)

            # 自动签到时，要求用户打开了签到功能；手动签到时都可以调用执行。若没签到，则进行签到功能。
            # 若获取今日签到情况失败，仍可继续
            sign_status=BaseApiStatus()
            if ((account.enable_game_sign and is_auto) or not is_auto) and (
                    (info and not info.is_sign) or not get_info_status):
                sign_status = await signer.sign(account.platform)
                logger.info(sign_status)
                if not sign_status:
                    if sign_status.login_expired:
                        status = "登录失效"
                        _conf.users.pop(qq)
                        write_plugin_data()
                        failed_list['删除账号'].add(qq)
                        failed_list['未登录'].add(qq)
                    elif sign_status.need_verify:
                        status = "验证码拦截"
                        failed_list['签到失败'].add(qq)
                    else:
                        status = "签到失败"
                        failed_list['未登录'].add(qq)
                    #await asyncio.sleep(_conf.preference.sleep_time)
                #await asyncio.sleep(_conf.preference.sleep_time)
            # 若用户未开启自动签到且手动签到过了，不再提醒
            elif not account.enable_game_sign and is_auto:
                continue
            else:
                signed = True

            # 用户打开通知或手动签到时，进行通知
            if user.enable_notice:
                get_info_status, info = await signer.get_info(account.platform)
                get_award_status, awards = await signer.get_rewards()
                if not get_info_status or not get_award_status:
                    msg_list.append(f"⚠️账户 {account.bbs_uid} 🎮『{signer.NAME}』获取签到结果失败！请手动前往米游社查看")
                else:
                    award = awards[info.total_sign_day - 1]
                    if info.is_sign:
                        failed_list['未登录'].discard(qq)
                        #img_file = await get_file(award.icon)
                        #img = MessageSegment.image(img_file)
                        status = "签到成功！" if not signed else "已经签到过了"
                    elif sign_status:
                        status = "签到失败！"
                    if sign_status.need_verify:
                        status = "成功绕过验证码"
                    msg_list.append(f"🪪账户 {account.bbs_uid}" \
                            f"\n🎮『{signer.NAME}』" \
                            f"\n🎮状态: {status}" \
                            f"\n{signer.record.nickname}·{signer.record.level}" \
                            "\n\n🎁今日签到奖励：" \
                            f"\n{award.name} * {award.cnt}" \
                            f"\n\n📅本月签到次数：{info.total_sign_day}")
            #await asyncio.sleep(_conf.preference.sleep_time)
        if not is_auto and qq not in failed_list['未登录']:
            msg_list += await perform_bbs_sign(bot=bot, qq=qq, is_auto=is_auto, group_event=group_event)
        user_id = _conf.preference.forward_msg_qq if _conf.preference.forward_msg_qq != 0 else qq
        msg = [
            MessageSegment.node_custom(
                user_id=user_id,
                nickname="哎嘿",
                content=Message(MessageSegment.text(msg_i)),
            )
            for msg_i in msg_list
        ]
        logger.info(msg)
        if group_event:
            await bot.send_group_forward_msg(group_id=group_event.group_id, messages=msg)
        else:
            ...
            #await bot.send_private_forward_msg(user_id=qq, messages=msg)

        if not games_has_record:
            if group_event:
                await bot.send(
                    event=group_event,
                    at_sender=True,
                    message=f"⚠️您的米游社账户 {account.bbs_uid} 下不存在任何游戏账号，已跳过签到"
                )
            else:
                ...
                '''
                await bot.send_msg(
                    message_type="private",
                    user_id=qq,
                    message=f"⚠️您的米游社账户 {account.bbs_uid} 下不存在任何游戏账号，已跳过签到"
                )
                '''

async def perform_bbs_sign(bot: Bot, qq: int, is_auto: bool,
                           group_event: ALL_MessageEvent = None):
    """
    执行米游币任务函数，并发送给用户任务执行消息。

    :param bot: Bot实例
    :param qq: 用户QQ号
    :param is_auto: True为当日自动执行任务，False为用户手动调用任务功能
    :param group_event: 若为群消息触发，则为群消息事件，否则为None
    """
    global failed_list
    if isinstance(group_event, PrivateMessageEvent):
        group_event = None
    user = _conf.users[qq]
    msg_list = []
    sign_status = BaseApiStatus()
    read_status = BaseApiStatus()
    like_status = BaseApiStatus()
    share_status = BaseApiStatus()
    for account in user.accounts.values():
        for class_type in account.mission_games:
            mission_obj: BaseMission = class_type(account)
            missions_state_status, missions_state = await get_missions_state(account)
            if not missions_state_status:
                if missions_state_status.login_expired:
                    msg_list.append(f"⚠️账户 {account.bbs_uid} 登录失效，请重新登录")
                    continue
                msg_list.append(f"⚠️账户 {account.bbs_uid} 获取任务完成情况请求失败，你可以手动前往App查看")
                continue

            myb_before_mission = missions_state.current_myb

            # 自动执行米游币任务时，要求用户打开了任务功能；手动执行时都可以调用执行。
            if (account.enable_mission and is_auto) or not is_auto:

                # 执行任务
                for key_name, (mission, current) in missions_state.state_dict.items():
                    if current < mission.threshold:
                        if key_name == BaseMission.SIGN:
                            sign_status = await mission_obj.sign()
                        elif key_name == BaseMission.VIEW:
                            read_status = await mission_obj.read()
                        elif key_name == BaseMission.LIKE:
                            like_status = await mission_obj.like()
                        elif key_name == BaseMission.SHARE:
                            share_status = await mission_obj.share()

                # 用户打开通知或手动任务时，进行通知
                if user.enable_notice or not is_auto:
                    missions_state_status, missions_state = await get_missions_state(account)
                    if not missions_state_status:
                        if missions_state_status.login_expired:
                            msg_list.append(f"⚠️账户 {account.bbs_uid} 登录失效，请重新登录")
                            continue
                        msg_list.append(f"⚠️账户 {account.bbs_uid} 获取任务完成情况请求失败，你可以手动前往App查看")
                        continue
                    if all(map(lambda x: x[1] >= x[0].threshold, missions_state.state_dict.values())):
                        notice_string = f"🎉已完成今日米游币任务 - 分区『{class_type.NAME}』"
                    else:
                        notice_string = f"⚠️今日米游币任务未全部完成 - 分区『{class_type.NAME}』"

                    msg = f"{notice_string}" \
                          f"\n🆔账户 {account.bbs_uid}"
                    for key_name, (mission, current) in missions_state.state_dict.items():
                        if key_name == BaseMission.SIGN:
                            mission_name = "签到"
                            logger.info(sign_status)
                            status = '遇到验证码' if not sign_status and sign_status.need_verify else '✕'
                        elif key_name == BaseMission.VIEW:
                            mission_name = "阅读"
                            status = '遇到验证码' if not read_status and read_status.need_verify else '✕'
                        elif key_name == BaseMission.LIKE:
                            mission_name = "点赞"
                            status = '遇到验证码' if not like_status and like_status.need_verify else '✕'
                        elif key_name == BaseMission.SHARE:
                            mission_name = "转发"
                            status = '遇到验证码' if not share_status and share_status.need_verify else '✕'
                        else:
                            mission_name = mission.mission_key
                        if current >= mission.threshold:
                            msg += f"\n- {mission_name} {'✓'}"
                        else:
                            msg += f"\n- {mission_name} {status}"
                    msg += f"\n💰获得米游币: {missions_state.current_myb - myb_before_mission}"
                    msg += f"\n💰当前米游币: {missions_state.current_myb}"
                    msg.strip()
                    msg_list.append(msg)
    return msg_list

async def gs_resin_check(bot: Bot, qq: int, is_auto: bool,
                      group_event: ALL_MessageEvent = None):
    """
    查看原神实时便笺函数，并发送给用户任务执行消息。

    :param bot: Bot实例
    :param qq: 用户QQ号
    :param is_auto: True为自动检查，False为用户手动调用该功能
    :param group_event: 若为群消息触发，则为群消息事件，否则为None
    """
    if isinstance(group_event, PrivateMessageEvent):
        group_event = None
    global has_checked
    user = _conf.users[qq]
    for account in user.accounts.values():
        if account.enable_resin:
            has_checked[account.bbs_uid] = has_checked.get(account.bbs_uid,
                                                           {"resin": False, "coin": False, "transformer": False})
        if (account.enable_resin and is_auto) or not is_auto:
            genshin_board_status, board = await genshin_board(account)
            if not genshin_board_status:
                if genshin_board_status.login_expired:
                    if not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {account.bbs_uid} 登录失效，请重新登录')
                        else:
                            await bot.send_private_msg(user_id=qq,
                                                       message=f'⚠️账户 {account.bbs_uid} 登录失效，请重新登录')
                if genshin_board_status.no_genshin_account:
                    if not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {account.bbs_uid} 没有绑定任何原神账户，请绑定后再重试')
                        else:
                            await bot.send_private_msg(user_id=qq,
                                                       message=f'⚠️账户 {account.bbs_uid} 没有绑定任何原神账户，请绑定后再重试')
                        account.enable_resin = False
                        write_plugin_data()
                        continue
                if not is_auto:
                    if group_event:
                        await bot.send(event=group_event, at_sender=True,
                                       message=f'⚠️账户 {account.bbs_uid} 获取实时便笺请求失败，你可以手动前往App查看')
                    else:
                        await bot.send_private_msg(user_id=qq,
                                                   message=f'⚠️账户 {account.bbs_uid} 获取实时便笺请求失败，你可以手动前往App查看')
                continue
            if genshin_board_status.need_verify:
                if group_event:
                    await bot.send(event=group_event, at_sender=True,
                                   message=f'⚠️遇到验证码正在尝试绕过')
                else:
                    await bot.send_private_msg(user_id=qq,
                                               message=f'⚠️遇到验证码正在尝试绕过')
            msg = ''
            # 手动查询体力时，无需判断是否溢出
            if not is_auto:
                pass
            else:
                # 体力溢出提醒
                if board.current_resin == 160:
                    # 防止重复提醒
                    if has_checked[account.bbs_uid]['resin']:
                        return
                    else:
                        has_checked[account.bbs_uid]['resin'] = True
                        msg += '❕您的树脂已经满啦\n'
                else:
                    has_checked[account.bbs_uid]['resin'] = False
                # 洞天财瓮溢出提醒
                if board.current_home_coin == board.max_home_coin:
                    # 防止重复提醒
                    if has_checked[account.bbs_uid]['coin']:
                        return
                    else:
                        has_checked[account.bbs_uid]['coin'] = True
                        msg += '❕您的洞天财瓮已经满啦\n'
                else:
                    has_checked[account.bbs_uid]['coin'] = False
                # 参量质变仪就绪提醒
                if board.transformer:
                    if board.transformer_text == '已准备就绪':
                        # 防止重复提醒
                        if has_checked[account.bbs_uid]['transformer']:
                            return
                        else:
                            has_checked[account.bbs_uid]['transformer'] = True
                            msg += '❕您的参量质变仪已准备就绪\n\n'
                    else:
                        has_checked[account.bbs_uid]['transformer'] = False
                        return
            msg += "❖实时便笺❖" \
                f"\n⏳树脂数量：{board.current_resin} / 160" \
                f"\n🕰️探索派遣：{board.current_expedition_num} / {board.max_expedition_num}" \
                f"\n📅每日委托：{4 - board.finished_task_num} 个任务未完成" \
                f"\n💰洞天财瓮：{board.current_home_coin} / {board.max_home_coin}" \
                f"\n🎰参量质变仪：{board.transformer_text if board.transformer else 'N/A'}"
            if group_event:
                await bot.send(event=group_event, at_sender=True, message=msg)
            else:
                await bot.send_private_msg(user_id=qq, message=msg)

async def sr_resin_check(bot: Bot, qq: int, is_auto: bool,
                      group_event: ALL_MessageEvent = None):
    """
    查看星穹铁道实时便笺函数，并发送给用户任务执行消息。

    :param bot: Bot实例
    :param qq: 用户QQ号
    :param is_auto: True为自动检查，False为用户手动调用该功能
    :param group_event: 若为群消息触发，则为群消息事件，否则为None
    """
    if isinstance(group_event, PrivateMessageEvent):
        group_event = None
    global has_checked
    user = _conf.users[qq]
    for account in user.accounts.values():
        if account.enable_resin:
            has_checked[account.bbs_uid] = has_checked.get(account.bbs_uid,
                                                           {"resin": False, "coin": False, "transformer": False})
        if (account.enable_resin and is_auto) or not is_auto:
            star_board_status, board = await star_board(account)
            if not star_board_status:
                if star_board_status.login_expired:
                    if not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {account.bbs_uid} 登录失效，请重新登录')
                        else:
                            await bot.send_private_msg(user_id=qq,
                                                       message=f'⚠️账户 {account.bbs_uid} 登录失效，请重新登录')
                if star_board_status.no_genshin_account:
                    if not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {account.bbs_uid} 没有绑定任何原神账户，请绑定后再重试')
                        else:
                            await bot.send_private_msg(user_id=qq,
                                                       message=f'⚠️账户 {account.bbs_uid} 没有绑定任何原神账户，请绑定后再重试')
                        account.enable_resin = False
                        write_plugin_data()
                        continue
                if not is_auto:
                    if group_event:
                        await bot.send(event=group_event, at_sender=True,
                                       message=f'⚠️账户 {account.bbs_uid} 获取实时便笺请求失败，你可以手动前往App查看')
                    else:
                        await bot.send_private_msg(user_id=qq,
                                                   message=f'⚠️账户 {account.bbs_uid} 获取实时便笺请求失败，你可以手动前往App查看')
                continue
            if star_board_status.need_verify:
                if group_event:
                    await bot.send(event=group_event, at_sender=True,
                                   message=f'⚠️遇到验证码正在尝试绕过')
                else:
                    await bot.send_private_msg(user_id=qq,
                                               message=f'⚠️遇到验证码正在尝试绕过')
            msg = "❖实时便笺❖" \
                f"\n⏳体力数量：{board.current_stamina} / 180" \
                f"\n🕰️每日实训：{board.current_train_score} / 500" \
                f"\n📅每日委托：{board.total_expedition_num} / {board.total_expedition_num}" \
                f"\n💰模拟宇宙：{board.current_rogue_score} / {board.max_rogue_score}" 
            if group_event:
                await bot.send(event=group_event, at_sender=True, message=msg)
            else:
                await bot.send_private_msg(user_id=qq, message=msg)

'''
@scheduler.scheduled_job("cron", hour='0', minute='0', id="daily_goodImg_update")
def daily_update():
    """
    每日图片生成函数
    """
    logger.info(f"{_conf.preference.log_head}后台开始生成每日商品图片")
    threading.Thread(target=generate_image).start()
'''

'''
@scheduler.scheduled_job("cron",
                         hour=_conf.preference.plan_time.split(':')[0],
                         minute=_conf.preference.plan_time.split(':')[1],
                         id="daily_schedule")
async def daily_schedule():
    """
    自动米游币任务、游戏签到函数
    """
    # 随机延迟
    global failed_list
    message = "⚠️每日签到执行完成"
    await asyncio.sleep(random.randint(0, 59))
    logger.info(f"{_conf.preference.log_head}开始执行每日自动任务")
    bot:Bot = get_bot()
    await bot.send_msg(
        message_type="group",
        group_id=719540466,
        message=f"⚠️开始执行每日签到"
    )
    failed_list = failed_list_default
    copy_users = _conf.users.copy()
    for qq in copy_users:
        await perform_game_sign(bot=bot, qq=qq, is_auto=True)
    logger.info(f"{_conf.preference.log_head}每日自动任务执行完成")
    cg_len = len(_conf.users)
    for failed_cause, failed_account in failed_list.items():
        message += "\n🎮{failed_cause}:『{sb_len}』".format(failed_cause=failed_cause,sb_len=str(len(failed_account)))
        cg_len -= len(failed_account) if failed_cause != "删除账号" else 0
    message += f"\n🎮成功:『{cg_len}』"
    await bot.send_msg(
        message_type="group",
        group_id=719540466,
        message=message
    )
'''

atuo_sign = on_command(_conf.preference.command_start + '自动签到', priority=5, block=True)

@atuo_sign.handle()
async def daily_schedule(bot: Bot, event: ALL_G_MessageEvent):
    """
    自动米游币任务、游戏签到函数
    """
    # 随机延迟
    global failed_list
    qq = event.get_user_id() if isinstance(event, GroupMessageEvent) else 1042633805
    if qq == 1042633805:
        message = "⚠️每日签到执行完成"
        logger.info(f"{_conf.preference.log_head}开始执行每日自动任务")
        await bot.send_msg(
            message_type="group",
            group_id=719540466,
            message=f"⚠️开始执行每日签到"
        )
        failed_list = failed_list_default
        copy_users = _conf.users.copy()
        for qq in copy_users:
            await perform_game_sign(bot=bot, qq=qq, is_auto=True)
        logger.info(f"{_conf.preference.log_head}每日自动任务执行完成")
        cg_len = len(_conf.users)
        for failed_cause, failed_account in failed_list.items():
            message += "\n🎮{failed_cause}:『{sb_len}』".format(failed_cause=failed_cause,sb_len=str(len(failed_account)))
            cg_len -= len(failed_account) if failed_cause != "删除账号" else 0
        message += f"\n🎮成功:『{cg_len}』"
        await bot.send_msg(
            message_type="group",
            group_id=719540466,
            message=message
        )
    else:
        await bot.send_msg(
            message_type="group",
            group_id=719540466,
            message="爬!!!"
        )

'''
@scheduler.scheduled_job("interval",
                         minutes=_conf.preference.resin_interval,
                         id="resin_check")
async def auto_resin_check():
    """
    自动查看实时便笺
    """
    bot = get_bot()
    for qq in _conf.users:
        await resin_check(bot=bot, qq=qq, is_auto=True)
'''
