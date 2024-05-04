import asyncio
import json
from typing import Union, Optional

from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent, MessageSegment as OneBotV11MessageSegment
from nonebot.adapters.qq import MessageSegment as QQGuildMessageSegment, DirectMessageCreateEvent, \
    MessageEvent as QQGuildMessageEvent
from nonebot.adapters.qq.exception import AuditException
from nonebot.exception import ActionFailed
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import ArgStr, ArgPlainText
from nonebot.params import T_State

from ..api.common import get_ltoken_by_stoken, get_cookie_token_by_stoken, get_device_fp, fetch_game_token_qrcode, \
    query_game_token_qrcode, \
    get_token_by_game_token, get_cookie_token_by_game_token, create_mmt, create_mobile_captcha, \
    get_login_ticket_by_captcha, get_multi_token_by_login_ticket, get_stoken_v2_by_v1, BaseApiStatus, \
    CreateMobileCaptchaStatus
from ..command.common import CommandRegistry
from ..model import PluginDataManager, plugin_config, UserAccount, UserData, CommandUsage, BBSCookies, \
    QueryGameTokenQrCodeStatus, GetCookieStatus
from ..utils import logger, COMMAND_BEGIN, GeneralMessageEvent, GeneralPrivateMessageEvent, \
    GeneralGroupMessageEvent, \
    read_blacklist, read_whitelist, generate_device_id, generate_qr_img, get_validate

__all__ = ["get_cookie", "output_cookies"]


def get_login_status_msg(status: Union[BaseApiStatus, QueryGameTokenQrCodeStatus, GetCookieStatus]) -> Optional[str]:
    if not status:
        notice_text = "⚠️登录失败："
        if isinstance(status, QueryGameTokenQrCodeStatus):
            if status.qrcode_expired:
                notice_text += "登录二维码已过期！"
        if isinstance(status, GetCookieStatus):
            if status.missing_bbs_uid:
                notice_text += "Cookies缺少 bbs_uid（例如 ltuid, stuid）"
            elif status.missing_login_ticket:
                notice_text += "Cookies缺少 login_ticket！"
            elif status.missing_cookie_token:
                notice_text += "Cookies缺少 cookie_token！"
            elif status.missing_stoken:
                notice_text += "Cookies缺少 stoken！"
            elif status.missing_stoken_v1:
                notice_text += "Cookies缺少 stoken_v1"
            elif status.missing_stoken_v2:
                notice_text += "Cookies缺少 stoken_v2"
            elif status.missing_mid:
                notice_text += "Cookies缺少 mid"
        if status.login_expired:
            notice_text += "登录失效！"
        elif status.incorrect_return:
            notice_text += "服务器返回错误！"
        elif status.network_error:
            notice_text += "网络连接失败！"
        else:
            notice_text += "未知错误！"
        notice_text += " 如果部分步骤成功，你仍然可以尝试获取收货地址、兑换等功能"
        return notice_text
    else:
        return None


get_cookie = on_command(plugin_config.preference.command_start + '登录', priority=4, block=True)

CommandRegistry.set_usage(
    get_cookie,
    CommandUsage(
        name="登录",
        description="跟随指引，通过电话获取短信方式绑定米游社账户，配置完成后会自动开启签到、米游币任务，后续可制定米游币自动兑换计划。"
    )
)


@get_cookie.handle()
async def handle_first_receive(event: Union[GeneralMessageEvent]):
    user_num = len(set(PluginDataManager.plugin_data.users.values()))  # 由于加入了用户数据绑定功能，可能存在重复的用户数据对象，需要去重
    if plugin_config.preference.enable_blacklist:
        if event.get_user_id() in read_blacklist():
            await get_cookie.finish("⚠️您已被加入黑名单，无法使用本功能")
    elif plugin_config.preference.enable_whitelist:
        if event.get_user_id() not in read_whitelist():
            await get_cookie.finish("⚠️您不在白名单内，无法使用本功能")
    if user_num <= plugin_config.preference.max_user or plugin_config.preference.max_user in [-1, 0]:
        await get_cookie.send("您可以选择通过短信验证码或扫描二维码的方式登录：\n"
                              "1. 扫描二维码\n"
                              "2. 短信验证码（需要通过私信使用）\n"
                              "请选择登录方式（数字序号）")


@get_cookie.got("method")
async def get_login_method(event: Union[GeneralMessageEvent], method: str = ArgPlainText('method')):
    if method == "1":
        # 获取用户数据对象
        user_id = event.get_user_id()
        PluginDataManager.plugin_data.users.setdefault(user_id, UserData())
        user = PluginDataManager.plugin_data.users[user_id]
        # 如果是QQ频道，需要记录频道ID
        if isinstance(event, DirectMessageCreateEvent):
            user.qq_guild[user_id] = event.channel_id

        # 1. 获取 GameToken 登录二维码
        device_id = generate_device_id()
        login_status, fetch_qrcode_ret = await fetch_game_token_qrcode(
            device_id,
            plugin_config.preference.game_token_app_id
        )
        if fetch_qrcode_ret:
            qrcode_url, qrcode_ticket = fetch_qrcode_ret
            await get_cookie.send("请用米游社App扫描下面的二维码进行登录")
            image_bytes = generate_qr_img(qrcode_url)
            if isinstance(event, OneBotV11MessageEvent):
                msg_img = OneBotV11MessageSegment.image(image_bytes)
            elif isinstance(event, QQGuildMessageEvent):
                msg_img = QQGuildMessageSegment.file_image(image_bytes)
            else:
                await get_cookie.finish("⚠️发送二维码失败，无法登录")
                return
            try:
                await get_cookie.send(msg_img)
            except (ActionFailed, AuditException) as e:
                if isinstance(e, ActionFailed):
                    logger.exception("发送包含二维码的登录消息失败")
                    await get_cookie.finish("⚠️发送二维码失败，无法登录")

            # 2. 从二维码登录获取 GameToken
            qrcode_query_times = round(
                plugin_config.preference.qrcode_wait_time / plugin_config.preference.qrcode_query_interval
            )
            bbs_uid, game_token = None, None
            for _ in range(qrcode_query_times):
                login_status, query_qrcode_ret = await query_game_token_qrcode(
                    qrcode_ticket,
                    device_id,
                    plugin_config.preference.game_token_app_id
                )
                if query_qrcode_ret:
                    bbs_uid, game_token = query_qrcode_ret
                    logger.success(f"用户 {bbs_uid} 成功获取 game_token: {game_token}")
                    break
                elif login_status.qrcode_expired:
                    get_cookie.finish("⚠️二维码已过期，登录失败")
                elif not login_status:
                    await asyncio.sleep(plugin_config.preference.qrcode_query_interval)
                    continue

            if bbs_uid and game_token:
                cookies = BBSCookies()
                cookies.bbs_uid = bbs_uid
                account = PluginDataManager.plugin_data.users[user_id].accounts.get(bbs_uid)
                """当前的账户数据对象"""
                if not account or not account.cookies:
                    user.accounts.update({
                        bbs_uid: UserAccount(
                            phone_number=None,
                            cookies=cookies,
                            device_id_ios=device_id,
                            device_id_android=generate_device_id())
                    })
                    account = user.accounts[bbs_uid]
                else:
                    account.cookies.update(cookies)
                fp_status, account.device_fp = await get_device_fp(device_id)
                if fp_status:
                    logger.success(f"用户 {bbs_uid} 成功获取 device_fp: {account.device_fp}")
                PluginDataManager.write_plugin_data()

                if login_status:
                    # 3. 通过 GameToken 获取 stoken_v2
                    login_status, cookies = await get_token_by_game_token(bbs_uid, game_token)
                    if login_status:
                        logger.success(f"用户 {bbs_uid} 成功获取 stoken_v2: {cookies.stoken_v2}")
                        account.cookies.update(cookies)
                        PluginDataManager.write_plugin_data()

                        if account.cookies.stoken_v2:
                            # 5. 通过 stoken_v2 获取 ltoken
                            login_status, cookies = await get_ltoken_by_stoken(account.cookies, device_id)
                            if login_status:
                                logger.success(f"用户 {bbs_uid} 成功获取 ltoken: {cookies.ltoken}")
                                account.cookies.update(cookies)
                                PluginDataManager.write_plugin_data()

                            # 6.1. 通过 stoken_v2 获取 cookie_token
                            login_status, cookies = await get_cookie_token_by_stoken(account.cookies, device_id)
                            if login_status:
                                logger.success(f"用户 {bbs_uid} 成功获取 cookie_token: {cookies.cookie_token}")
                                account.cookies.update(cookies)
                                PluginDataManager.write_plugin_data()

                                logger.success(
                                    f"{plugin_config.preference.log_head}米游社账户 {bbs_uid} 绑定成功")
                                await get_cookie.finish(f"🎉米游社账户 {bbs_uid} 绑定成功")
                        else:
                            # 6.2. 通过 GameToken 获取 cookie_token
                            login_status, cookies = await get_cookie_token_by_game_token(bbs_uid, game_token)
                            if login_status:
                                logger.success(f"用户 {bbs_uid} 成功获取 cookie_token: {cookies.cookie_token}")
                                account.cookies.update(cookies)
                                PluginDataManager.write_plugin_data()
            else:
                get_cookie.finish("⚠️获取二维码扫描状态超时，请尝试重新登录")

        if login_status_msg := get_login_status_msg(login_status):
            get_cookie.finish(login_status_msg)
    elif method == "2":
        if isinstance(event, GeneralGroupMessageEvent):
            await get_cookie.finish("⚠️为了保护您的隐私，请私聊进行登录。")
        # QQ频道可能无法发送链接，需要发送二维码
        login_url = "https://user.mihoyo.com/#/login/captcha"
        msg_text = "登录过程概览：\n" \
                   "1.发送手机号\n" \
                   "2.{browse_way}，输入手机号并获取验证码（不要在网页上登录）\n" \
                   "3.发送验证码给QQ机器人，完成登录\n" \
                   "🚪过程中发送“退出”即可退出"
        try:
            await get_cookie.send(msg_text.format(browse_way=f"前往 {login_url}"))
        except ActionFailed:
            logger.exception("发送包含URL链接的登录消息失败")
            msg_img = QQGuildMessageSegment.file_image(generate_qr_img(login_url))
            try:
                await get_cookie.send(msg_img)
                await get_cookie.send(msg_text.format(browse_way="扫描二维码，进入米哈游官方登录页"))
            except (ActionFailed, AuditException) as e:
                if isinstance(e, ActionFailed):
                    logger.exception("发送包含二维码的登录消息失败")
                    await get_cookie.send(msg_text.format(
                        browse_way="前往米哈游官方登录页") + "\n\n⚠️发送二维码失败，请自行搜索米哈游通行证登录页")
    else:
        await get_cookie.finish('⚠️目前可支持使用用户数已经满啦~')


@get_cookie.got('phone', prompt='1.请发送您的手机号：')
async def get_phone(event: Union[GeneralPrivateMessageEvent], state: T_State, phone: str = ArgPlainText('phone')):
    if phone == '退出':
        await get_cookie.finish("🚪已成功退出")
    if not phone.isdigit():
        await get_cookie.reject("⚠️手机号应为数字，请重新输入")
    if len(phone) != 11:
        await get_cookie.reject("⚠️手机号应为11位数字，请重新输入")
    else:
        state['phone'] = phone
    user = PluginDataManager.plugin_data.users.get(event.get_user_id())
    if user:
        account_filter = filter(lambda x: x.phone_number == phone, user.accounts.values())
        account = next(account_filter, None)
        device_id = account.phone_number if account else None
    else:
        device_id = None
    mmt_status, mmt_data, device_id, _ = await create_mmt(device_id=device_id)
    state['device_id'] = device_id
    if mmt_status:
        if not mmt_data.gt:
            captcha_status, _ = await create_mobile_captcha(phone_number=phone, mmt_data=mmt_data,
                                                            device_id=device_id)
            if captcha_status:
                await get_cookie.send("检测到无需进行人机验证，已发送短信验证码，请查收")
                return
        elif plugin_config.preference.geetest_url:
            await get_cookie.send("⏳正在尝试完成人机验证，请稍后...")
            # TODO: 人机验证待支持 GT4
            geetest_result = await get_validate(gt=mmt_data.gt, user=user)
            captcha_status, _ = await create_mobile_captcha(
                phone_number=phone,
                mmt_data=mmt_data,
                geetest_result=geetest_result,
                use_v4=False,
                device_id=device_id
            )
            if captcha_status:
                await get_cookie.send("已发送短信验证码，请查收")
                return
            elif captcha_status.incorrect_geetest:
                await get_cookie.send("⚠️尝试进行人机验证失败，请手动获取短信验证码")
        else:
            captcha_status = CreateMobileCaptchaStatus()
        if captcha_status.invalid_phone_number:
            await get_cookie.reject("⚠️手机号无效，请重新发送手机号")
        elif captcha_status.not_registered:
            await get_cookie.reject("⚠️手机号未注册，请注册后重新发送手机号")

    await get_cookie.send('2.前往米哈游官方登录页，获取验证码（不要登录！）')


@get_cookie.got("captcha", prompt='3.请发送验证码：')
async def get_captcha(event: Union[GeneralPrivateMessageEvent], state: T_State, captcha: str = ArgPlainText('captcha')):
    phone_number: str = state['phone']
    device_id: str = state['device_id']
    if captcha == '退出':
        await get_cookie.finish("🚪已成功退出")
    if not captcha.isdigit():
        await get_cookie.reject("⚠️验证码应为数字，请重新输入")
    else:
        user_id = event.get_user_id()
        PluginDataManager.plugin_data.users.setdefault(user_id, UserData())
        user = PluginDataManager.plugin_data.users[user_id]
        # 如果是QQ频道，需要记录频道ID
        if isinstance(event, DirectMessageCreateEvent):
            user.qq_guild[user_id] = event.channel_id
        # 1. 通过短信验证码获取 login_ticket / 使用已有 login_ticket
        login_status, cookies = await get_login_ticket_by_captcha(phone_number, int(captcha), device_id)
        if login_status:
            logger.success(f"用户 {cookies.bbs_uid} 成功获取 login_ticket: {cookies.login_ticket}")
            account = PluginDataManager.plugin_data.users[user_id].accounts.get(cookies.bbs_uid)
            """当前的账户数据对象"""
            if not account or not account.cookies:
                user.accounts.update({
                    cookies.bbs_uid: UserAccount(
                        phone_number=phone_number,
                        cookies=cookies,
                        device_id_ios=device_id,
                        device_id_android=generate_device_id())
                })
                account = user.accounts[cookies.bbs_uid]
            else:
                account.cookies.update(cookies)
            fp_status, account.device_fp = await get_device_fp(device_id)
            if fp_status:
                logger.success(f"用户 {cookies.bbs_uid} 成功获取 device_fp: {account.device_fp}")
            PluginDataManager.write_plugin_data()

            # 2. 通过 login_ticket 获取 stoken 和 ltoken
            if login_status or account:
                login_status, cookies = await get_multi_token_by_login_ticket(account.cookies)
                if login_status:
                    logger.success(f"用户 {phone_number} 成功获取 stoken: {cookies.stoken}")
                    account.cookies.update(cookies)
                    PluginDataManager.write_plugin_data()

                    # 3. 通过 stoken_v1 获取 stoken_v2 和 mid
                    login_status, cookies = await get_stoken_v2_by_v1(account.cookies, device_id)
                    if login_status:
                        logger.success(f"用户 {phone_number} 成功获取 stoken_v2: {cookies.stoken_v2}")
                        account.cookies.update(cookies)
                        PluginDataManager.write_plugin_data()

                        # 4. 通过 stoken_v2 获取 ltoken
                        login_status, cookies = await get_ltoken_by_stoken(account.cookies, device_id)
                        if login_status:
                            logger.success(f"用户 {phone_number} 成功获取 ltoken: {cookies.ltoken}")
                            account.cookies.update(cookies)
                            PluginDataManager.write_plugin_data()

                            # 5. 通过 stoken_v2 获取 cookie_token
                            login_status, cookies = await get_cookie_token_by_stoken(account.cookies, device_id)
                            if login_status:
                                logger.success(f"用户 {phone_number} 成功获取 cookie_token: {cookies.cookie_token}")
                                account.cookies.update(cookies)
                                PluginDataManager.write_plugin_data()

                                logger.success(f"{plugin_config.preference.log_head}米游社账户 {phone_number} 绑定成功")
                                await get_cookie.finish(f"🎉米游社账户 {phone_number} 绑定成功")


output_cookies = on_command(
    plugin_config.preference.command_start + '导出Cookies',
    aliases={plugin_config.preference.command_start + '导出Cookie', plugin_config.preference.command_start + '导出账号',
             plugin_config.preference.command_start + '导出cookie',
             plugin_config.preference.command_start + '导出cookies'}, priority=4,
    block=True)

CommandRegistry.set_usage(
    output_cookies,
    CommandUsage(
        name="导出Cookies",
        description="导出绑定的米游社账号的Cookies数据"
    )
)


@output_cookies.handle()
async def handle_first_receive(event: Union[GeneralMessageEvent], state: T_State):
    """
    Cookies导出命令触发
    """
    if isinstance(event, GeneralGroupMessageEvent):
        await output_cookies.finish("⚠️为了保护您的隐私，请私聊进行Cookies导出。")
    user_account = PluginDataManager.plugin_data.users[event.get_user_id()].accounts
    if not user_account:
        await output_cookies.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    elif len(user_account) == 1:
        account = next(iter(user_account.values()))
        state["bbs_uid"] = account.bbs_uid
    else:
        msg = "您有多个账号，您要导出哪个账号的Cookies数据？\n"
        msg += "\n".join(map(lambda x: f"🆔{x}", user_account))
        msg += "\n🚪发送“退出”即可退出"
        await output_cookies.send(msg)


@output_cookies.got('bbs_uid')
async def _(event: Union[GeneralPrivateMessageEvent], matcher: Matcher, bbs_uid=ArgStr()):
    """
    根据手机号设置导出相应的账户的Cookies
    """
    if bbs_uid == '退出':
        await matcher.finish('🚪已成功退出')
    user_account = PluginDataManager.plugin_data.users[event.get_user_id()].accounts
    if bbs_uid in user_account:
        await output_cookies.finish(json.dumps(user_account[bbs_uid].cookies.dict(cookie_type=True), indent=4))
    else:
        await matcher.reject('⚠️您输入的账号不在以上账号内，请重新输入')
