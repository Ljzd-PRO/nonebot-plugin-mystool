"""
### 计划任务相关
"""
import asyncio
import random
from typing import List, Union

from nonebot import get_bot, on_command
from nonebot.adapters.onebot.v11 import (Bot, MessageSegment,
                                         PrivateMessageEvent, GroupMessageEvent)
from nonebot_plugin_apscheduler import scheduler

from .base_api import GameInfo, GameRecord, genshin_board_bbs, get_game_record
from .game_sign_api import BaseGameSign
from .myb_missions_api import BaseMission, get_missions_state
from .plugin_data import plugin_data_obj as conf, write_plugin_data
from .user_data import UserData
from .exchangePlan import generate_image
from .utils import blur_phone as blur
from .utils import get_file, logger, COMMAND_BEGIN

manually_game_sign = on_command(conf.COMMAND_START + '签到', priority=5, block=True)
manually_game_sign.name = '签到'
manually_game_sign.usage = '手动进行游戏签到，查看本次签到奖励及本月签到天数'


@manually_game_sign.handle()
async def _(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    """
    手动游戏签到函数
    """
    bot = get_bot(str(event.self_id))
    if not conf.users[event.user_id].accounts:
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    await perform_game_sign(bot=bot, qq=event.user_id, is_auto=False, group_event=event)


manually_bbs_sign = on_command(conf.preference.command_start + '任务', priority=5, block=True)
manually_bbs_sign.name = '任务'
manually_bbs_sign.usage = '手动执行米游币每日任务，可以查看米游币任务完成情况'


@manually_bbs_sign.handle()
async def _(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    """
    手动米游币任务函数
    """
    bot = get_bot(str(event.self_id))
    if not conf.users[event.user_id].accounts:
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    await perform_bbs_sign(bot=bot, qq=event.user_id, is_auto=False, group_event=event)


manually_resin_check = on_command(conf.preference.command_start + '便笺', priority=5, block=True)
manually_resin_check.name = '便笺'
manually_resin_check.usage = '手动查看原神实时便笺，即原神树脂、洞天财瓮等信息'
has_checked = {}
for user in conf.users.values():
    for account in user.accounts.values():
        if account.enable_resin:
            has_checked[account.bbs_uid] = has_checked.get(account.bbs_uid,
                                                           {"resin": False, "coin": False, "transformer": False})


@manually_resin_check.handle()
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent]):
    """
    手动查看原神便笺
    """
    bot = get_bot(str(event.self_id))
    if not conf.users[event.user_id].accounts:
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    await resin_check(bot=bot, qq=event.user_id, is_auto=False, group_event=event)


async def perform_game_sign(bot: Bot, qq: int, is_auto: bool,
                            group_event: Union[GroupMessageEvent, PrivateMessageEvent, None] = None):
    """
    执行游戏签到函数，并发送给用户签到消息。

    :param bot: Bot实例
    :param qq: 用户QQ号
    :param is_auto: `True`为当日自动签到，`False`为用户手动调用签到功能
    :param group_event: 若为群消息触发，则为群消息事件，否则为None
    """
    if isinstance(group_event, PrivateMessageEvent):
        group_event = None
    failed_accounts = []
    for account in conf.users.get(qq).accounts.values():
        game_record_status, records = await get_game_record(account)
        if not game_record_status:
            if group_event:
                await bot.send(event=group_event, at_sender=True,
                               message=f"⚠️账户 {blur(account.phone)} 获取游戏账号信息失败，请重新尝试")
            else:
                await bot.send_private_msg(user_id=qq,
                                           message=f"⚠️账户 {account.phone} 获取游戏账号信息失败，请重新尝试")
            continue
        for class_name in BaseGameSign.AVAILABLE_GAME_SIGNS:
            signer = class_name(account, records)
            get_info_status, info = await signer.get_info(account.platform)
            if not get_info_status:
                if group_event:
                    await bot.send(event=group_event, at_sender=True,
                                   message=f"⚠️账户 {blur(account.phone)} 获取签到记录失败")
                else:
                    await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 获取签到记录失败")

            # 自动签到时，要求用户打开了签到功能；手动签到时都可以调用执行。若没签到，则进行签到功能。
            # 若获取今日签到情况失败，仍可继续
            if ((account.enable_game_sign and is_auto) or not is_auto) and (
                    (info and not info.is_sign) or not get_info_status):
                sign_status = await signer.sign(account.platform)
                if not sign_status:
                    if sign_status.login_expired:
                        message = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{signer.record.region_name}』签到时服务器返回登录失效，请尝试重新登录绑定账户"
                    elif sign_status.need_verify:
                        message = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{signer.record.region_name}』签到时可能遇到验证码拦截，请尝试使用命令『/账号设置』更改设备平台，若仍失败请手动前往米游社签到"
                    else:
                        message = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{signer.record.region_name}』签到失败，请稍后再试"
                    if conf.users[qq].enable_notice or not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True, message=message)
                        else:
                            await bot.send_msg(
                                message_type="private",
                                user_id=qq,
                                message=message
                            )
                    await asyncio.sleep(conf.SLEEP_TIME)
                    continue
                await asyncio.sleep(conf.SLEEP_TIME)
            # 若用户未开启自动签到且手动签到过了，不再提醒
            elif not account.gameSign and is_auto:
                continue

            # 用户打开通知或手动签到时，进行通知
            if conf.users[qq].enable_notice or not is_auto:
                img = ""
                get_info_status, info = await signer.get_info(account.platform)
                get_award_status, awards = await signer.get_rewards()
                if not get_info_status or not get_award_status:
                    msg = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{signer.record.region_name}』获取签到结果失败！请手动前往米游社查看"
                else:
                    award = awards[info.total_sign_day - 1]
                    if info.is_sign:
                        msg = f"""\
                            \n📱账户 {account.phone if not group_event else blur(account.phone)}\
                            \n🎮『{signer.record.region_name}』今日签到成功！\
                            \n{signer.record.nickname}·{signer.record.level}\
                            \n🎁今日签到奖励：\
                            \n{award.name} * {award.cnt}\
                            \n\n📅本月签到次数：{info.total_sign_day}\
                        """.strip()
                        img_file = await get_file(award.icon)
                        img = MessageSegment.image(img_file)
                    else:
                        msg = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{signer.record.region_name}』签到失败！请尝试重新签到，若多次失败请尝试重新登录绑定账户"
                if group_event:
                    await bot.send(event=group_event, at_sender=True, message=msg + img)
                else:
                    await bot.send_msg(
                        message_type="private",
                        user_id=qq,
                        message=msg + img
                    )
            await asyncio.sleep(conf.SLEEP_TIME)

    # 如果全部登录失效，则关闭通知
    if len(failed_accounts) == len(user.accounts):
        user.enable_notice = False
        write_plugin_data()


async def perform_bbs_sign(bot: Bot, qq: int, is_auto: bool,
                           group_event: Union[GroupMessageEvent, PrivateMessageEvent, None] = None):
    """
    执行米游币任务函数，并发送给用户任务执行消息。

    :param bot: Bot实例
    :param qq: 用户QQ号
    :param is_auto: True为当日自动执行任务，False为用户手动调用任务功能
    :param group_event: 若为群消息触发，则为群消息事件，否则为None
    """
    if isinstance(group_event, PrivateMessageEvent):
        group_event = None
    failed_accounts = []
    for account in conf.users[qq].accounts.values():
        for class_name in BaseMission.AVAILABLE_GAMES:
            mission_obj = class_name(account)
            missions_state_status, missions_state = await get_missions_state(account)
            if not missions_state_status:
                if missions_state_status.login_expired:
                    if group_event:
                        await bot.send(event=group_event, at_sender=True,
                                       message=f'⚠️账户 {blur(account.phone)} 登录失效，请重新登录')
                    else:
                        await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                    continue
                if group_event:
                    await bot.send(event=group_event, at_sender=True,
                                   message=f'⚠️账户 {blur(account.phone)} 获取任务完成情况请求失败，你可以手动前往App查看')
                else:
                    await bot.send_private_msg(user_id=qq,
                                               message=f'⚠️账户 {account.phone} 获取任务完成情况请求失败，你可以手动前往App查看')
                continue
            await mission_obj.async_init()
            # 自动执行米游币任务时，要求用户打开了任务功能；手动执行时都可以调用执行。
            if (account.enable_mission and is_auto) or not is_auto:
                if not is_auto:
                    if not group_event:
                        await bot.send_private_msg(user_id=qq, message=f'📱账户 {account.phone} ⏳开始执行米游币任务...')

                # 执行任务
                for mission, current in missions_state.state_dict.items():
                    if current < mission.threshold:
                        if mission.mission_key == BaseMission.SIGN:
                            await mission_obj.sign()
                        elif mission.mission_key == BaseMission.VIEW:
                            await mission_obj.read()
                        elif mission.mission_key == BaseMission.LIKE:
                            await mission_obj.like()
                        elif mission.mission_key == BaseMission.SHARE:
                            await mission_obj.share()


                # 用户打开通知或手动任务时，进行通知
                if conf.users[qq].enable_notice or not is_auto:
                    missions_state_status, missions_state = await get_missions_state(account)
                    if not missions_state_status:
                        if missions_state_status.login_expired:
                            if group_event:
                                await bot.send(event=group_event, at_sender=True,
                                               message=f'⚠️账户 {blur(account.phone)} 登录失效，请重新登录')
                            else:
                                await bot.send_private_msg(user_id=qq,
                                                           message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                            continue
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {blur(account.phone)} 获取任务完成情况请求失败，你可以手动前往App查看')
                        else:
                            await bot.send_private_msg(user_id=qq,
                                                       message=f'⚠️账户 {account.phone} 获取任务完成情况请求失败，你可以手动前往App查看')
                        continue
                    if all(map(lambda x: x[1] >= x[0].threshold, missions_state.state_dict.items())):
                        notice_string = "🎉已完成今日米游币任务"
                    else:
                        notice_string = "⚠️今日米游币任务未全部完成"

                    msg = f"""\
                        \n{notice_string}\
                        \n📱账户 {account.phone if not group_event else blur(account.phone)}\
                        """
                    for mission, current in missions_state.state_dict.items():
                        if mission.mission_key == BaseMission.SIGN:
                            mission_name = "签到"
                        elif mission.mission_key == BaseMission.VIEW:
                            mission_name = "阅读"
                        elif mission.mission_key == BaseMission.LIKE:
                            mission_name = "点赞"
                        elif mission.mission_key == BaseMission.SHARE:
                            mission_name = "转发"
                        else:
                            mission_name = mission.mission_key
                        msg += f"\n- {mission_name} {'✓' if current >= mission.threshold else '✕'}"
                    msg += f"\n💰米游币: {missions_state.current_myb}"

                    if group_event:
                        await bot.send(event=group_event, at_sender=True, message=msg)
                    else:
                        await bot.send_msg(
                            message_type="private",
                            user_id=qq,
                            message=msg
                        )

    # 如果全部登录失效，则关闭通知
    if len(failed_accounts) == len(user.accounts):
        user.enable_notice = False
        write_plugin_data()


async def resin_check(bot: Bot, qq: int, is_auto: bool,
                      group_event: Union[GroupMessageEvent, PrivateMessageEvent, None] = None):
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
    for account in conf.users[qq].accounts.values():
        if account.enable_resin:
            has_checked[account.phone] = has_checked.get(account.phone,
                                                         {"resin": False, "coin": False, "transformer": False})
        if (account.enable_resin and is_auto) or not is_auto:
            genshin_board_status, board = await genshin_board_bbs(account)
            if not genshin_board_status:
                if genshin_board_status.login_expired:
                    if not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {blur(account.phone)} 登录失效，请重新登录')
                        else:
                            await bot.send_private_msg(user_id=qq,
                                                       message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                if genshin_board_status.no_genshin_account:
                    if not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {blur(account.phone)} 没有绑定任何原神账户，请绑定后再重试')
                        else:
                            await bot.send_private_msg(user_id=qq,
                                                       message=f'⚠️账户 {account.phone} 没有绑定任何原神账户，请绑定后再重试')
                        account.enable_resin = False
                        write_plugin_data()
                        continue
                if not is_auto:
                    if group_event:
                        await bot.send(event=group_event, at_sender=True,
                                       message=f'⚠️账户 {blur(account.phone)} 获取实时便笺请求失败，你可以手动前往App查看')
                    else:
                        await bot.send_private_msg(user_id=qq,
                                                   message=f'⚠️账户 {account.phone} 获取实时便笺请求失败，你可以手动前往App查看')
                continue
            msg = ''
            # 手动查询体力时，无需判断是否溢出
            if not is_auto:
                pass
            else:
                # 体力溢出提醒
                if board.current_resin == 160:
                    # 防止重复提醒
                    if has_checked[account.phone]['resin']:
                        return
                    else:
                        has_checked[account.phone]['resin'] = True
                        msg += '❕您的树脂已经满啦\n'
                else:
                    has_checked[account.phone]['resin'] = False
                # 洞天财瓮溢出提醒
                if board.current_home_coin == board.max_home_coin:
                    # 防止重复提醒
                    if has_checked[account.phone]['coin']:
                        return
                    else:
                        has_checked[account.phone]['coin'] = True
                        msg += '❕您的洞天财瓮已经满啦\n'
                else:
                    has_checked[account.phone]['coin'] = False
                # 参量质变仪就绪提醒
                if board.transformer_text == '已准备就绪':
                    # 防止重复提醒
                    if has_checked[account.phone]['transformer']:
                        return
                    else:
                        has_checked[account.phone]['transformer'] = True
                        msg += '❕您的参量质变仪已准备就绪\n\n'
                else:
                    has_checked[account.phone]['transformer'] = False
                    return
            msg += f"""\
            ❖实时便笺❖\
            \n⏳树脂数量：{board.current_resin}/160\
            \n🕰️探索派遣：{board.current_expedition_num}/{board.max_expedition_num}\
            \n📅每日委托：{4 - board.finished_task_num} 个任务未完成\
            \n💰洞天财瓮：{board.current_home_coin}/{board.max_home_coin}\
            \n🎰参量质变仪：{board.transformer_text}
            """.strip()
            if group_event:
                await bot.send(event=group_event, at_sender=True, message=msg)
            else:
                await bot.send_private_msg(user_id=qq, message=msg)


@scheduler.scheduled_job("cron", hour='0', minute='0', id="daily_goodImg_update")
def daily_update():
    """
    每日图片生成函数
    """
    logger.info(f"{conf.preference.log_head}开始生成每日商品图片")
    generate_image()


@scheduler.scheduled_job("cron",
                         hour=conf.preference.plan_time.split(':')[0],
                         minute=conf.preference.plan_time.split(':')[1],
                         id="daily_schedule")
async def daily_schedule():
    """
    自动米游币任务、游戏签到函数
    """
    # 随机延迟
    await asyncio.sleep(random.randint(0, 59))
    logger.info(f"{conf.preference.log_head}开始执行每日自动任务")
    bot = get_bot()
    for qq in conf.users:
        await perform_bbs_sign(bot=bot, qq=qq, is_auto=True)
        await perform_game_sign(bot=bot, qq=qq, is_auto=True)
    logger.info(f"{conf.preference.log_head}每日自动任务执行完成")


@scheduler.scheduled_job("interval",
                         minutes=conf.preference.resin_interval,
                         id="resin_check")
async def auto_resin_check():
    """
    自动查看实时便笺
    """
    bot = get_bot()
    for qq in conf.users:
        await resin_check(bot=bot, qq=qq, is_auto=True)
