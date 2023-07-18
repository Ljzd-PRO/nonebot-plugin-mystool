"""
### 米游社登录获取Cookie相关
"""
import json
from typing import Union

from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent, Message
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Arg
from nonebot.params import ArgPlainText, T_State

from .plugin_data import PluginDataManager, write_plugin_data
from .simple_api import get_login_ticket_by_captcha, get_multi_token_by_login_ticket, get_stoken_v2_by_v1, \
    get_ltoken_by_stoken, get_cookie_token_by_stoken, get_device_fp
from .user_data import UserAccount, UserData
from .utils import logger, COMMAND_BEGIN

_conf = PluginDataManager.plugin_data

get_cookie = on_command(_conf.preference.command_start + '登录', priority=4, block=True)
get_cookie.name = '登录'
get_cookie.usage = '跟随指引，通过电话获取短信方式绑定米游社账户，配置完成后会自动开启签到、米游币任务，后续可制定米游币自动兑换计划。'


@get_cookie.handle()
async def handle_first_receive(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    if isinstance(event, GroupMessageEvent):
        await get_cookie.finish("⚠️为了保护您的隐私，请添加机器人好友后私聊进行登录。")
    user_num = len(_conf.users)
    if user_num < _conf.preference.max_user or _conf.preference.max_user in [-1, 0]:
        await get_cookie.send("""\
        登录过程概览：\
        \n1.发送手机号\
        \n2.前往 https://user.mihoyo.com/#/login/captcha，输入手机号并获取验证码（网页上不要登录）\
        \n3.发送验证码给QQ机器人，完成登录\
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
async def _(event: PrivateMessageEvent, state: T_State, captcha: str = ArgPlainText('captcha')):
    phone_number: str = state['phone']
    if captcha == '退出':
        await get_cookie.finish("🚪已成功退出")
    if not captcha.isdigit():
        await get_cookie.reject("⚠️验证码应为数字，请重新输入")
    else:
        _conf.users.setdefault(event.user_id, UserData())
        user = _conf.users[event.user_id]
        # 1. 通过短信验证码获取 login_ticket / 使用已有 login_ticket
        login_status, cookies = await get_login_ticket_by_captcha(phone_number, int(captcha))
        if login_status:
            # logger.info(f"用户 {phone_number} 成功获取 login_ticket: {cookies.login_ticket}")
            account = _conf.users[event.user_id].accounts.get(cookies.bbs_uid)
            """当前的账户数据对象"""
            if not account or not account.cookies:
                user.accounts.update({
                    cookies.bbs_uid: UserAccount(phone_number=phone_number, cookies=cookies)
                })
                account = user.accounts[cookies.bbs_uid]
            else:
                account.cookies.update(cookies)
            if not account.device_id_ios:
                fp_status, account.device_fp = await get_device_fp(account.device_id_ios)
                if fp_status:
                    logger.info(f"用户 {cookies.bbs_uid} 成功获取 device_fp: {account.device_fp}")
            write_plugin_data()

            # 2. 通过 login_ticket 获取 stoken 和 ltoken
            if login_status or account:
                login_status, cookies = await get_multi_token_by_login_ticket(account.cookies)
                if login_status:
                    logger.info(f"用户 {phone_number} 成功获取 stoken: {cookies.stoken}")
                    account.cookies.update(cookies)
                    write_plugin_data()

                    # 3. 通过 stoken_v1 获取 stoken_v2 和 mid
                    login_status, cookies = await get_stoken_v2_by_v1(account.cookies, account.device_id_ios)
                    if login_status:
                        logger.info(f"用户 {phone_number} 成功获取 stoken_v2: {cookies.stoken_v2}")
                        account.cookies.update(cookies)
                        write_plugin_data()

                        # 4. 通过 stoken_v2 获取 ltoken
                        login_status, cookies = await get_ltoken_by_stoken(account.cookies, account.device_id_ios)
                        if login_status:
                            logger.info(f"用户 {phone_number} 成功获取 ltoken: {cookies.ltoken}")
                            account.cookies.update(cookies)
                            write_plugin_data()

                            # 5. 通过 stoken_v2 获取 cookie_token
                            login_status, cookies = await get_cookie_token_by_stoken(account.cookies,
                                                                                     account.device_id_ios)
                            if login_status:
                                logger.info(f"用户 {phone_number} 成功获取 cookie_token: {cookies.cookie_token}")
                                account.cookies.update(cookies)
                                write_plugin_data()

                                logger.info(f"{_conf.preference.log_head}米游社账户 {phone_number} 绑定成功")
                                await get_cookie.finish(f"🎉米游社账户 {phone_number} 绑定成功")

        if not login_status:
            notice_text = "⚠️登录失败："
            if login_status.incorrect_captcha:
                notice_text += "验证码错误！"
            elif login_status.login_expired:
                notice_text += "登录失效！"
            elif login_status.incorrect_return:
                notice_text += "服务器返回错误！"
            elif login_status.network_error:
                notice_text += "网络连接失败！"
            elif login_status.missing_bbs_uid:
                notice_text += "Cookies缺少 bbs_uid（例如 ltuid, stuid）"
            elif login_status.missing_login_ticket:
                notice_text += "Cookies缺少 login_ticket！"
            elif login_status.missing_cookie_token:
                notice_text += "Cookies缺少 cookie_token！"
            elif login_status.missing_stoken:
                notice_text += "Cookies缺少 stoken！"
            elif login_status.missing_stoken_v1:
                notice_text += "Cookies缺少 stoken_v1"
            elif login_status.missing_stoken_v2:
                notice_text += "Cookies缺少 stoken_v2"
            elif login_status.missing_mid:
                notice_text += "Cookies缺少 mid"
            else:
                notice_text += "未知错误！"
            notice_text += " 如果部分步骤成功，你仍然可以尝试获取收货地址、兑换等功能"
            await get_cookie.finish(notice_text)


output_cookies = on_command(
    _conf.preference.command_start + '导出Cookies',
    aliases={_conf.preference.command_start + '导出Cookie', _conf.preference.command_start + '导出账号',
             _conf.preference.command_start + '导出cookie', _conf.preference.command_start + '导出cookies'}, priority=4,
    block=True)
output_cookies.name = '导出Cookies'
output_cookies.usage = '导出绑定的米游社账号的Cookies数据'


@output_cookies.handle()
async def handle_first_receive(event: Union[GroupMessageEvent, PrivateMessageEvent], matcher: Matcher):
    """
    Cookies导出命令触发
    """
    if isinstance(event, GroupMessageEvent):
        await output_cookies.finish("⚠️为了保护您的隐私，请添加机器人好友后私聊进行Cookies导出。")
    user_account = _conf.users[event.user_id].accounts
    if not user_account:
        await output_cookies.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    elif len(user_account) == 1:
        account = next(iter(user_account.values()))
        matcher.set_arg('bbs_uid', Message(account.bbs_uid))
    else:
        msg = "您有多个账号，您要导出哪个账号的Cookies数据？\n"
        msg += "\n".join(map(lambda x: f"🆔{x}", user_account))
        msg += "\n🚪发送“退出”即可退出"
        await output_cookies.send(msg)


@output_cookies.got('bbs_uid')
async def _(event: PrivateMessageEvent, matcher: Matcher, uid=Arg("bbs_uid")):
    """
    根据手机号设置导出相应的账户的Cookies
    """
    if isinstance(uid, Message):
        uid = uid.extract_plain_text().strip()
    if uid == '退出':
        await matcher.finish('🚪已成功退出')
    user_account = _conf.users[event.user_id].accounts
    if uid in user_account:
        await output_cookies.finish(json.dumps(user_account[uid].cookies.dict(cookie_type=True), indent=4))
    else:
        await matcher.reject('⚠️您输入的账号不在以上账号内，请重新输入')
