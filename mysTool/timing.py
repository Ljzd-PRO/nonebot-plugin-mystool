"""
### 计划任务相关
"""
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, MessageSegment
from nonebot.params import T_State
from nonebot import on_command, require, get_bots
from nonebot.permission import SUPERUSER
import asyncio
from .data import UserData
from .bbsAPI import *
from .gameSign import *
from .config import mysTool_config as conf
from .utils import *
from .mybMission import Mission
from .exchange import get_good_list

bot = get_bots().values()


daily_game_sign = require("nonebot_plugin_apscheduler").scheduler

@daily_game_sign.scheduled_job("cron", hour='0', minute='00', id="daily_game_sign")

async def daily_game_sign_():
    qq_accounts = UserData.read_all().keys()
    for qq in qq_accounts:
        await send_game_sign_msg(qq)


manually_game_sign = on_command(
    'game_sign', aliases={'签到', '手动签到', '游戏签到', '原神签到' ,'yssign'}, priority=4, block=True)
manually_game_sign.__help_name__ = 'game_sign'
manually_game_sign.__help_info__ = '手动进行游戏签到'

@manually_game_sign.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    qq = event.user_id
    await send_game_sign_msg(qq)


daily_bbs_sign = require("nonebot_plugin_apscheduler").scheduler

@daily_bbs_sign.scheduled_job("cron", hour='0', minute='00', id="daily_bbs_sign")
async def daily_bbs_sign_():
    qq_accounts = UserData.read_all().keys()
    for qq in qq_accounts:
        await send_bbs_sign_msg(qq)


manually_bbs_sign = on_command(
    'bbs_sign', aliases={'米游社签到', '米游社任务', '米游币获取', 'bbssign'}, priority=4, block=True)
manually_bbs_sign.__help_name__ = 'bbs_sign'
manually_bbs_sign.__help_info__ = '手动进行米游社每日任务'

@manually_bbs_sign.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    qq = event.user_id
    await send_bbs_sign_msg(qq)


update_timing = require("nonebot_plugin_apscheduler").scheduler

@update_timing.scheduled_job("cron", hour='0', minute='00', id="daily_update")
async def daily_update():
    for game in ("bh3", "ys", "bh2", "wd", "bbs"):
        await get_good_list(game)  # 米游社商品更新函数


manually_update = on_command('update_good', aliases={
                             '商品更新', '米游社商品更新'}, permission=SUPERUSER, priority=4, block=True)

@manually_update.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    for game in ("bh3", "ys", "bh2", "wd", "bbs"):
        await get_good_list(game)  # 米游社商品更新函数
    await manually_update.send('已完成商品更新')


async def send_game_sign_msg(qq):
    accounts = UserData.read_account_all(qq)
    for account in accounts:
        gamesign = GameSign(account)
        if account.gameSign:
            await gamesign.sign('ys')
            if account.notice:
                sign_award = await gamesign.reward('ys')
                sign_info = await gamesign.info('ys')
                accounts_info = await get_game_record(account)
                for account_info in accounts_info:
                    if account_info.gameID == '2':
                        break
                msg = f"""\
                    {'今日签到成功！' if sign_info.isSign else '今日已签到！'}
                    {account_info.nickname} {account_info.regionName} {account_info.level}
                    今日签到奖励：
                    {sign_award.name} * {sign_award.count}
                    本月签到次数： {sign_info.totalDays}\
                """
                img = MessageSegment.image(sign_award.icon)
                await bot.send_msg(
                    message_type="private",
                    user_id=qq,
                    message=msg + img
                )


async def send_bbs_sign_msg(qq):
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
