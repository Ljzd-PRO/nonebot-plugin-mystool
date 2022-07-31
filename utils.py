import httpx
import asyncio
import requests
import random
import string

USER_AGENT_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.25.1"
"""移动端 User-Agent"""
USER_AGENT_PC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
"""桌面端 User-Agent"""
X_RPC_DEVICE_MODEL = "OS X 10.15.7"
"""Headers所用的 x-rpc-device_model"""
X_RPC_DEVICE_NAME = "Microsoft Edge 103.0.1264.62"
"""Headers所用的 x-rpc-device_name"""
UA = "\".Not/A)Brand\";v=\"99\", \"Microsoft Edge\";v=\"103\", \"Chromium\";v=\"103\""
"""Headers所用的 sec-ch-ua"""


def generateDeviceID() -> str:
    """
    生成随机的x-rpc-device_id
    """
    return "".join(random.sample(string.ascii_letters + string.digits,
                                 8)).lower() + "-" + "".join(random.sample(string.ascii_letters + string.digits,
                                                                           4)).lower() + "-" + "".join(random.sample(string.ascii_letters + string.digits,
                                                                                                                     4)).lower() + "-" + "".join(random.sample(string.ascii_letters + string.digits,
                                                                                                                                                               4)).lower() + "-" + "".join(random.sample(string.ascii_letters + string.digits,
                                                                                                                                                                                                         12)).lower()


async def onekeyCookie(phone, captcha) -> None:
    login_1_headers = {
        "Host": "webapi.account.mihoyo.com",
        "Connection": "keep-alive",
        "Content-Length": "79",
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
    except:
        return
    login_1_cookie = requests.utils.dict_from_cookiejar(
        login_1_req.cookies)

    if "login_ticket" not in login_1_cookie:
        print("> 由于Cookie缺少login_ticket，无法继续，回车以返回\n")
        return

    for cookie in ("login_uid", "stuid", "ltuid", "account_id"):
        if cookie in login_1_cookie:
            bbs_uid = login_1_cookie[cookie]
            break
    if bbs_uid == None:
        print("> 由于Cookie缺少uid，无法继续，回车以返回\n")
        return

    print("正在获取stoken...")
    try:
        get_stoken_req = httpx.get(
            "https://api-takumi.mihoyo.com/auth/api/getMultiTokenByLoginTicket?login_ticket={0}&token_types=3&uid={1}".format(login_1_cookie["login_ticket"], bbs_uid))
        stoken = list(filter(
            lambda data: data["name"] == "stoken", get_stoken_req.json()["data"]["list"]))[0]["token"]
        exit(1)
    except:
        print("> 获取stoken失败，一种可能是登录失效，回车以返回\n")
        return
