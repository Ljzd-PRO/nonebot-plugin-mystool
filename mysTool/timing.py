from turtle import update
from .config import mysTool_config as conf
from .utils import *
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import T_State, ArgPlainText
from .data import UserAccount, UserData
from nonebot import on_command, require, get_bots
import asyncio
from nonebot.permission import SUPERUSER
from .gameSign import *


sign_timing = require("nonebot_plugin_apscheduler").scheduler


# 此处应改为可由config读入签到时间
@sign_timing.scheduled_job("cron", hour='0', minute='00', id="daily_sign")
async def daily_sign():
    await ...  # 签到函数
    await ...  # 向订阅者发送每日签到播报

manually_sign = on_command(
    'sign', aliases={'签到', '手动签到'}, permission=SUPERUSER, priority=4, block=True)


@manually_sign.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    await ...  # 签到函数
    await manually_sign.send('已完成签到')

update_timing = require("nonebot_plugin_apscheduler").scheduler


# 此处应改为可由config读入更新时间
@update_timing.scheduled_job("cron", hour='0', minute='00', id="daily_update")
async def daily_update():
    await ...  # 米游社商品更新函数

manually_update = on_command('update_good', aliases={
                             '商品更新', '米游社商品更新'}, permission=SUPERUSER, priority=4, block=True)


async def _(event: PrivateMessageEvent, state: T_State):
    await ...  # 米游社商品更新函数
    await manually_sign.send('已完成商品更新')
