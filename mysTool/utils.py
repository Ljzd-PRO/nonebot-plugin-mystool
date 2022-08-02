import random
import string
import time
import httpx
import ntplib
import hashlib
import nonebot
from pathlib import Path
from .config import mysTool_config as conf
from nonebot.log import logger

driver = nonebot.get_driver()

PATH = Path(__file__).parent.absolute()

URL_ACTION_TICKET = "https://api-takumi.mihoyo.com/auth/api/getActionTicketBySToken?action_type=game_role&stoken={stoken}&uid={bbs_uid}"
HEADERS_ACTION_TICKET = {
    "Host": "api-takumi.mihoyo.com",
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_MOBILE,
    "User-Agent": conf.device.USER_AGENT_ACTION_TICKET,
    "Referer": "https://webstatic.mihoyo.com/",
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_MOBILE,
    "Origin": "https://webstatic.mihoyo.com",
    "Content-Length": "66",
    "Connection": "keep-alive",
    "x-rpc-channel": conf.device.X_RPC_CHANNEL,
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "DS": None,
    "x-rpc-device_id": None,
    "x-rpc-client_type": "5",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=utf-8",
    "Accept-Encoding": "gzip, deflate, br",
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION,
    "x-rpc-platform": conf.device.X_RPC_PLATFORM
}


class NtpTime():
    """
    >>> NtpTime.time() #获取校准后的时间（如果校准成功）
    """
    time_offset = 0

    @classmethod
    def time(cls) -> float:
        """
        获取校准后的时间（如果校准成功）
        """
        return time.time() + cls.time_offset


@driver.on_startup
def ntp_time_sync():
    ntp_error_times = 0
    NtpTime.time_offset = 0
    while True:
        logger.debug(conf.LOG_HEAD + "正在校对互联网时间")
        try:
            NtpTime.time_offset = ntplib.NTPClient().request(
                conf.NTP_SERVER).tx_time - time.time()
            break
        except:
            ntp_error_times += 1
            if ntp_error_times == conf.MAX_RETRY_TIMES:
                logger.warning(conf.LOG_HEAD + "校对互联网时间失败，改为使用本地时间")
                break
            else:
                logger.warning(conf.LOG_HEAD +
                               "校对互联网时间失败，正在重试({})".format(ntp_error_times))


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


def cookie_str_to_dict(cookie_str: str) -> dict[str, str]:
    """
    将字符串Cookie转换为字典Cookie
    """
    cookie_str = cookie_str.replace(" ", "")
    # Cookie末尾缺少 ; 的情况
    if cookie_str[-1] != ";":
        cookie_str += ";"

    cookie_dict = {}
    start = 0
    while start != len(cookie_str):
        mid = cookie_str.find("=", start)
        end = cookie_str.find(";", mid)
        cookie_dict.setdefault(cookie_str[start:mid], cookie_str[mid + 1:end])
        start = end + 1
    return cookie_dict


def cookie_dict_to_str(cookie_dict: dict[str, str]) -> str:
    """
    将字符串Cookie转换为字典Cookie
    """
    cookie_str = ""
    for key in cookie_dict:
        cookie_str += (key + "=" + cookie_dict[key] + ";")
    return cookie_str


def get_DS():
    """
    获取Headers中所需DS
    """
    # DS 加密算法:
    # 1. https://github.com/lhllhx/miyoubi/issues/3
    # 2. https://github.com/jianggaocheng/mihoyo-signin/blob/master/lib/mihoyoClient.js
    t = int(NtpTime.time())
    a = "".join(random.sample(
        string.ascii_lowercase + string.digits, 6))
    re = hashlib.md5(
        f"salt=b253c83ab2609b1b600eddfe974df47b&t={t}&r={a}".encode(
            encoding="utf-8")).hexdigest()
    return f"{t},{a},{re}"


async def get_action_ticket(cookie: dict) -> str:
    headers = HEADERS_ACTION_TICKET.copy()
    headers["DS"] = get_DS()
    res: httpx.Response = await httpx.get(URL_ACTION_TICKET, headers=headers, cookies=cookie)
    return res["data"]["ticket"]
