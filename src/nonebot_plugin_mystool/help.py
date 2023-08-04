"""
### 帮助相关
#### 参考了`nonebot-plugin-help`
"""
from nonebot import on_command
from nonebot.adapters.qqguild.exception import ActionFailed as QQGuildActionFailed
from nonebot.internal.params import ArgStr
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from .plugin_data import PluginDataManager
from .utils import PLUGIN, COMMAND_BEGIN, GeneralMessageEvent, logger

_conf = PluginDataManager.plugin_data

helper = on_command(
    f"{_conf.preference.command_start}帮助",
    priority=1,
    aliases={f"{_conf.preference.command_start}help"},
    block=True
)

helper.name = '帮助'
helper.usage = "🍺欢迎使用米游社小助手帮助系统！" \
               "\n{HEAD}帮助 ➢ 查看米游社小助手使用说明" \
               "\n{HEAD}帮助 <功能名> ➢ 查看目标功能详细说明"


@helper.handle()
async def _(_: GeneralMessageEvent, matcher: Matcher, args=CommandArg()):
    """
    主命令触发
    """
    # 二级命令
    if args:
        matcher.set_arg("content", args)
    # 只有主命令“帮助”
    else:
        try:
            await matcher.finish(
                f"{PLUGIN.metadata.name}"
                f"{PLUGIN.metadata.description}\n"
                "具体用法：\n"
                f"{PLUGIN.metadata.usage.format(HEAD=COMMAND_BEGIN)}"
            )
        except QQGuildActionFailed as e:
            if e.code == 304003:
                logger.exception(f"{_conf.preference.log_head}帮助命令的文本发送失败，原因是频道禁止发送URL")


@helper.got('content')
async def _(_: GeneralMessageEvent, content=ArgStr()):
    """
    二级命令触发。功能详细说明查询
    """
    # 相似词
    if content == '登陆':
        content = '登录'

    matchers = PLUGIN.matcher
    for matcher in matchers:
        try:
            if content.lower() == matcher.name:
                await helper.finish(
                    f"『{COMMAND_BEGIN}{matcher.name}』- 使用说明\n{matcher.usage}")
        except AttributeError:
            continue
    await helper.finish("⚠️未查询到相关功能，请重新尝试")
