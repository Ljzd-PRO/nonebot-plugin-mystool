"""
### 帮助相关
### 参考了nonebot-plugin-help 
"""
import nonebot.plugin
from nonebot import on_command, get_driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Arg
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.adapters.onebot.v11.message import Message
from .config import mysTool_config as conf

__cs = ''
if conf.USE_COMMAND_START:
    __cs = conf.COMMAND_START
helper = on_command(__cs+"help", priority=1, aliases={__cs+"帮助"})
command = __cs + list(get_driver().config.command_start)[0]

helper.__help_name__ = '帮助'
helper.__help_info__ = f'''\
    欢迎使用米游社小助手帮助系统！\
    \n{command}帮助  # 获取米游社小助手可调用帮助\
    \n{command}帮助 <功能名>  # 调取目标功能帮助信息\
'''.strip()
plugin = nonebot.plugin.get_plugin('mysTool')
@helper.handle()
async def handle_first_receive(event: PrivateMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if args:
        matcher.set_arg("content", args)
    else:
        await matcher.finish(plugin.metadata.name + plugin.metadata.description + "具体用法：\n" + plugin.metadata.usage.replace('/', command) + '\n' + plugin.metadata.extra)

@helper.got('content')
async def get_result(event: PrivateMessageEvent, content: Message = Arg()):
    arg = content.extract_plain_text().strip()
    matchers = plugin.matcher
    for matcher in matchers:
        try:
            if arg.lower() == matcher.__help_name__:
                await helper.finish(f"{command}{matcher.__help_name__}：\n{matcher.__help_info__}")
        except AttributeError:
            continue
    await helper.finish("未查询到相关功能，请重新尝试")