from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, Message
from nonebot.params import CommandArg, T_State, Arg, ArgPlainText
from nonebot.plugin import PluginMetadata
import requests
import httpx

from .utils import *

__plugin_meta__ = PluginMetadata(
    name="原神签到、米游币获取、米游币兑换插件",
    description="通过手机号获取cookie，每日自动原神签到、获取米游币，可制定米游币兑换计划",
    usage=(
        "get_cookie 跟随指引获取cookie\n"
        "get_myb 订阅每日自动获取米游币计划\n"
        "get_yuanshen 订阅每日自动原神签到计划\n"
        "myb_info 查看米游币数量\n"
        "yuanshen_info 查看当日原神签到奖励，当月原石、摩拉获取\n"
        "myb_exchange 制定米游币兑换计划\n"
        "myb_exchange_info 查看当前米游币兑换计划\n"
        "myb_delete 删除你的所有兑换计划\n"
    )
)

get_cookie = on_command('myb', aliases={'cookie填写', 'cookie'}, priority=4, block=True)
get_cookie.__help__ = {
    "usage":     "get_cookie",
    "introduce": "通过电话获取验证码方式获取cookie"
}

@get_cookie.handle()
async def handle_first_receive(event: PrivateMessageEvent, state: T_State):
    state['qq_account'] = event.user_id
    print(state['qq_account'])
    await get_cookie.send('获取cookie过程分为三步：\n1.发送手机号\n2.登录https://user.mihoyo.com/#/login/captcha，输入手机号并获取验证码并发送\n3.刷新页面，再次获取验证码并发送\n过程中随时输入退出即可退出')

@get_cookie.got('手机号', prompt='请输入您的手机号')
async def _(event: PrivateMessageEvent, state: T_State, phone: str = ArgPlainText('手机号')):
    if phone == '退出':
        await get_cookie.finish("已成功退出")
    try:
        phone_num = int(phone)
    except:
        await get_cookie.finish("手机号应为11位数字，程序已退出")
    if len(phone) != 11:
        await get_cookie.finish("手机号应为11位数字，程序已退出")
    else:
        state['phone'] = phone_num

@get_cookie.got('验证码1', prompt='请在浏览器打开https://user.mihoyo.com/#/login/captcha，输入手机号，获取验证码并发送（不要登录！）')
async def _(event: PrivateMessageEvent, state: T_State, captcha1: str = ArgPlainText('验证码1')):
    await get_cookie.send("请输入验证码")
    if captcha1 == '退出':
        await get_cookie.finish("已成功退出")
    try:
        int(captcha1)
    except:
        await get_cookie.finish("验证码应为6位数字，程序已退出")
    if len(captcha1) != 6:
        await get_cookie.finish("验证码应为6位数字，程序已退出")
    else:
        await get_cookie_1(state['phone'], captcha1, state)
        

@get_cookie.got('验证码2', prompt='请刷新浏览器，再次输入手机号，获取验证码并发送（不要登录！）')
async def _(event: PrivateMessageEvent, state: T_State, captcha2: str = ArgPlainText('验证码2')):
    await get_cookie.send("请输入验证码")
    if captcha2 == '退出':
        await get_cookie.finish("已成功退出")
    try:
        int(captcha2)
    except:
        await get_cookie.finish("验证码应为6位数字，程序已退出")
    if len(captcha2) != 6:
        await get_cookie.finish("验证码应为6位数字，程序已退出")
    else:
        await get_cookie_2(state['phone'], captcha2, state)
    print(state['cookie'])
        

async def get_cookie_1(phone, captcha, state: T_State):
    login_1_headers = {
        "Host": "webapi.account.mihoyo.com",
        "Connection": "keep-alive",
        "sec-ch-ua": UA,
        "DNT": "1",
        "x-rpc-device_model": X_RPC_DEVICE_MODEL,
        "sec-ch-ua-mobile": "?0",
        "User-Agent": USER_AGENT_PC,
        "x-rpc-device_id": generateDeviceID(),
        "Accept": "application/json, text/plain, */*",
        "x-rpc-device_name": X_RPC_DEVICE_NAME,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-rpc-client_type": "4",
        "sec-ch-ua-platform": "\"macOS\"",
        "Origin": "https://user.mihoyo.com",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://user.mihoyo.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
    }

    try:
        login_1_req = httpx.post(
            "https://webapi.account.mihoyo.com/Api/login_by_mobilecaptcha", headers=login_1_headers, data="mobile={0}&mobile_captcha={1}&source=user.mihoyo.com".format(phone, captcha))
    except Exception as e:
        print(repr(e))
        await get_cookie.finish("登录遇到问题，请稍后重试")
    print(login_1_req.cookies)
    login_1_cookie = requests.utils.dict_from_cookiejar(
        login_1_req.cookies.jar)

    if "login_ticket" not in login_1_cookie:
        await get_cookie.finish("由于Cookie缺少login_ticket，无法继续，请稍后再试")

    for cookie in ("login_uid", "stuid", "ltuid", "account_id"):
        if cookie in login_1_cookie:
            bbs_uid = login_1_cookie[cookie]
            break
    if bbs_uid == None:
        await get_cookie.finish("由于Cookie缺少uid，无法继续，请稍后再试")
        
    state['cookie'] = login_1_cookie

    try:
        get_stoken_req = httpx.get(
            "https://api-takumi.mihoyo.com/auth/api/getMultiTokenByLoginTicket?login_ticket={0}&token_types=3&uid={1}".format(login_1_cookie["login_ticket"], bbs_uid))
        stoken = list(filter(
            lambda data: data["name"] == "stoken", get_stoken_req.json()["data"]["list"]))[0]["token"]
        state['cookie']['stoken'] = stoken
    except:
        await get_cookie.finish("获取stoken失败，一种可能是登录失效，请稍后再试")


async def get_cookie_2(phone, captcha, state: T_State):
    login_2_headers = {
        "Host": "api-takumi.mihoyo.com",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://bbs.mihoyo.com",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": USER_AGENT_PC,
        "Referer": "https://bbs.mihoyo.com/",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9"
    }
    try:
        login_2_req = httpx.post(
            "https://api-takumi.mihoyo.com/account/auth/api/webLoginByMobile", headers=login_2_headers, json={
                "is_bh2": False,
                "mobile": phone,
                "captcha": captcha,
                "action_type": "login",
                "token_type": 6
            })
    except:
        await get_cookie.finish(" 登录失败，请稍后再试")

    login_2_cookie = requests.utils.dict_from_cookiejar(
        login_2_req.cookies.jar)

    if "cookie_token" not in login_2_cookie:
        await get_cookie.finish("由于Cookie缺少cookie_token，无法继续，清歌稍后再试")
    
    login_1_cookie = state['cookie']
    state['cookie'] = login_2_cookie
    state['cookie']['login_ticket'] = login_1_cookie["login_ticket"]
    state['cookie']['stoken'] = login_1_cookie["stoken"]
    print(state['cookie'])
    await get_cookie.finish("cookie获取成功")
