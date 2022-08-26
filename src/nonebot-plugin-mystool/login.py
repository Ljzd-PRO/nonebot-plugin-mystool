"""
### 米游社登录获取Cookie相关
"""
import httpx
import requests.utils
from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import ArgPlainText, T_State

from .config import mysTool_config as conf
from .data import UserData
from .utils import *

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
        self.bbsUID: str = None
        self.cookie: dict = None
        '''获取到的Cookie数据'''
        self.client = httpx.AsyncClient()
        account = UserData.read_account(qq, phone)
        if account is None:
            self.deviceID = generateDeviceID()
        else:
            self.deviceID = account.deviceID

    async def get_1(self, captcha: str, retry: bool = True):
        """
        第一次获取Cookie(目标是login_ticket)

        参数:
            `captcha`: 短信验证码
            `retry`: 是否允许重试

        - 若返回 `1` 说明已成功
        - 若返回 `-1` 说明Cookie缺少`login_ticket`
        - 若返回 `-2` 说明Cookie缺少米游社UID(bbsUID)，如`stuid`
        - 若返回 `-3` 说明请求失败
        """
        headers = HEADERS_1.copy()
        headers["x-rpc-device_id"] = self.deviceID
        res = None
        try:
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = await self.client.post(URL_1, headers=headers, data="mobile={0}&mobile_captcha={1}&source=user.mihoyo.com".format(self.phone, captcha), timeout=conf.TIME_OUT)
        except tenacity.RetryError:
            logger.error(
                conf.LOG_HEAD + "登录米哈游账号 - 获取第一次Cookie: 网络请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            return -3

        if "login_ticket" not in res.cookies:
            return -1

        for item in ("login_uid", "stuid", "ltuid", "account_id"):
            if item in res.cookies:
                self.bbsUID = res.cookies[item]
                break
        if not self.bbsUID:
            return -2
        self.cookie = requests.utils.dict_from_cookiejar(res.cookies.jar)
        return 1

    async def get_2(self, retry: bool = True):
        """
        获取stoken

        参数:
            `retry`: 是否允许重试

        - 若返回 `True` 说明Cookie缺少`cookie_token`
        - 若返回 `False` 说明网络请求失败或服务器没有正确返回
        """
        try:
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True, wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = await self.client.get(URL_2.format(self.cookie["login_ticket"], self.bbsUID), timeout=conf.TIME_OUT)
                    stoken = list(filter(
                        lambda data: data["name"] == "stoken", res.json()["data"]["list"]))[0]["token"]
                    self.cookie["stoken"] = stoken
                    return True
        except KeyError:
            logger.error(
                conf.LOG_HEAD + "登录米哈游账号 - 获取stoken: 服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + "网络请求返回: {}".format(res.text))
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
        except:
            logger.error(
                conf.LOG_HEAD + "登录米哈游账号 - 获取stoken: 网络请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
        return False

    async def get_3(self, captcha: str, retry: bool = True):
        """
        第二次获取Cookie(目标是cookie_token)

        参数:
            `captcha`: 短信验证码
            `retry`: 是否允许重试

        - 若返回 `1` 说明已成功
        - 若返回 `-1` 说明Cookie缺少`cookie_token`
        - 若返回 `-2` 说明请求失败
        """
        try:
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = await self.client.post(URL_3, headers=HEADERS_2, json={
                        "is_bh2": False,
                        "mobile": str(self.phone),
                        "captcha": captcha,
                        "action_type": "login",
                        "token_type": 6
                    }, timeout=conf.TIME_OUT)
        except tenacity.RetryError:
            logger.error(
                conf.LOG_HEAD + "登录米哈游账号 - 获取第三次Cookie: 网络请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            return -2
        if "cookie_token" not in res.cookies:
            return -1
        self.cookie.update(requests.utils.dict_from_cookiejar(res.cookies.jar))
        await self.client.aclose()
        return 1

    async def __del__(self):
        await self.client.aclose()


get_cookie = on_command(
    conf.COMMAND_START+'cookie', aliases={conf.COMMAND_START+'cookie填写', conf.COMMAND_START+'cookie', conf.COMMAND_START+'login', conf.COMMAND_START+'登录', conf.COMMAND_START+'登陆'}, priority=4, block=True)
get_cookie.__help_name__ = '登录'
get_cookie.__help_info__ = '跟随指引，通过电话获取短信方式绑定米游社账户，配置完成后会自动开启签到、米游币任务，后续可制定米游币自动兑换计划。'


@get_cookie.handle()
async def handle_first_receive(event: PrivateMessageEvent, state: T_State):
    await get_cookie.send("""\
    登录过程概览：
    1.发送手机号
    2.前往 https://user.mihoyo.com/#/login/captcha，输入手机号并获取验证码（网页上不要登录）
    3.发送验证码给QQ机器人
    4.刷新网页，再次获取验证码并发送给QQ机器人
    过程中随时输入“退出”即可退出\
        """)


@get_cookie.got('手机号', prompt='1.请发送您的手机号：')
async def _(event: PrivateMessageEvent, state: T_State, phone: str = ArgPlainText('手机号')):
    if phone == '退出':
        await get_cookie.finish("已成功退出")
    try:
        phone_num = int(phone)
    except:
        await get_cookie.reject("⚠️手机号应为11位数字，请重新输入")
    if len(phone) != 11:
        await get_cookie.reject("⚠️手机号应为11位数字，请重新输入")
    else:
        state['phone'] = phone_num
        state['getCookie'] = GetCookie(event.user_id, phone_num)


@get_cookie.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    await get_cookie.send('2.前往 https://user.mihoyo.com/#/login/captcha，获取验证码（不要登录！）')


@get_cookie.got("验证码1", prompt='3.请发送验证码：')
async def _(event: PrivateMessageEvent, state: T_State, captcha1: str = ArgPlainText('验证码1')):
    if captcha1 == '退出':
        await get_cookie.finish("已成功退出")
    try:
        int(captcha1)
    except:
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

    status: bool = await state["getCookie"].get_2()
    if not status:
        await get_cookie.finish("⚠️获取stoken失败，一种可能是登录失效，请稍后再试")


@get_cookie.handle()
async def _(event: PrivateMessageEvent, state: T_State):
    await get_cookie.send('4.请刷新网页，再次获取验证码（不要登录！）')


@get_cookie.got('验证码2', prompt='4.请发送验证码：')
async def _(event: PrivateMessageEvent, state: T_State, captcha2: str = ArgPlainText('验证码2')):
    if captcha2 == '退出':
        await get_cookie.finish("已成功退出")
    try:
        int(captcha2)
    except:
        await get_cookie.reject("⚠️验证码应为6位数字，请重新输入")
    if len(captcha2) != 6:
        await get_cookie.reject("⚠️验证码应为6位数字，请重新输入")
    else:
        status: bool = await state["getCookie"].get_3(captcha2)
        if status < 0:
            await get_cookie.finish("⚠️获取cookie_token失败，一种可能是登录失效，请稍后再试")

    UserData.set_cookie(state['getCookie'].cookie,
                        int(event.user_id), state['phone'])
    await get_cookie.finish("米游社账户 {} 绑定成功".format(state['phone']))
