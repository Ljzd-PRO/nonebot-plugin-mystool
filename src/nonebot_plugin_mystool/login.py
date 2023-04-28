"""
### 米游社登录获取Cookie相关
"""
import json
import traceback
from typing import Literal, Union, List

import httpx
import requests.utils
import tenacity
from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent, Message
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Arg
from nonebot.params import ArgPlainText, T_State

from .config import config as conf
from .data import UserData, UserAccount
from .utils import custom_attempt_times, generate_device_id, logger, COMMAND_BEGIN

URL_1 = "https://webapi.account.mihoyo.com/Api/login_by_mobilecaptcha"
URL_2 = "https://api-takumi.mihoyo.com/auth/api/getMultiTokenByLoginTicket?login_ticket={0}&token_types=3&uid={1}"
URL_3 = "https://api-takumi.mihoyo.com/account/auth/api/webLoginByMobile"
HEADERS_1 = {
    "Host": "webapi.account.mihoyo.com",
    "Connection": "keep-alive",
    "sec-ch-ua": conf.device.UA,
    "DNT": "1",
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_PC,
    "sec-ch-ua-mobile": "?0",
    "User-Agent": conf.device.USER_AGENT_PC,
    "x-rpc-device_id": None,
    "Accept": "application/json, text/plain, */*",
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_PC,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-rpc-client_type": "4",
    "sec-ch-ua-platform": conf.device.UA_PLATFORM,
    "Origin": "https://user.mihoyo.com",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://user.mihoyo.com/",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
}
HEADERS_2 = {
    "Host": "api-takumi.mihoyo.com",
    "Content-Type": "application/json;charset=utf-8",
    "Origin": "https://bbs.mihoyo.com",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": conf.device.USER_AGENT_PC,
    "Referer": "https://bbs.mihoyo.com/",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9"
}


class GetCookie:
    """
    获取Cookie(需先初始化对象)
    """

    def __init__(self, qq: int, phone: int) -> None:
        self.phone = phone
        self.bbsUID: str = ""
        self.cookie: dict = {}
        '''获取到的Cookie数据'''
        self.client = httpx.AsyncClient()
        account = UserData.read_account(qq, phone)
        if account is None:
            self.deviceID = generate_device_id()
        else:
            self.deviceID = account.deviceID

    async def get_1(self, captcha: str, retry: bool = True) -> Literal[1, -1, -2, -3, -4]:
        """
        第一次获取Cookie(目标是login_ticket)

        :param captcha: 短信验证码
        :param retry: 是否允许重试

        - 若返回 `1` 说明已成功
        - 若返回 `-1` 说明Cookie缺少`login_ticket`
        - 若返回 `-2` 说明Cookie缺少米游社UID(bbsUID)，如`stuid`
        - 若返回 `-3` 说明请求失败
        - 若返回 `-4` 说明验证码错误
        """
        headers = HEADERS_1.copy()
        headers["x-rpc-device_id"] = self.deviceID
        try:
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry),
                                                        wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = await self.client.post(URL_1, headers=headers,
                                                 content=f"mobile={self.phone}&mobile_captcha={captcha}&source=user"
                                                         ".mihoyo.com", timeout=conf.TIME_OUT)
                    try:
                        res_json = res.json()
                        if res_json["data"]["msg"] == "验证码错误" or res_json["data"]["info"] == "Captcha not match Err":
                            logger.info(f"{conf.LOG_HEAD}登录米哈游账号 - 验证码错误")
                            return -4
                    except Exception:
                        pass
                    if "login_ticket" not in res.cookies:
                        return -1
                    for item in ("login_uid", "stuid", "ltuid", "account_id"):
                        if item in res.cookies:
                            self.bbsUID = res.cookies[item]
                            break
                    if not self.bbsUID:
                        return -2
                    self.cookie = requests.utils.dict_from_cookiejar(
                        res.cookies.jar)
                    return 1
        except tenacity.RetryError:
            logger.error(f"{conf.LOG_HEAD}登录米哈游账号 - 获取第一次Cookie: 网络请求失败")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
            return -3

    async def get_2(self, retry: bool = True):
        """
        获取stoken

        :param retry: 是否允许重试

        - 若返回 `True` 说明Cookie缺少`cookie_token`
        - 若返回 `False` 说明网络请求失败或服务器没有正确返回
        """
        try:
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                        wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = await self.client.get(URL_2.format(self.cookie["login_ticket"], self.bbsUID),
                                                timeout=conf.TIME_OUT)
                    stoken = list(filter(
                        lambda data: data["name"] == "stoken", res.json()["data"]["list"]))[0]["token"]
                    self.cookie["stoken"] = stoken
                    return True
        except KeyError:
            logger.error(f"{conf.LOG_HEAD}登录米哈游账号 - 获取stoken: 服务器没有正确返回")
            logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        except Exception:
            logger.error(f"{conf.LOG_HEAD}登录米哈游账号 - 获取stoken: 网络请求失败")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return False

    async def get_3(self, captcha: str, retry: bool = True) -> Literal[1, -1, -2, -3]:
        """
        第二次获取Cookie(目标是cookie_token)

        :param captcha: 短信验证码
        :param retry: 是否允许重试

        - 若返回 `1` 说明已成功
        - 若返回 `-1` 说明Cookie缺少`cookie_token`
        - 若返回 `-2` 说明请求失败
        - 若返回 `-3` 说明验证码错误
        """
        try:
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry),
                                                        wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = await self.client.post(URL_3, headers=HEADERS_2, json={
                        "is_bh2": False,
                        "mobile": str(self.phone),
                        "captcha": captcha,
                        "action_type": "login",
                        "token_type": 6
                    }, timeout=conf.TIME_OUT)
                    try:
                        res_json = res.json()
                        if res_json["data"]["msg"] == "验证码错误" or res_json["data"]["info"] == "Captcha not match Err":
                            logger.info(f"{conf.LOG_HEAD}登录米哈游账号 - 验证码错误")
                            return -3
                    except Exception:
                        pass
                    if "cookie_token" not in res.cookies:
                        return -1
                    self.cookie.update(
                        requests.utils.dict_from_cookiejar(res.cookies.jar))
                    await self.client.aclose()
                    return 1
        except tenacity.RetryError:
            logger.error(f"{conf.LOG_HEAD}登录米哈游账号 - 获取第三次Cookie: 网络请求失败")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
            return -2


get_cookie = on_command(conf.COMMAND_START + '登录', priority=4, block=True)
get_cookie.name = '登录'
get_cookie.usage = '跟随指引，通过电话获取短信方式绑定米游社账户，配置完成后会自动开启签到、米游币任务，后续可制定米游币自动兑换计划。'


@get_cookie.handle()
async def handle_first_receive(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    if isinstance(event, GroupMessageEvent):
        await get_cookie.finish("⚠️为了保护您的隐私，请添加机器人好友后私聊进行登录。")
    account_num = len(UserData.read_all())
    if account_num < conf.MAX_USER:
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


@get_cookie.got('手机号', prompt='1.请发送您的手机号：')
async def _(event: PrivateMessageEvent, state: T_State, phone: str = ArgPlainText('手机号')):
    if phone == '退出':
        await get_cookie.finish("🚪已成功退出")
    phone_num = None
    try:
        phone_num = int(phone)
    except Exception:
        await get_cookie.reject("⚠️手机号应为11位数字，请重新输入")
    if len(phone) != 11:
        await get_cookie.reject("⚠️手机号应为11位数字，请重新输入")
    else:
        state['phone'] = phone_num
        state['getCookie'] = GetCookie(event.user_id, phone_num)


@get_cookie.handle()
async def _(_: PrivateMessageEvent):
    await get_cookie.send('2.前往 https://user.mihoyo.com/#/login/captcha，获取验证码（不要登录！）')


@get_cookie.got("验证码1", prompt='3.请发送验证码：')
async def _(_: PrivateMessageEvent, state: T_State, captcha1: str = ArgPlainText('验证码1')):
    if captcha1 == '退出':
        await get_cookie.finish("🚪已成功退出")
    try:
        int(captcha1)
    except Exception:
        await get_cookie.reject("⚠️验证码应为6位数字，请重新输入")
    if len(captcha1) != 6:
        await get_cookie.reject("⚠️验证码应为6位数字，请重新输入")
    else:
        status: int = await state['getCookie'].get_1(captcha1)
        if status == -1:
            await get_cookie.finish("⚠️由于Cookie缺少login_ticket，无法继续，请稍后再试")
        elif status == -2:
            await get_cookie.finish("⚠️由于Cookie缺少uid，无法继续，请稍后再试")
        elif status == -3:
            await get_cookie.finish("⚠️网络请求失败，无法继续，请稍后再试")
        elif status == -4:
            await get_cookie.reject("⚠️验证码错误，注意不要在网页上使用掉验证码，请重新发送")

    status: bool = await state["getCookie"].get_2()
    if not status:
        await get_cookie.finish("⚠️获取stoken失败，一种可能是登录失效，请稍后再试")


@get_cookie.handle()
async def _(_: PrivateMessageEvent):
    await get_cookie.send('4.请刷新网页，再次获取验证码（不要登录！）')


@get_cookie.got('验证码2', prompt='4.请发送验证码：')
async def _(event: PrivateMessageEvent, state: T_State, captcha2: str = ArgPlainText('验证码2')):
    if captcha2 == '退出':
        await get_cookie.finish("🚪已成功退出")
    try:
        int(captcha2)
    except Exception:
        await get_cookie.reject("⚠️验证码应为6位数字，请重新输入")
    if len(captcha2) != 6:
        await get_cookie.reject("⚠️验证码应为6位数字，请重新输入")
    else:
        status: bool = await state["getCookie"].get_3(captcha2)
        if status < 0:
            if status == -3:
                await get_cookie.reject("⚠️验证码错误，注意不要在网页上使用掉验证码，请重新发送")
            await get_cookie.finish("⚠️获取cookie_token失败，一种可能是登录失效，请稍后再试")

    UserData.set_cookie(state['getCookie'].cookie,
                        int(event.user_id), state['phone'])
    logger.info(f"{conf.LOG_HEAD}米游社账户 {state['phone']} 绑定成功")
    await get_cookie.finish(f"🎉米游社账户 {state['phone']} 绑定成功")


output_cookies = on_command(
    conf.COMMAND_START + '导出Cookies',
    aliases={conf.COMMAND_START + '导出Cookie', conf.COMMAND_START + '导出账号',
             conf.COMMAND_START + '导出cookie', conf.COMMAND_START + '导出cookies'}, priority=4, block=True)
output_cookies.name = '导出Cookies'
output_cookies.usage = '导出绑定的米游社账号的Cookies数据'


@output_cookies.handle()
async def handle_first_receive(event: Union[GroupMessageEvent, PrivateMessageEvent], state: T_State):
    """
    Cookies导出命令触发
    """
    if isinstance(event, GroupMessageEvent):
        await output_cookies.finish("⚠️为了保护您的隐私，请添加机器人好友后私聊进行登录。")
    if not UserData.read_account_all(event.user_id):
        await output_cookies.finish(f"⚠️你尚未绑定米游社账户，请先使用『{COMMAND_BEGIN}登录』进行登录")
    else:
        user_account = UserData.read_account_all(event.user_id)
        phones = [str(str(user_account[i].phone)) for i in range(len(user_account))]
        state['user_account'] = user_account
        msg = "您有多个账号，您要导出哪个账号的Cookies数据？\n"
        msg += "📱" + "\n📱".join(phones)
        msg += "\n🚪发送“退出”即可退出"
        await output_cookies.send(msg)


@output_cookies.got('phone')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, phone=Arg()):
    """
    根据手机号设置导出相应的账户的Cookies
    """
    if isinstance(phone, Message):
        phone = phone.extract_plain_text().strip()
    if phone == '退出':
        await matcher.finish('🚪已成功退出')
    user_account: List[UserAccount] = state['user_account']
    phones = [str(user_account[i].phone) for i in range(len(user_account))]
    if phone in phones:
        await output_cookies.finish(json.dumps(UserData.read_account(event.user_id, int(phone)).cookie, indent=4))
    else:
        await matcher.reject('⚠️您输入的账号不在以上账号内，请重新输入')
