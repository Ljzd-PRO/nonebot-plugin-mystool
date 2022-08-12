from nonebot.adapters.onebot.v11 import Bot, RequestEvent, FriendRequestEvent,GroupRequestEvent
from nonebot import get_driver, on_request
import asyncio

FriendRequest = on_request(priority=1, block=True)
@FriendRequest.handle()
async def _(bot: Bot, event: RequestEvent):
    command = list(get_driver().config.command_start)[0]
    if isinstance(event, FriendRequestEvent):
        await bot.set_friend_add_request(flag=event.flag, approve=True)
        await asyncio.sleep(1.5)
        await bot.send_private_msg(user_id=event.user_id, message=f'欢迎使用米游社小助手，请发送{command}help查看更多用法哦~')
    elif isinstance(event, GroupRequestEvent):
        await asyncio.sleep(1.5)
        await bot.send_group_msg(group_id=event.group_id, message=f'欢迎使用米游社小助手，请添加小助手为好友后，发送{command}help查看更多用法哦~')
        