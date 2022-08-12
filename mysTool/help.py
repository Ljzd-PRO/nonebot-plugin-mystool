"""
### 帮助相关
### 参考了nonebot-plugin-help 
"""
import nonebot.plugin
from nonebot import on_command, get_driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Arg
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

helper = on_command("help", priority=1, aliases={"帮助"})
command = list(get_driver().config.command_start)[0]

helper.__help_name__ = 'help'
helper.__help_info__ = f'''\
    欢迎使用米游社小助手！
    {command}help  # 获取米游社小助手帮助
    {command}help list  # 展示米游社小助手可调用功能
    {command}help <name>  # 调取目标功能帮助信息\
'''.strip()
plugin = nonebot.plugin.get_plugin('mysTool')
@helper.handle()
async def handle_first_receive(event: Event, matcher: Matcher, args: Message = CommandArg()):
    at = MessageSegment.at(event.get_user_id())
    if args:
        matcher.set_arg("content", args)
    else:
        await matcher.finish(plugin.metadata.name + plugin.metadata.description + "具体用法：\n" + plugin.metadata.usage)

@helper.got('content')
async def get_result(event: Event, content: Message = Arg()):
    at = MessageSegment.at(event.get_user_id())
    arg = content.extract_plain_text().strip()
    if arg.lower() == "list":
        await helper.finish("具体用法：\n" + plugin.metadata.usage)
    else:
        matchers = plugin.matcher
        infos = {}
        index = 1
        """for matcher in matchers:
            continue
            try:
                name = matcher.__help_name__
            except AttributeError:
                name = None
            try:
                help_info = matcher.__help_info__
            except AttributeError:
                help_info = matcher.__doc__
            if name and help_info:
                infos[f'{index}. {name}'] = help_info
                index += 1
        # not found
        if not plugin:
            result = f'{arg} 不存在或未加载，请确认输入了正确的插件名'
        else:
            results = []
            # if metadata set, use the general usage in metadata instead of legacy __usage__
            if plugin.metadata and plugin.metadata.name and plugin.metadata.usage:
                results.extend([f'{plugin.metadata.name}: {plugin.metadata.description}', plugin.metadata.usage])
            else:
                # legacy __usage__ or __doc__
                try:
                    results.extend([plugin.module.__getattribute__("__help_plugin_name__"),
                                    plugin.module.__getattribute__("__usage__")])
                except:
                    try:
                        results.extend([plugin.name, plugin.module.__doc__])
                    except AttributeError:
                        pass
            # Matcher level help, still legacy since nb2 has no Matcher metadata
            matchers = plugin.matcher
            infos = {}
            index = 1
            for matcher in matchers:
                try:
                    name = matcher.__help_name__
                except AttributeError:
                    name = None
                try:
                    help_info = matcher.__help_info__
                except AttributeError:
                    help_info = matcher.__doc__
                if name and help_info:
                    infos[f'{index}. {name}'] = help_info
                    index += 1
            if index > 1:
                results.extend(["", "序号. 命令名: 命令用途"])
                results.extend(
                    [f'{key}: {value}' for key, value in infos.items()
                     if key and value]
                )
            results = list(filter(None, results))
            result = '\n'.join(results)
    await helper.finish(Message().append(at).append(
        MessageSegment.text(result)))"""