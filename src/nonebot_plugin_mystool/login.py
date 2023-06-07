"""
### 米游社登录获取Cookie相关
"""
import json
from typing import Union, List

from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent, Message
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Arg
from nonebot.params import ArgPlainText, T_State

from .plugin_data import plugin_data_obj as conf
from .user_data import UserAccount
from .utils import logger, COMMAND_BEGIN

get_cookie = on_command(conf.preference.command_start + '登录', priority=4, block=True)
get_cookie.name = '登录'
get_cookie.usage = '跟随指引，通过电话获取短信方式绑定米游社账户，配置完成后会自动开启签到、米游币任务，后续可制定米游币自动兑换计划。'


@get_cookie.handle()
async def handle_first_receive(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    if isinstance(event, GroupMessageEvent):
        await get_cookie.finish("⚠️为了保护您的隐私，请添加机器人好友后私聊进行登录。")
    user_num = len(conf.users)
    if user_num < conf.preference.max_user or conf.preference.max_user in [-1, 0]:
        await get_cookie.send("""\
        登录过程概览：\
        \n1.发送手机号\
        \n2.前往 https://user.mihoyo.com/#/login/captcha，输入手机号并获取验证码（网页上不要登录）\
        \n3.发送验证码给QQ机器人\
        \n4.刷新网页，再次获取验证码并发送给QQ机器人\
        \n🚪过程中发送“退出”即可退出\
            """.strip())
    else:
        await get_cookie.finish('⚠️目前可支持使用用户数已经满啦~')


@get_cookie.got('phone', prompt='1.请发送您的手机号：')
async def _(_: PrivateMessageEvent, state: T_State, phone: str = ArgPlainText('phone')):
    if phone == '退出':
        await get_cookie.finish("🚪已成功退出")
    if not phone.isdigit():
        await get_cookie.reject("⚠️手机号应为数字，请重新输入")
    if len(phone) != 11:
        await get_cookie.reject("⚠️手机号应为11位数字，请重新输入")
    else:
        state['phone'] = phone


@get_cookie.handle()
async def _(_: PrivateMessageEvent):
    await get_cookie.send('2.前往 https://user.mihoyo.com/#/login/captcha，获取验证码（不要登录！）')


@get_cookie.got("captcha", prompt='3.请发送验证码：')
async def _(_: PrivateMessageEvent, state: T_State, captcha: str = ArgPlainText('captcha')):
    if captcha == '退出':
        await get_cookie.finish("🚪已成功退出")
    if not captcha.isdigit():
        await get_cookie.reject("⚠️验证码应为数字，请重新输入")
    else:
        # TODO login
        if status == -1:
            await get_cookie.finish("⚠️由于Cookie缺少login_ticket，无法继续，请稍后再试")
        elif status == -2:
            await get_cookie.finish("⚠️由于Cookie缺少uid，无法继续，请稍后再试")
        elif status == -3:
            await get_cookie.finish("⚠️网络请求失败，无法继续，请稍后再试")
        elif status == -4:
            await get_cookie.reject("⚠️验证码错误，注意不要在网页上使用掉验证码，请重新发送")

    # TODO save

    logger.info(f"{conf.preference.log_head}米游社账户 {state['phone']} 绑定成功")
    await get_cookie.finish(f"🎉米游社账户 {state['phone']} 绑定成功")


output_cookies = on_command(
    conf.preference.command_start + '导出Cookies',
    aliases={conf.preference.command_start + '导出Cookie', conf.preference.command_start + '导出账号',
             conf.preference.command_start + '导出cookie', conf.preference.command_start + '导出cookies'}, priority=4, block=True)
output_cookies.name = '导出Cookies'
output_cookies.usage = '导出绑定的米游社账号的Cookies数据'


@output_cookies.handle()
async def handle_first_receive(event: Union[GroupMessageEvent, PrivateMessageEvent], state: T_State):
    """
    Cookies导出命令触发
    """
    if isinstance(event, GroupMessageEvent):
        await output_cookies.finish("⚠️为了保护您的隐私，请添加机器人好友后私聊进行登录。")
    user_account = conf.users[event.user_id].accounts
    if user_account:
        await output_cookies.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    else:
        phones = [str(str(user_account[i].phone)) for i in range(len(user_account))]
        state['user_account'] = user_account
        msg = "您有多个账号，您要导出哪个账号的Cookies数据？\n"
        msg += "📱" + "\n📱".join(phones)
        msg += "\n🚪发送“退出”即可退出"
        await output_cookies.send(msg)


@output_cookies.got('phone')
async def _(_: PrivateMessageEvent, matcher: Matcher, state: T_State, phone=Arg()):
    """
    根据手机号设置导出相应的账户的Cookies
    """
    if isinstance(phone, Message):
        phone = phone.extract_plain_text().strip()
    if phone == '退出':
        await matcher.finish('🚪已成功退出')
    user_account: List[UserAccount] = state['user_account']
    phones = [str(user_account[i].phone_number) for i in range(len(user_account))]
    if phone in phones:
        await output_cookies.finish(json.dumps(next(filter(lambda x: x.phone_number == phone, user_account)), indent=4))
    else:
        await matcher.reject('⚠️您输入的账号不在以上账号内，请重新输入')
