"""
### 计划任务相关
"""
from nonebot import get_driver, get_bot, on_command
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent, MessageSegment
from nonebot.params import T_State
from nonebot import on_command, get_bot
from nonebot.permission import SUPERUSER
import nonebot_plugin_apscheduler
import asyncio
import time
import os
from .data import UserData
from .bbsAPI import *
from .gameSign import *
from .config import mysTool_config as conf
from .config import img_config as img_conf
from .utils import *
from .mybMission import Mission
from .exchange import *

driver = nonebot.get_driver()


__cs = ''
if conf.USE_COMMAND_START:
    __cs = conf.COMMAND_START

daily_game_sign = nonebot_plugin_apscheduler.scheduler

@daily_game_sign.scheduled_job("cron", hour='0', minute='00', id="daily_game_sign")

async def daily_game_sign_():
    bot = get_bot()
    qq_accounts = UserData.read_all().keys()
    for qq in qq_accounts:
        await send_game_sign_msg(bot=bot, qq=qq)


manually_game_sign = on_command(
    __cs+'yssign', aliases={__cs+'签到', __cs+'手动签到', __cs+'游戏签到', __cs+'原神签到', __cs+'gamesign'}, priority=4, block=True)
manually_game_sign.__help_name__ = '游戏签到'
manually_game_sign.__help_info__ = '手动进行游戏签到，查看本次签到奖励及本月签到天数'

@manually_game_sign.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    bot = get_bot()
    qq = event.user_id
    await send_game_sign_msg(bot=bot, qq=qq)


daily_bbs_sign = nonebot_plugin_apscheduler.scheduler

@daily_bbs_sign.scheduled_job("cron", hour='0', minute='00', id="daily_bbs_sign")
async def daily_bbs_sign_():
    qq_accounts = UserData.read_all().keys()
    bot = get_bot()
    for qq in qq_accounts:
        await send_bbs_sign_msg(bot=bot, qq=qq)


manually_bbs_sign = on_command(
    __cs+'bbs_sign', aliases={__cs+'米游社签到', __cs+'米游社任务', __cs+'米游币获取', __cs+'bbssign'}, priority=4, block=True)
manually_bbs_sign.__help_name__ = '米游社任务'
manually_bbs_sign.__help_info__ = '手动进行米游社每日任务，可以查看米游社任务完成情况'

@manually_bbs_sign.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    qq = event.user_id
    bot = get_bot()
    await send_bbs_sign_msg(bot=bot, qq=qq)


update_timing = nonebot_plugin_apscheduler.scheduler

@update_timing.scheduled_job("cron", hour='0', minute='00', id="daily_update")
async def daily_update():
    generate_image()



async def send_game_sign_msg(bot: Bot, qq: str):
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        gamesign = GameSign(account)
        record_list: list[GameRecord] = await get_game_record(account)
        for record in record_list:
            if GameInfo.ABBR_TO_ID[record.gameID][0] not in GameSign.SUPPORTED_GAMES:
                logger.info(conf.LOG_HEAD + "执行游戏签到 - {} 暂不支持".format(GameInfo.ABBR_TO_ID[record.gameID][1]))
                continue
            else:
                sign_game = GameInfo.ABBR_TO_ID[record.gameID][0]
                sign_game_name = GameInfo.ABBR_TO_ID[record.gameID][1]
                if account.gameSign:
                    sign_flag = await gamesign.sign(sign_game)
                else:
                    return
                if not sign_flag:
                    await bot.send_msg(
                        message_type="private",
                        user_id=qq,
                        message=f"今日{sign_game_name}签到失败！请尝试重新签到，若多次失败请尝试重新配置cookie"
                    )
                    continue
                if UserData.isNotice(qq):
                    sign_award = await gamesign.reward(sign_game)
                    sign_info = await gamesign.info(sign_game)
                    account_info = record
                    if sign_award and sign_info:
                        msg = f"""\
                            {'今日{sign_game_name}签到成功！' if sign_info.isSign else '今日已签到！'}
                            {account_info.nickname} {account_info.regionName} {account_info.level}
                            今日签到奖励：
                            {sign_award.name} * {sign_award.count}
                            本月签到次数： {sign_info.totalDays}\
                        """
                        img = MessageSegment.image(sign_award.icon)
                    else:
                        msg = f"今日{sign_game_name}签到失败！请尝试重新签到，若多次失败请尝试重新配置cookie"
                        img = ''
                    await bot.send_msg(
                        message_type="private",
                        user_id=qq,
                        message=msg + img
                    )
                await asyncio.sleep(10)

async def send_bbs_sign_msg(bot: Bot, qq: str):
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        mybmission = Mission(account)
        if account.mybMission:
            sign_flag = await mybmission.sign('ys')
            read_flag = await mybmission.read('ys')
            like_flag = await mybmission.like('ys')
            share_flag = await mybmission.share('ys')
            if account.notice:
                msg = f"""\
                    '今日米游币任务执行完成！
                    执行结果：
                    签到： {'√' if sign_flag else '×'} 
                    阅读： {'√' if read_flag else '×'} 
                    点赞： {'√' if like_flag else '×'} 
                    签到： {'√' if share_flag else '×'} 
                """
                await bot.send_msg(
                    message_type="private",
                    user_id=qq,
                    message=msg
                )
            await asyncio.sleep(10)

async def generate_image():
    for root, dirs, files in os.walk(img_conf.SAVE_PATH, topdown=False):
        for name in files:
            if name.endswith('.jpg'):
                os.remove(os.path.join(root, name))
    for game in ("bh3", "ys", "bh2", "wd", "bbs"):
        good_list = await get_good_list(game)
        img_path = time.strftime(f'{img_conf.SAVE_PATH}/%m-%d-{game}.jpg',time.localtime())
        with open(img_path, 'wb') as f:
            image_bytes = await game_list_to_image(good_list)
            f.write(image_bytes)
            f.close()


driver.on_startup(generate_image)

