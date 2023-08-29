'''
Author: Night-stars-1 nujj1042633805@gmail.com
Date: 2023-08-25 16:54:38
LastEditors: Night-stars-1 nujj1042633805@gmail.com
LastEditTime: 2023-08-29 23:54:25
Description: 

Copyright (c) 2023 by Night-stars-1, All Rights Reserved. 
'''
"""
### QQ好友相关
"""
import asyncio
from typing import  Union

from nonebot import get_driver, on_request
from nonebot.adapters.onebot.v11 import (Bot, FriendRequestEvent,
                                         GroupRequestEvent, RequestEvent)
from nonebot.adapters.qqguild import Bot as GuildBot
from nonebot.adapters.telegram import Bot as TGBot
from nonebot_plugin_apscheduler import scheduler

from .plugin_data import PluginDataManager, write_plugin_data
from .utils import logger, PLUGIN

_conf = PluginDataManager.plugin_data_obj
_driver = get_driver()
friendRequest = on_request(priority=1, block=True)

@friendRequest.handle()
async def _(bot: Bot, event: RequestEvent):
    command_start = list(get_driver().config.command_start)[0]
    # 判断为加好友事件
    if isinstance(event, FriendRequestEvent):
        if _conf.preference.add_friend_accept:
            logger.info(f'{_conf.preference.log_head}已添加好友{event.get_user_id()}')
            await bot.set_friend_add_request(flag=event.flag, approve=True)
            if _conf.preference.add_friend_welcome:
                # 等待腾讯服务器响应
                await asyncio.sleep(1.5)
                await bot.send_private_msg(user_id=event.get_user_id(),
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
    copy_users = _conf.users.copy()
    for user in copy_users:
        user_filter = filter(lambda x: x["user_id"] == user, friend_list)
        friend = next(user_filter, None)
        if not friend and _conf.users[user].software == "qq":
            logger.info(f'{_conf.preference.log_head}用户 {user} 不在好友列表内，已删除其数据')
            _conf.users.pop(user)
            write_plugin_data()
    logger.info(f'{_conf.preference.log_head}好友列表检测完成...')

@_driver.on_bot_connect
async def check_guild_list(bot: GuildBot):
    """
    检查用户是否仍在频道成员列表中，不在的话则删除
    """
    logger.info(f'{_conf.preference.log_head}正在检查频道成员列表...')
    guild_list = []
    for guild in await bot.guilds():
        guild_list += await bot.get_members(guild_id=guild.id, limit=1000)
    copy_users = _conf.users.copy()
    for user in copy_users:
        user_filter = filter(lambda x: x.user.id == user, guild_list)
        friend = next(user_filter, None)
        if not friend and _conf.users[user].software == "qqguild":
            logger.info(f'{_conf.preference.log_head}用户 {user} 不在频道成员列表内，已删除其数据')
            _conf.users.pop(user)
            write_plugin_data()
    logger.info(f'{_conf.preference.log_head}频道成员列表检测完成...')

@_driver.on_bot_connect
async def _(bot: TGBot):
    """
    检查用户是否仍在TG群组成员列表中，不在的话则删除
    """
    commands = [
        {
            "command":matcher.command,
            "description": matcher.usage
        } 
        for matcher in PLUGIN.matcher 
        if "command" in matcher.__dict__ and "usage" in matcher.__dict__
    ]
    try:
        await bot.setMyCommands(commands=commands)
        logger.info(f'{_conf.preference.log_head}TG群组命令栏设置成功')
    except:
        logger.info(f'{_conf.preference.log_head}TG群组命令栏设置失败')

@_driver.on_bot_connect
async def _(bot: Union[Bot, GuildBot]):
    scheduler.add_job(id='check_friend', replace_existing=True,
                      trigger="cron", hour='23', minute='59', func=check_friend_list, args=(bot,))
    scheduler.add_job(id='guild_friend', replace_existing=True,
                      trigger="cron", hour='23', minute='59', func=check_guild_list, args=(bot,))
