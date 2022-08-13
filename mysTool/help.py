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

helper = on_command("help", priority=1, aliases={"帮助"})
command = list(get_driver().config.command_start)[0]

helper.__help_name__ = 'help'
helper.__help_info__ = f'''\
    欢迎使用米游社小助手帮助系统！
    {command}help  # 获取米游社小助手可调用帮助
    {command}help main # 获取米游社小助手具体信息
    {command}help list  # 展示米游社小助手可调用功能
    {command}help <功能名>  # 调取目标功能帮助信息
    {command}help extra # 获取github项目地址，可进行bug反馈，意见提出\
'''.strip()
plugin = nonebot.plugin.get_plugin('mysTool')
@helper.handle()
async def handle_first_receive(event: PrivateMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if args:
        matcher.set_arg("content", args)
    else:
        await matcher.finish(helper.__help_info__)

@helper.got('content')
async def get_result(event: PrivateMessageEvent, content: Message = Arg()):
    arg = content.extract_plain_text().strip()
    if arg.lower() == "list":
        await helper.finish("具体用法：\n" + plugin.metadata.usage)
    elif arg.lower() == "main":
        await helper.finish(plugin.metadata.name + plugin.metadata.description + "具体用法：\n" + plugin.metadata.usage.replace('/', command))
    elif arg.lower() == "extra":
        await helper.finish(plugin.metadata.extra)
    else:
        matchers = plugin.matcher
        for matcher in matchers:
            try:
                if arg.lower() == matcher.__help_name__:
                    await helper.finish(f"{matcher.__help_name__}：\n{matcher.__help_info__}")
            except AttributeError:
                continue
        helper.finish("未查询到相关功能，请重新尝试")