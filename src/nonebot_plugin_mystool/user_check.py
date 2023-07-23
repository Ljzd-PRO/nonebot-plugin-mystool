"""
### QQ好友相关
"""
import asyncio
import json
import os

from nonebot import get_driver, on_request
from nonebot.adapters.onebot.v11 import (Bot, FriendRequestEvent,
                                         GroupRequestEvent, RequestEvent)
from nonebot_plugin_apscheduler import scheduler

from .plugin_data import PluginDataManager, write_plugin_data, DELETED_USERS_PATH
from .utils import logger

_conf = PluginDataManager.plugin_data
_driver = get_driver()
friendRequest = on_request(priority=1, block=True)


@friendRequest.handle()
async def _(bot: Bot, event: RequestEvent):
    command_start = list(get_driver().config.command_start)[0]
    # 判断为加好友事件
    if isinstance(event, FriendRequestEvent):
        if _conf.preference.add_friend_accept:
            logger.info(f'{_conf.preference.log_head}已添加好友{event.user_id}')
            await bot.set_friend_add_request(flag=event.flag, approve=True)
            if _conf.preference.add_friend_welcome:
                # 等待腾讯服务器响应
                await asyncio.sleep(1.5)
                await bot.send_private_msg(user_id=event.user_id,
                                           message=f'欢迎使用米游社小助手，请发送『{command_start}帮助』查看更多用法哦~')
    # 判断为邀请进群事件
    elif isinstance(event, GroupRequestEvent):
        logger.info(f'{_conf.preference.log_head}已加入群聊 {event.group_id}')


@_driver.on_bot_connect
async def check_friend_list(bot: Bot):
    """
    检查用户是否仍在好友列表中，不在的话则删除
    """
    logger.info(f'{_conf.preference.log_head}正在检查好友列表...')
    friend_list = await bot.get_friend_list()
    for user in _conf.users:
        user_filter = filter(lambda x: x["user_id"] == user, friend_list)
        friend = next(user_filter, None)
        if not friend:
            if not os.path.exists(DELETED_USERS_PATH):
                os.mkdir(DELETED_USERS_PATH)
            json.dump(
                _conf.users.pop(user),
                open(DELETED_USERS_PATH / f"{user}.json", "w"),
                ensure_ascii=False,
                indent=4
            )
            write_plugin_data()
            logger.info(f'{_conf.preference.log_head}用户 {user} 不在好友列表内，'
                        f'已删除其数据，并备份至 {DELETED_USERS_PATH / f"{user}.json"}')


@_driver.on_bot_connect
async def _(bot: Bot):
    scheduler.add_job(id='check_friend', replace_existing=True,
                      trigger="cron", hour='23', minute='59', func=check_friend_list, args=(bot,))
