"""
### 帮助相关
#### 参考了`nonebot-plugin-help`
"""
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, CommandArg

from .plugin_data import PluginDataManager
from .utils import PLUGIN, COMMAND_BEGIN

_conf = PluginDataManager.plugin_data

helper = on_command(_conf.preference.command_start + "help",
                    priority=1,
                    aliases={_conf.preference.command_start + "帮助"},
                    block=True)

helper.name = '帮助'
helper.usage = '''\
    🍺欢迎使用米游社小助手帮助系统！\
    \n{HEAD}帮助 ➢ 查看米游社小助手使用说明\
    \n{HEAD}帮助 <功能名> ➢ 查看目标功能详细说明\
'''.strip()


@helper.handle()
async def _(_: MessageEvent, matcher: Matcher, args: Message = CommandArg()):
    """
    主命令触发
    """
    # 二级命令
    if args:
        matcher.set_arg("content", args)
    # 只有主命令“帮助”
    else:
        await matcher.finish(
            PLUGIN.metadata.name +
            PLUGIN.metadata.description +
            "\n具体用法：\n" +
            PLUGIN.metadata.usage.format(HEAD=COMMAND_BEGIN))


@helper.got('content')
async def _(_: MessageEvent, content: Message = Arg()):
    """
    二级命令触发。功能详细说明查询
    """
    arg = content.extract_plain_text().strip()

    # 相似词
    if arg == '登陆':
        arg = '登录'

    matchers = PLUGIN.matcher
    for matcher in matchers:
        try:
            if arg.lower() == matcher.name:
                await helper.finish(
                    f"『{COMMAND_BEGIN}{matcher.name}』- 使用说明\n{matcher.usage.format(HEAD=COMMAND_BEGIN)}")
        except AttributeError:
            continue
    await helper.finish("⚠️未查询到相关功能，请重新尝试")
