"""
### 帮助相关
#### 参考了`nonebot-plugin-help`
"""
from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, CommandArg

from .config import mysTool_config as conf
from .utils import PLUGIN

COMMAND = list(get_driver().config.command_start)[0] + conf.COMMAND_START

helper = on_command(conf.COMMAND_START + "help", priority=1,
                    aliases={conf.COMMAND_START + "帮助"})

helper.__help_name__ = '帮助'
helper.__help_info__ = f'''\
    🍺欢迎使用米游社小助手帮助系统！\
    \n{COMMAND}帮助 ➢ 查看米游社小助手使用说明\
    \n{COMMAND}帮助 <功能名> ➢ 查看目标功能详细说明\
'''.strip()


@helper.handle()
async def handle_first_receive(event: MessageEvent, matcher: Matcher, args: Message = CommandArg()):
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
            PLUGIN.metadata.usage.format(HEAD=COMMAND))


@helper.got('content')
async def get_result(event: MessageEvent, content: Message = Arg()):
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
            if arg.lower() == matcher.__help_name__:
                await helper.finish(f"『{COMMAND}{matcher.__help_name__}』- 使用说明\n{matcher.__help_info__}")
        except AttributeError:
            continue
    await helper.finish("⚠️未查询到相关功能，请重新尝试")
