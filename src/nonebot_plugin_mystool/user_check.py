"""
### QQ好友相关
"""
import asyncio
from uuid import uuid4

from nonebot import get_driver, on_request, on_command
from nonebot.adapters.onebot.v11 import (Bot, FriendRequestEvent,
                                         GroupRequestEvent, RequestEvent)
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg, Command

from .plugin_data import PluginDataManager, write_plugin_data
from .user_data import UserData, uuid4_validate
from .utils import logger, GeneralMessageEvent, COMMAND_BEGIN, get_last_command_sep

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


user_binding = on_command(
    f"{_conf.preference.command_start}用户绑定",
    aliases={
        (f"{_conf.preference.command_start}用户绑定", "UUID"),
        (f"{_conf.preference.command_start}用户绑定", "uuid"),
        (f"{_conf.preference.command_start}用户绑定", "查询"),
        (f"{_conf.preference.command_start}用户绑定", "还原"),
        (f"{_conf.preference.command_start}用户绑定", "刷新UUID"),
        (f"{_conf.preference.command_start}用户绑定", "刷新uuid")
    },
    priority=5,
    block=True
)
user_binding.name = '用户绑定'
user_binding.usage = '通过UUID绑定关联其他聊天平台或者其他账号的用户数据，以免去重新登录等操作'
user_binding.extra_usage = """\
具体用法：
{HEAD}用户绑定{SEP}UUID ➢ 查看用于绑定的当前用户数据的UUID密钥
{HEAD}用户绑定{SEP}查询 ➢ 查看当前用户的绑定情况
{HEAD}用户绑定{SEP}还原 ➢ 清除当前用户的绑定关系，使当前用户数据成为空白数据
{HEAD}用户绑定{SEP}刷新UUID ➢ 重新生成当前用户的UUID密钥，原先与您绑定的用户将无法访问您当前的用户数据
{HEAD}用户绑定 <UUID> ➢ 绑定目标UUID的用户数据，当前用户的所有数据将被目标用户覆盖
『{SEP}』为分隔符，使用NoneBot配置中的其他分隔符亦可\
"""


@user_binding.handle()
async def _(
        event: GeneralMessageEvent,
        matcher: Matcher,
        command=Command(),
        command_arg=CommandArg()
):
    user_id = event.get_user_id()
    user = _conf.users.get(user_id)
    if len(command) > 1:
        if user is None:
            await matcher.finish("⚠️您的用户数据不存在，只有进行登录操作以后才会生成用户数据")
        elif command[1] in ["UUID", "uuid"]:
            await matcher.send(
                "🔑您的UUID密钥为：\n" if user_id not in _conf.user_bind else
                "🔑您绑定的用户数据的UUID密钥为：\n"
                f"{user.uuid.upper()}\n"
                "可用于其他聊天平台进行数据绑定，请不要泄露给他人"
            )

        elif command[1] == "查询":
            if user_id in _conf.user_bind:
                await matcher.send(
                    "🖇️目前您绑定关联了用户：\n"
                    f"{_conf.user_bind[user_id]}\n"
                    "您的任何操作都将会影响到目标用户的数据"
                )
            elif user_id in _conf.user_bind.values():
                user_filter = filter(lambda x: _conf.user_bind[x] == user_id, _conf.user_bind)
                await matcher.send(
                    "🖇️目前有以下用户绑定了您的数据：\n"
                    "\n".join(user_filter)
                )
            else:
                await matcher.send("⚠️您当前没有绑定任何用户数据，也没有任何用户绑定您的数据")

        elif command[1] == "还原":
            if user_id not in _conf.user_bind:
                await matcher.finish("⚠️您当前没有绑定任何用户数据")
            else:
                del _conf.user_bind[user_id]
                _conf.users[user_id] = UserData()
                write_plugin_data()
                await matcher.send("✔已清除当前用户的绑定关系，当前用户数据已是空白数据")

        elif command[1] in ["刷新UUID", "刷新uuid"]:
            if user_id in _conf.user_bind:
                target_id = _conf.user_bind[user_id]
                be_bind = False
            else:
                target_id = user_id
                be_bind = True

            user_filter = filter(lambda x: _conf.user_bind[x] == target_id, _conf.user_bind)
            for key in user_filter:
                del _conf.user_bind[key]
                _conf.users[key] = UserData()
            _conf.users[target_id].uuid = str(uuid4())
            write_plugin_data()

            await matcher.send(
                "✔已刷新UUID密钥，原先绑定的用户将无法访问当前用户数据\n" if be_bind else
                "✔已刷新您绑定的用户数据的UUID密钥，目前您的用户数据已为空，您也可以再次绑定\n"
                f"🔑新的UUID密钥：{user.uuid.upper()}\n"
                "可用于其他聊天平台进行数据绑定，请不要泄露给他人"
            )

        else:
            await matcher.reject(
                '⚠️您的输入有误，二级命令不正确\n\n'
                f'{matcher.extra_usage.format(HEAD=COMMAND_BEGIN, SEP=get_last_command_sep())}'
            )
    elif not command_arg:
        await matcher.send(
            f"『{COMMAND_BEGIN}{matcher.name}』- 使用说明\n"
            f"{matcher.usage.format(HEAD=COMMAND_BEGIN)}\n"
            f'{matcher.extra_usage.format(HEAD=COMMAND_BEGIN, SEP=get_last_command_sep())}'
        )
    else:
        uuid = str(command_arg).lower()
        if not uuid4_validate(uuid):
            await matcher.finish("⚠️您输入的UUID密钥格式不正确")
        elif uuid == user.uuid:
            await matcher.finish("⚠️您不能绑定自己的UUID密钥")
        else:
            # 筛选UUID密钥对应的用户
            target_users = list(filter(lambda x: x[1].uuid == uuid and x[0] != user_id, _conf.users.items()))
            # 如果有多个用户使用了此UUID密钥，即目标用户被多个用户绑定，需要进一步筛选，防止形成循环绑定的关系链
            if len(target_users) > 1:
                user_filter = filter(lambda x: x[0] not in _conf.user_bind, target_users)
                target_id, _ = next(user_filter)
            elif len(target_users) == 1:
                target_id, _ = target_users[0]
            else:
                await matcher.finish("⚠️找不到此UUID密钥对应的用户数据")
                return
            _conf.do_user_bind(user_id, target_id)
            await matcher.send(f"✔已绑定用户 {target_id} 的用户数据")
