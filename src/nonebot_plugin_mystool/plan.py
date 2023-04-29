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

from .bbsAPI import GameInfo, GameRecord, genshin_status_bbs, get_game_record
from .config import config as conf
from .data import UserData
from .exchangePlan import generate_image
from .gameSign import GameSign, Info
from .mybMission import Action, get_missions_state
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
    if not UserData.read_account_all(event.user_id):
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    await perform_game_sign(bot=bot, qq=event.user_id, is_auto=False, group_event=event)


manually_bbs_sign = on_command(conf.COMMAND_START + '任务', priority=5, block=True)
manually_bbs_sign.name = '任务'
manually_bbs_sign.usage = '手动执行米游币每日任务，可以查看米游币任务完成情况'


@manually_bbs_sign.handle()
async def _(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    """
    手动米游币任务函数
    """
    bot = get_bot(str(event.self_id))
    if not UserData.read_account_all(event.user_id):
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    await perform_bbs_sign(bot=bot, qq=event.user_id, is_auto=False, group_event=event)


manually_resin_check = on_command(conf.COMMAND_START + '便笺', priority=5, block=True)
manually_resin_check.name = '便笺'
manually_resin_check.usage = '手动查看原神实时便笺，即原神树脂、洞天财瓮等信息'
HAS_CHECKED = {}
qq_accounts = UserData.read_all().keys()
for qq in qq_accounts:
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        if account.checkResin:
            HAS_CHECKED[account.phone] = HAS_CHECKED.get(account.phone,
                                                         {"resin": False, "coin": False, "transformer": False})


@manually_resin_check.handle()
async def _(event: Union[PrivateMessageEvent, GroupMessageEvent]):
    """
    手动查看原神便笺
    """
    bot = get_bot(str(event.self_id))
    if not UserData.read_account_all(event.user_id):
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
    accounts = UserData.read_account_all(qq)
    failed_accounts = []
    for account in accounts:
        gamesign = GameSign(account)
        record_list: List[GameRecord] = await get_game_record(account)
        if isinstance(record_list, int):
            if record_list == -1:
                failed_accounts.append(account)
                if group_event:
                    await bot.send(event=group_event, at_sender=True, message=f"⚠️账户 {blur(account.phone)} 登录失效，请重新登录")
                else:
                    await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 登录失效，请重新登录")
                continue
            else:
                if group_event:
                    await bot.send(event=group_event, at_sender=True,
                                   message=f"⚠️账户 {blur(account.phone)} 获取游戏账号信息失败，请重新尝试")
                else:
                    await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 获取游戏账号信息失败，请重新尝试")
                continue
        if not record_list and not is_auto:
            if group_event:
                await bot.send(event=group_event, at_sender=True,
                               message=f"⚠️账户 {blur(account.phone)} 没有绑定任何游戏账号，跳过游戏签到")
            else:
                await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 没有绑定任何游戏账号，跳过游戏签到")
            continue
        for record in record_list:
            if GameInfo.ABBR_TO_ID[record.game_id][0] not in GameSign.SUPPORTED_GAMES:
                logger.info(f"{conf.LOG_HEAD}执行游戏签到 - {GameInfo.ABBR_TO_ID[record.game_id][1]} 暂不支持")
                continue
            else:
                sign_game = GameInfo.ABBR_TO_ID[record.game_id][0]
                sign_info = await gamesign.info(sign_game, record.uid)
                game_name = GameInfo.ABBR_TO_ID[record.game_id][1]

                if sign_info == -1:
                    if group_event:
                        await bot.send(event=group_event, at_sender=True,
                                       message=f"⚠️账户 {blur(account.phone)} 登录失效，请重新登录")
                    else:
                        await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 登录失效，请重新登录")
                    continue

                # 自动签到时，要求用户打开了签到功能；手动签到时都可以调用执行。若没签到，则进行签到功能。
                # 若获取今日签到情况失败，但不是登录失效的情况，仍可继续
                if ((account.gameSign and is_auto) or not is_auto) and (
                        (isinstance(sign_info, Info) and not sign_info.is_sign) or (
                        isinstance(sign_info, int) and sign_info != -1)):
                    sign_flag = await gamesign.sign(sign_game, record.uid, account.platform)
                    if sign_flag != 1:
                        if sign_flag == -1:
                            message = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{game_name}』签到时服务器返回登录失效，请尝试重新登录绑定账户"
                        elif sign_flag == -5:
                            message = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{game_name}』签到时可能遇到验证码拦截，请尝试使用命令『/账号设置』更改设备平台，若仍失败请手动前往米游社签到"
                        else:
                            message = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{game_name}』签到失败，请稍后再试"
                        if UserData.is_notice(qq) or not is_auto:
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
                elif isinstance(sign_info, int):
                    if UserData.is_notice(qq) or not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f"账户 {blur(account.phone)} 🎮『{game_name}』已尝试签到，但获取签到结果失败")
                        else:
                            await bot.send_private_msg(user_id=qq,
                                                       message=f"账户 {account.phone} 🎮『{game_name}』已尝试签到，但获取签到结果失败")
                        continue
                # 若用户未开启自动签到且手动签到过了，不再提醒
                elif not account.gameSign and is_auto:
                    continue

                # 用户打开通知或手动签到时，进行通知
                if UserData.is_notice(qq) or not is_auto:
                    img = ""
                    sign_info = await gamesign.info(sign_game, record.uid)
                    month_sign_award = await gamesign.reward(sign_game)
                    if isinstance(sign_info, int) or isinstance(month_sign_award, int):
                        msg = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{game_name}』获取签到结果失败！请手动前往米游社查看"
                    else:
                        sign_award = month_sign_award[sign_info.total_days - 1]
                        if sign_info.is_sign:
                            msg = f"""\
                                \n📱账户 {account.phone if not group_event else blur(account.phone)}\
                                \n🎮『{game_name}』今日签到成功！\
                                \n{record.nickname}·{record.region_name}·{record.level}\
                                \n🎁今日签到奖励：\
                                \n{sign_award.name} * {sign_award.count}\
                                \n\n📅本月签到次数：{sign_info.total_days}\
                            """.strip()
                            img_file = await get_file(sign_award.icon)
                            img = MessageSegment.image(img_file)
                        else:
                            msg = f"⚠️账户 {account.phone if not group_event else blur(account.phone)} 🎮『{game_name}』签到失败！请尝试重新签到，若多次失败请尝试重新登录绑定账户"
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
    if len(failed_accounts) == len(accounts):
        UserData.set_notice(False, qq)


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
    accounts = UserData.read_account_all(qq)
    failed_accounts = []
    for account in accounts:
        missions_state = await get_missions_state(account)
        mybmission = await Action(account).async_init()
        if isinstance(missions_state, int):
            if mybmission == -1:
                if group_event:
                    await bot.send(event=group_event, at_sender=True, message=f'⚠️账户 {blur(account.phone)} 登录失效，请重新登录')
                else:
                    await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                continue
            if group_event:
                await bot.send(event=group_event, at_sender=True,
                               message=f'⚠️账户 {blur(account.phone)} 获取任务完成情况请求失败，你可以手动前往App查看')
            else:
                await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 获取任务完成情况请求失败，你可以手动前往App查看')
            continue
        if isinstance(mybmission, int):
            if mybmission == -1:
                failed_accounts.append(account)
                if group_event:
                    await bot.send(event=group_event, at_sender=True, message=f'⚠️账户 {blur(account.phone)} 登录失效，请重新登录')
                else:
                    await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                continue
            if group_event:
                await bot.send(event=group_event, at_sender=True, message=f'⚠️账户 {blur(account.phone)} 请求失败，请重新尝试')
            else:
                await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 请求失败，请重新尝试')
            continue
        # 自动执行米游币任务时，要求用户打开了任务功能；手动执行时都可以调用执行。
        if (account.mybMission and is_auto) or not is_auto:
            if not is_auto:
                if not group_event:
                    await bot.send_private_msg(user_id=qq, message=f'📱账户 {account.phone} ⏳开始执行米游币任务...')

            # 执行任务
            for mission_state in missions_state[0]:
                if mission_state[1] < mission_state[0].total_times:
                    for gameID in account.missionGame:
                        await mybmission.NAME_TO_FUNC[mission_state[0].key_name](mybmission, gameID)
                        await asyncio.sleep(conf.SLEEP_TIME)

            # 用户打开通知或手动任务时，进行通知
            if UserData.is_notice(qq) or not is_auto:
                missions_state = await get_missions_state(account)
                if isinstance(missions_state, int):
                    if mybmission == -1:
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
                if missions_state[0][0][1] >= missions_state[0][0][0].total_times and \
                        missions_state[0][1][1] >= missions_state[0][1][0].total_times and \
                        missions_state[0][2][1] >= missions_state[0][2][0].total_times and \
                        missions_state[0][3][1] >= missions_state[0][3][0].total_times:
                    notice_string = "🎉已完成今日米游币任务"
                else:
                    notice_string = "⚠️今日米游币任务未全部完成"
                msg = f"""\
                    \n{notice_string}\
                    \n📱账户 {account.phone if not group_event else blur(account.phone)}\
                    \n- 签到 {'✓' if missions_state[0][0][1] >= missions_state[0][0][0].total_times else '✕'}\
                    \n- 阅读 {'✓' if missions_state[0][1][1] >= missions_state[0][1][0].total_times else '✕'}\
                    \n- 点赞 {'✓' if missions_state[0][2][1] >= missions_state[0][2][0].total_times else '✕'}\
                    \n- 转发 {'✓' if missions_state[0][3][1] >= missions_state[0][3][0].total_times else '✕'}\
                \n💰米游币: {missions_state[1]}
                """.strip()
                if group_event:
                    await bot.send(event=group_event, at_sender=True, message=msg)
                else:
                    await bot.send_msg(
                        message_type="private",
                        user_id=qq,
                        message=msg
                    )

    # 如果全部登录失效，则关闭通知
    if len(failed_accounts) == len(accounts):
        UserData.set_notice(False, qq)


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
    global HAS_CHECKED
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        if account.checkResin:
            HAS_CHECKED[account.phone] = HAS_CHECKED.get(account.phone,
                                                         {"resin": False, "coin": False, "transformer": False})
        if (account.checkResin and is_auto) or not is_auto:
            genshinstatus = await genshin_status_bbs(account)
            if isinstance(genshinstatus, int):
                if genshinstatus == -1:
                    if not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {blur(account.phone)} 登录失效，请重新登录')
                        else:
                            await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                if genshinstatus == -4:
                    if not is_auto:
                        if group_event:
                            await bot.send(event=group_event, at_sender=True,
                                           message=f'⚠️账户 {blur(account.phone)} 没有绑定任何原神账户，请绑定后再重试')
                        else:
                            await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 没有绑定任何原神账户，请绑定后再重试')
                        account.checkResin = False
                        UserData.set_account(account, qq, account.phone)
                        continue
                if not is_auto:
                    if group_event:
                        await bot.send(event=group_event, at_sender=True,
                                       message=f'⚠️账户 {blur(account.phone)} 获取实时便笺请求失败，你可以手动前往App查看')
                    else:
                        await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 获取实时便笺请求失败，你可以手动前往App查看')
                continue
            msg = ''
            # 手动查询体力时，无需判断是否溢出
            if not is_auto:
                pass
            else:
                # 体力溢出提醒
                if genshinstatus.resin == 160:
                    # 防止重复提醒
                    if HAS_CHECKED[account.phone]['resin']:
                        return
                    else:
                        HAS_CHECKED[account.phone]['resin'] = True
                        msg += '❕您的树脂已经满啦\n'
                else:
                    HAS_CHECKED[account.phone]['resin'] = False
                # 洞天财瓮溢出提醒
                if genshinstatus.coin[0] == genshinstatus.coin[1]:
                    # 防止重复提醒
                    if HAS_CHECKED[account.phone]['coin']:
                        return
                    else:
                        HAS_CHECKED[account.phone]['coin'] = True
                        msg += '❕您的洞天财瓮已经满啦\n'
                else:
                    HAS_CHECKED[account.phone]['coin'] = False
                # 参量质变仪就绪提醒
                if genshinstatus.transformer == '已准备就绪':
                    # 防止重复提醒
                    if HAS_CHECKED[account.phone]['transformer']:
                        return
                    else:
                        HAS_CHECKED[account.phone]['transformer'] = True
                        msg += '❕您的参量质变仪已准备就绪\n\n'
                else:
                    HAS_CHECKED[account.phone]['transformer'] = False
                    return
            msg += f"""\
            ❖实时便笺❖\
            \n🎮{genshinstatus.name}·{genshinstatus.level}\
            \n⏳树脂数量：{genshinstatus.resin}/160\
            \n🕰️探索派遣：{genshinstatus.expedition[0]}/{genshinstatus.expedition[1]}\
            \n📅每日委托：{4 - genshinstatus.task} 个任务未完成\
            \n💰洞天财瓮：{genshinstatus.coin[0]}/{genshinstatus.coin[1]}\
            \n🎰参量质变仪：{genshinstatus.transformer}
            """.strip()
            if group_event:
                await bot.send(event=group_event, at_sender=True, message=msg)
            else:
                await bot.send_private_msg(user_id=qq, message=msg)


@scheduler.scheduled_job("cron", hour='0', minute='0', id="daily_goodImg_update")
async def daily_update():
    """
    每日图片生成函数
    """
    logger.info(f"{conf.LOG_HEAD}开始生成每日商品图片")
    await generate_image()


@scheduler.scheduled_job("cron",
                         hour=conf.SIGN_TIME.split(':')[0],
                         minute=conf.SIGN_TIME.split(':')[1],
                         id="daily_schedule")
async def daily_schedule():
    """
    自动米游币任务、游戏签到函数
    """
    # 随机延迟
    await asyncio.sleep(random.randint(0, 59))
    logger.info(f"{conf.LOG_HEAD}开始执行每日自动任务")
    qq_accounts = UserData.read_all().keys()
    bot = get_bot()
    for qq in qq_accounts:
        await perform_bbs_sign(bot=bot, qq=qq, is_auto=True)
        await perform_game_sign(bot=bot, qq=qq, is_auto=True)
    logger.info(f"{conf.LOG_HEAD}每日自动任务执行完成")


@scheduler.scheduled_job("interval",
                         minutes=conf.RESIN_CHECK_INTERVAL,
                         id="resin_check")
async def auto_resin_check():
    """
    自动查看实时便笺
    """
    qq_accounts = UserData.read_all().keys()
    bot = get_bot()
    for qq in qq_accounts:
        await resin_check(bot=bot, qq=qq, is_auto=True)
