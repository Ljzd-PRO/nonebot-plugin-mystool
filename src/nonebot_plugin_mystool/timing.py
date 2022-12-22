"""
### 计划任务相关
"""
import asyncio
import os
import time
from typing import List

from nonebot import get_bot, get_driver, on_command
from nonebot.adapters.onebot.v11 import (Bot, MessageSegment,
                                         PrivateMessageEvent)
from nonebot_plugin_apscheduler import scheduler

from .bbsAPI import GameInfo, GameRecord, genshin_status_bbs, get_game_record
from .config import mysTool_config as conf
from .data import UserData
from .exchange import game_list_to_image, get_good_list
from .gameSign import GameSign, Info
from .mybMission import Action, get_missions_state
from .utils import get_file, logger

driver = get_driver()
COMMAND = list(driver.config.command_start)[0] + conf.COMMAND_START

manually_game_sign = on_command(
    conf.COMMAND_START + 'yssign',
    aliases={conf.COMMAND_START + '签到', conf.COMMAND_START + '手动签到', conf.COMMAND_START + '游戏签到',
             conf.COMMAND_START + '原神签到', conf.COMMAND_START + 'gamesign'}, priority=4, block=True)
manually_game_sign.__help_name__ = '签到'
manually_game_sign.__help_info__ = '手动进行游戏签到，查看本次签到奖励及本月签到天数'


@manually_game_sign.handle()
async def _(event: PrivateMessageEvent):
    """
    手动游戏签到函数
    """
    bot = get_bot(str(event.self_id))
    if not UserData.read_account_all(event.user_id):
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND}{conf.COMMAND_START}登录』进行登录")
    await perform_game_sign(bot=bot, qq=event.user_id, isAuto=False)


manually_bbs_sign = on_command(
    conf.COMMAND_START + '任务',
    aliases={conf.COMMAND_START + '米游社签到', conf.COMMAND_START + '米游币任务', conf.COMMAND_START + '米游币获取',
             conf.COMMAND_START + 'bbssign', conf.COMMAND_START + '米游社任务'}, priority=4, block=True)
manually_bbs_sign.__help_name__ = '任务'
manually_bbs_sign.__help_info__ = '手动执行米游币每日任务，可以查看米游币任务完成情况'


@manually_bbs_sign.handle()
async def _(event: PrivateMessageEvent):
    """
    手动米游币任务函数
    """
    bot = get_bot(str(event.self_id))
    if not UserData.read_account_all(event.user_id):
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND}{conf.COMMAND_START}登录』进行登录")
    await perform_bbs_sign(bot=bot, qq=event.user_id, isAuto=False)


manually_resin_check = on_command(
    conf.COMMAND_START + '树脂',
    aliases={conf.COMMAND_START + '体力', conf.COMMAND_START + '树脂查看', conf.COMMAND_START + '实时便笺',
             conf.COMMAND_START + '便笺', conf.COMMAND_START + '原神便笺'}, priority=4, block=True)
manually_resin_check.__help_name__ = '便笺'
manually_resin_check.__help_info__ = '手动查看原神实时便笺，即原神树脂、洞天财瓮等信息'
HAS_CHECKED = {}
qq_accounts = UserData.read_all().keys()
for qq in qq_accounts:
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        if account.checkResin:
            HAS_CHECKED[account.phone] = HAS_CHECKED.get(account.phone,
                                                         {"resin": False, "coin": False, "transformer": False})


@manually_resin_check.handle()
async def _(event: PrivateMessageEvent):
    """
    手动查看原神便笺
    """
    bot = get_bot(str(event.self_id))
    if not UserData.read_account_all(event.user_id):
        await manually_game_sign.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND}{conf.COMMAND_START}登录』进行登录")
    await resin_check(bot=bot, qq=event.user_id, isAuto=False)


async def perform_game_sign(bot: Bot, qq: int, isAuto: bool):
    """
    执行游戏签到函数，并发送给用户签到消息。

    :param isAuto: `True`为当日自动签到，`False`为用户手动调用签到功能
    """
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        gamesign = GameSign(account)
        record_list: List[GameRecord] = await get_game_record(account)
        if isinstance(record_list, int):
            if record_list == -1:
                await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 登录失效，请重新登录")
                continue
            else:
                await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 获取游戏账号信息失败，请重新尝试")
                continue
        if not record_list and not isAuto:
            await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 没有绑定任何游戏账号，跳过游戏签到")
            continue
        for record in record_list:
            if GameInfo.ABBR_TO_ID[record.gameID][0] not in GameSign.SUPPORTED_GAMES:
                logger.info("{0}执行游戏签到 - {1} 暂不支持".format(conf.LOG_HEAD,
                                                          GameInfo.ABBR_TO_ID[record.gameID][1]))
                continue
            else:
                sign_game = GameInfo.ABBR_TO_ID[record.gameID][0]
                sign_info = await gamesign.info(sign_game, record.uid)
                game_name = GameInfo.ABBR_TO_ID[record.gameID][1]

                if sign_info == -1:
                    await bot.send_private_msg(user_id=qq, message=f"⚠️账户 {account.phone} 登录失效，请重新登录")
                    continue

                # 自动签到时，要求用户打开了签到功能；手动签到时都可以调用执行。若没签到，则进行签到功能。
                # 若获取今日签到情况失败，但不是登录失效的情况，仍可继续
                if ((account.gameSign and isAuto) or not isAuto) and (
                        (isinstance(sign_info, Info) and not sign_info.isSign) or (
                        isinstance(sign_info, int) and sign_info != -1)):
                    sign_flag = await gamesign.sign(sign_game, record.uid, account.platform)
                    if sign_flag != 1:
                        if sign_flag == -1:
                            message = "⚠️账户 {0} 🎮『{1}』签到时服务器返回登录失效，请尝试重新登录绑定账户".format(
                                account.phone, game_name)
                        elif sign_flag == -5:
                            message = "⚠️账户 {0} 🎮『{1}』签到时可能遇到验证码拦截，请尝试使用命令『/账户设置』更改设备平台，若仍失败请手动前往米游社签到".format(
                                account.phone, game_name)
                        else:
                            message = "⚠️账户 {0} 🎮『{1}』签到失败，请稍后再试".format(
                                account.phone, game_name)
                        if UserData.isNotice(qq):
                            await bot.send_msg(
                                message_type="private",
                                user_id=qq,
                                message=message
                            )
                        await asyncio.sleep(conf.SLEEP_TIME)
                        continue
                    await asyncio.sleep(conf.SLEEP_TIME)
                elif isinstance(sign_info, int):
                    if UserData.isNotice(qq) or not isAuto:
                        await bot.send_private_msg(user_id=qq, message="账户 {0} 🎮『{1}』已尝试签到，但获取签到结果失败".format(
                            account.phone, game_name))
                        continue
                # 若用户未开启自动签到且手动签到过了，不再提醒
                elif not account.gameSign and isAuto:
                    continue

                # 用户打开通知或手动签到时，进行通知
                if UserData.isNotice(qq) or not isAuto:
                    img = ""
                    sign_info = await gamesign.info(sign_game, record.uid)
                    month_sign_award = await gamesign.reward(sign_game)
                    if isinstance(sign_info, int) or isinstance(month_sign_award, int):
                        msg = "⚠️账户 {0} 🎮『{1}』获取签到结果失败！请手动前往米游社查看".format(
                            account.phone, game_name)
                    else:
                        sign_award = month_sign_award[sign_info.totalDays - 1]
                        if sign_info.isSign:
                            msg = f"""\
                                \n📱账户 {account.phone}\
                                \n🎮『{game_name}』今日签到成功！\
                                \n{record.nickname}·{record.regionName}·{record.level}\
                                \n🎁今日签到奖励：\
                                \n{sign_award.name} * {sign_award.count}\
                                \n\n📅本月签到次数：{sign_info.totalDays}\
                            """.strip()
                            img_file = await get_file(sign_award.icon)
                            img = MessageSegment.image(img_file)
                        else:
                            msg = "⚠️账户 {0} 🎮『{1}』签到失败！请尝试重新签到，若多次失败请尝试重新登录绑定账户".format(
                                account.phone, game_name)
                    await bot.send_msg(
                        message_type="private",
                        user_id=qq,
                        message=msg + img
                    )
                await asyncio.sleep(conf.SLEEP_TIME)


async def perform_bbs_sign(bot: Bot, qq: int, isAuto: bool):
    """
    执行米游币任务函数，并发送给用户任务执行消息。

    :param isAuto: True为当日自动执行任务，False为用户手动调用任务功能
    """
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        missions_state = await get_missions_state(account)
        mybmission = await Action(account).async_init()
        if isinstance(missions_state, int):
            if mybmission == -1:
                await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                continue
            await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 获取任务完成情况请求失败，你可以手动前往App查看')
            continue
        if isinstance(mybmission, int):
            if mybmission == -1:
                await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                continue
            await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 请求失败，请重新尝试')
            continue
        # 自动执行米游币任务时，要求用户打开了任务功能；手动执行时都可以调用执行。
        if (account.mybMission and isAuto) or not isAuto:
            if not isAuto:
                await bot.send_private_msg(user_id=qq, message=f'📱账户 {account.phone} ⏳开始执行米游币任务...')

            # 执行任务
            for mission_state in missions_state[0]:
                if mission_state[1] < mission_state[0].totalTimes:
                    for gameID in account.missionGame:
                        await mybmission.NAME_TO_FUNC[mission_state[0].keyName](mybmission, gameID)
                        await asyncio.sleep(conf.SLEEP_TIME)

            # 用户打开通知或手动任务时，进行通知
            if UserData.isNotice(qq) or not isAuto:
                missions_state = await get_missions_state(account)
                if isinstance(missions_state, int):
                    if mybmission == -1:
                        await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                        continue
                    await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 获取任务完成情况请求失败，你可以手动前往App查看')
                    continue
                if missions_state[0][0][1] >= missions_state[0][0][0].totalTimes and \
                        missions_state[0][1][1] >= missions_state[0][1][0].totalTimes and \
                        missions_state[0][2][1] >= missions_state[0][2][0].totalTimes and \
                        missions_state[0][3][1] >= missions_state[0][3][0].totalTimes:
                    notice_string = "🎉已完成今日米游币任务"
                else:
                    notice_string = "⚠️今日米游币任务未全部完成"
                msg = f"""\
                    \n{notice_string}\
                    \n📱账户 {account.phone}\
                    \n- 签到 {'✓' if missions_state[0][0][1] >= missions_state[0][0][0].totalTimes else '✕'}\
                    \n- 阅读 {'✓' if missions_state[0][1][1] >= missions_state[0][1][0].totalTimes else '✕'}\
                    \n- 点赞 {'✓' if missions_state[0][2][1] >= missions_state[0][2][0].totalTimes else '✕'}\
                    \n- 转发 {'✓' if missions_state[0][3][1] >= missions_state[0][3][0].totalTimes else '✕'}\
                \n💰米游币: {missions_state[1]}
                """.strip()
                await bot.send_msg(
                    message_type="private",
                    user_id=qq,
                    message=msg
                )


async def resin_check(bot: Bot, qq: int, isAuto: bool):
    """
    查看原神实时便笺函数，并发送给用户任务执行消息。

    :param isAuto: True为自动检查，False为用户手动调用该功能
    """
    global HAS_CHECKED
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        if account.checkResin:
            HAS_CHECKED[account.phone] = HAS_CHECKED.get(account.phone,
                                                         {"resin": False, "coin": False, "transformer": False})
        if (account.checkResin and isAuto) or not isAuto:
            genshinstatus = await genshin_status_bbs(account)
            if isinstance(genshinstatus, int):
                if genshinstatus == -1:
                    if not isAuto:
                        await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 登录失效，请重新登录')
                if genshinstatus == -4:
                    if not isAuto:
                        await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 没有绑定任何原神账户，请绑定后再重试')
                        account.checkResin = False
                        UserData.set_account(account, qq, account.phone)
                        continue
                if not isAuto:
                    await bot.send_private_msg(user_id=qq, message=f'⚠️账户 {account.phone} 获取实时便笺请求失败，你可以手动前往App查看')
                continue
            msg = ''
            # 手动查询体力时，无需判断是否溢出
            if not isAuto:
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
            await bot.send_private_msg(user_id=qq, message=msg)


async def generate_image(isAuto=True):
    """
    生成米游币商品函数。

    :param isAuto: True为每日自动生成，False为用户手动更新
    """
    for root, _, files in os.walk(conf.goodListImage.SAVE_PATH, topdown=False):
        for name in files:
            date = time.strftime('%m-%d', time.localtime())
            # 若图片开头为当日日期，则退出函数不执行
            if name.startswith(date):
                if isAuto:
                    return
            # 删除旧图片，以方便生成当日图片
            if name.endswith('.jpg'):
                os.remove(os.path.join(root, name))
    for game in ("bh3", "ys", "bh2", "wd", "bbs"):
        good_list = await get_good_list(game)
        if good_list:
            img_path = time.strftime(
                f'{conf.goodListImage.SAVE_PATH}/%m-%d-{game}.jpg', time.localtime())
            image_bytes = await game_list_to_image(good_list)
            if not image_bytes:
                return
            with open(img_path, 'wb') as fp:
                fp.write(image_bytes)
        else:
            logger.info(f"{conf.LOG_HEAD}{game}分区暂时没有商品，跳过生成...")


@scheduler.scheduled_job("cron", hour='0', minute='0', id="daily_goodImg_update")
async def daily_update():
    """
    每日图片生成函数
    """
    logger.info(f"{conf.LOG_HEAD}开始生成每日商品图片")
    await generate_image()


@scheduler.scheduled_job("cron", hour=conf.SIGN_TIME.split(':')[0],
                         minute=conf.SIGN_TIME.split(':')[1], id="daily_schedule")
async def daily_schedule():
    """
    自动米游币任务、游戏签到函数
    """
    logger.info(f"{conf.LOG_HEAD}开始执行每日自动任务")
    qq_accounts = UserData.read_all().keys()
    bot = get_bot()
    for qq in qq_accounts:
        await perform_bbs_sign(bot=bot, qq=qq, isAuto=True)
        await perform_game_sign(bot=bot, qq=qq, isAuto=True)
    logger.info(f"{conf.LOG_HEAD}每日自动任务执行完成")


@scheduler.scheduled_job("interval", minutes=conf.RESIN_CHECK_INTERVAL, id="resin_check")
async def auto_resin_check():
    """
    自动查看实时便笺
    """
    qq_accounts = UserData.read_all().keys()
    bot = get_bot()
    for qq in qq_accounts:
        await resin_check(bot=bot, qq=qq, isAuto=True)


# 启动时，自动生成当日米游社商品图片
driver.on_startup(generate_image)
