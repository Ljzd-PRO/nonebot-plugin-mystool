"""
### QQ好友相关
"""
import asyncio

from nonebot import get_driver, on_request
from nonebot.adapters.onebot.v11 import (Bot, FriendRequestEvent,
                                         GroupRequestEvent, RequestEvent)
from nonebot_plugin_apscheduler import scheduler

from .config import mysTool_config as conf
from .data import UserData
from .utils import logger

driver = get_driver()

friendRequest = on_request(priority=1, block=True)


@friendRequest.handle()
async def _(bot: Bot, event: RequestEvent):
    command = list(get_driver().config.command_start)[0]
    # 判断为加好友事件
    if isinstance(event, FriendRequestEvent):
        if conf.ADD_FRIEND_ACCEPT:
            logger.info(f'{conf.LOG_HEAD}已添加好友{event.user_id}')
            await bot.set_friend_add_request(flag=event.flag, approve=True)
            # 等待腾讯服务器响应
            await asyncio.sleep(1.5)
            await bot.send_private_msg(user_id=event.user_id, message=f'欢迎使用米游社小助手，请发送『{command}帮助』查看更多用法哦~')
    # 判断为邀请进群事件
    elif isinstance(event, GroupRequestEvent):
        logger.info(f'{conf.LOG_HEAD}已添加群聊{event.group_id}')
        # 等待腾讯服务器响应
        await asyncio.sleep(1.5)
        await bot.send_group_msg(group_id=event.group_id, message=f'欢迎使用米游社小助手，请添加小助手为好友后，发送『{command}』帮助 查看更多用法哦~')


@driver.on_bot_connect
async def check_friend_list(bot: Bot):
    """
    检查用户是否仍在好友列表中，不在的话则删除
    """
    logger.info(f'{conf.LOG_HEAD}正在检查好友列表...')
    friend_list = await bot.get_friend_list()
    user_list = UserData.read_all().keys()
    for user in user_list:
        if not list(filter(lambda friend: friend["user_id"] == user, friend_list)):
            logger.info(f'{conf.LOG_HEAD}用户{user}不在好友列表内，已删除其数据')
            UserData.del_user(user)


@driver.on_bot_connect
async def _(bot: Bot):
    scheduler.add_job(id='check_friend', replace_existing=True,
                      trigger="cron", hour='23', minute='59', func=check_friend_list, args=(bot,))
