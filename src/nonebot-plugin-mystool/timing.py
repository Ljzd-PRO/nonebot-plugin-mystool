"""
### 计划任务相关
"""
import asyncio
import os
import time
from typing import List

import nonebot_plugin_apscheduler
from nonebot import get_bot, get_driver, on_command
from nonebot.adapters.onebot.v11 import (Bot, MessageSegment,
                                         PrivateMessageEvent)
from nonebot.params import T_State
from nonebot.permission import SUPERUSER

from .bbsAPI import *
from .config import mysTool_config as conf
from .data import UserData
from .exchange import *
from .gameSign import *
from .mybMission import *
from .utils import *

driver = nonebot.get_driver()

daily_game_sign = nonebot_plugin_apscheduler.scheduler


@daily_game_sign.scheduled_job("cron", hour='0', minute='00', id="daily_game_sign")
async def daily_game_sign_():
    bot = get_bot()
    qq_accounts = UserData.read_all().keys()
    for qq in qq_accounts:
        await send_game_sign_msg(bot=bot, qq=qq, IsAuto=True)


manually_game_sign = on_command(
    conf.COMMAND_START+'yssign', aliases={conf.COMMAND_START+'签到', conf.COMMAND_START+'手动签到', conf.COMMAND_START+'游戏签到', conf.COMMAND_START+'原神签到', conf.COMMAND_START+'gamesign'}, priority=4, block=True)
manually_game_sign.__help_name__ = '游戏签到'
manually_game_sign.__help_info__ = '手动进行游戏签到，查看本次签到奖励及本月签到天数'


@manually_game_sign.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    bot = get_bot()
    qq = event.user_id
    await send_game_sign_msg(bot=bot, qq=qq, IsAuto=False)


daily_bbs_sign = nonebot_plugin_apscheduler.scheduler


@daily_bbs_sign.scheduled_job("cron", hour='0', minute='00', id="daily_bbs_sign")
async def daily_bbs_sign_():
    qq_accounts = UserData.read_all().keys()
    bot = get_bot()
    for qq in qq_accounts:
        await send_bbs_sign_msg(bot=bot, qq=qq, IsAuto=True)


manually_bbs_sign = on_command(
    conf.COMMAND_START+'bbs_sign', aliases={conf.COMMAND_START+'米游社签到', conf.COMMAND_START+'米游社任务', conf.COMMAND_START+'米游币获取', conf.COMMAND_START+'bbssign'}, priority=4, block=True)
manually_bbs_sign.__help_name__ = '米游社任务'
manually_bbs_sign.__help_info__ = '手动进行米游社每日任务，可以查看米游社任务完成情况'


@manually_bbs_sign.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    qq = event.user_id
    bot = get_bot()
    await send_bbs_sign_msg(bot=bot, qq=qq, IsAuto=False)


update_timing = nonebot_plugin_apscheduler.scheduler


@update_timing.scheduled_job("cron", hour='0', minute='00', id="daily_update")
async def daily_update():
    generate_image()


async def send_game_sign_msg(bot: Bot, qq: str, IsAuto: bool):
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        gamesign = GameSign(account)
        record_list: List[GameRecord] = await get_game_record(account)
        if isinstance(record_list, int):
            if record_list == -1:
                await bot.send_private_msg(user_id=qq, message=f"账户{account.phone}登录失效，请重新登录")
                return
            else:
                await bot.send_private_msg(user_id=qq, message="请求失败，请重新尝试")
                return
        for record in record_list:
            if GameInfo.ABBR_TO_ID[record.gameID][0] not in GameSign.SUPPORTED_GAMES:
                logger.info(
                    conf.LOG_HEAD + "执行游戏签到 - {} 暂不支持".format(GameInfo.ABBR_TO_ID[record.gameID][1]))
                continue
            else:
                sign_game = GameInfo.ABBR_TO_ID[record.gameID][0]
                sign_info = await gamesign.info(sign_game, record.uid)
                sign_game_name = GameInfo.ABBR_TO_ID[record.gameID][1]
                if ((account.gameSign and IsAuto) or not IsAuto) and not sign_info.isSign:
                    sign_flag = await gamesign.sign(sign_game, record.uid)
                    if isinstance(sign_flag, int):
                        await bot.send_msg(
                            message_type="private",
                            user_id=qq,
                            message=f"今日{sign_game_name}签到失败！请尝试重新签到，若多次失败请尝试重新配置cookie"
                        )
                        continue
                elif sign_info.isSign:
                    pass
                else:
                    return
                if UserData.isNotice(qq):
                    sign_info = await gamesign.info(sign_game, record.uid)
                    month_sign_award = await gamesign.reward(sign_game)
                    sign_award = month_sign_award[sign_info.totalDays-1]
                    account_info = record
                    if sign_award and sign_info:
                        msg = f"""\
                            \n{'🎮{}今日签到成功！'.format(sign_game_name) if not sign_info.isSign else '🎮{}今日已签到！'.format(sign_game_name)}\
                            \n{account_info.nickname}-{account_info.regionName}-{account_info.level}\
                            \n🎁今日签到奖励：\
                            \n  {sign_award.name} * {sign_award.count}\
                            \n📅本月签到次数：{sign_info.totalDays}\
                        """.strip()
                        img_file = await get_file(sign_award.icon)
                        img = MessageSegment.image(img_file)
                    else:
                        msg = f"今日{sign_game_name}签到失败！请尝试重新签到，若多次失败请尝试重新配置cookie"
                        img = ''
                    await bot.send_msg(
                        message_type="private",
                        user_id=qq,
                        message=msg + img
                    )
                await asyncio.sleep(conf.SLEEP_TIME)


async def send_bbs_sign_msg(bot: Bot, qq: str, IsAuto: bool):
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        missions_state = await get_missions_state(account)
        mybmission = Action(account)
        if isinstance(missions_state, int):
            if mybmission == -1:
                await bot.send_private_msg(user_id=qq, message=f'账户{account.phone}登录失效，请重新登录')
            await bot.send_private_msg(user_id=qq, message='请求失败，请重新尝试')
            return
        if isinstance(mybmission, int):
            if mybmission == -1:
                await bot.send_private_msg(user_id=qq, message=f'账户{account.phone}登录失效，请重新登录')
            await bot.send_private_msg(user_id=qq, message='请求失败，请重新尝试')
            return
        if (account.mybMission and IsAuto) or not IsAuto:
            for mission_state in missions_state[0]:
                if mission_state[1] < mission_state[0].totalTimes:
                    mybmission.NAME_TO_FUNC[mission_state.keyName](mybmission)
            if UserData.isNotice(qq):
                missions_state = await get_missions_state(account)
                msg = f"""\
                    \n今日米游币任务执行完成！\
                    \n执行结果：\
                    \n签到： {'√' if missions_state[0][0][1] >= missions_state[0][0][0].totalTimes else '×'}\
                    \n阅读： {'√' if missions_state[0][1][1] >= missions_state[0][1][0].totalTimes else '×'}\
                    \n点赞： {'√' if missions_state[0][2][1] >= missions_state[0][2][0].totalTimes else '×'}\
                    \n签到： {'√' if missions_state[0][3][1] >= missions_state[0][3][0].totalTimes else '×'}\
                \n💰米游币:{missions_state[1]}
                """.strip()
                await bot.send_msg(
                    message_type="private",
                    user_id=qq,
                    message=msg
                )
            await asyncio.sleep(conf.SLEEP_TIME)


async def generate_image():
    for root, dirs, files in os.walk(conf.goodListImage.SAVE_PATH, topdown=False):
        for name in files:
            date = time.strftime('%m-%d', time.localtime())
            if name.startswith(date):
                return
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


driver.on_startup(generate_image)
