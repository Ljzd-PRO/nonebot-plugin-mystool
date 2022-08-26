"""
### 工具函数
"""
import hashlib
import json
import random
import string
import time
import traceback
import uuid
from typing import Dict, Union
from urllib.parse import urlencode

import httpx
import nonebot
import ntplib
import tenacity
from nonebot.log import logger

from .config import mysTool_config as conf

driver = nonebot.get_driver()


class NtpTime:
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


def custom_attempt_times(retry: bool):
    """
    自定义的重试机制停止条件\n
    根据是否要重试的bool值，给出相应的`tenacity.stop_after_attempt`对象
    >>> retry == True #重试次数达到配置中 MAX_RETRY_TIMES 时停止
    >>> retry == False #执行次数达到1时停止，即不进行重试
    """
    if retry:
        return tenacity.stop_after_attempt(conf.MAX_RETRY_TIMES + 1)
    else:
        return tenacity.stop_after_attempt(1)


@driver.on_startup
def ntp_time_sync():
    """
    启动时校对互联网时间
    """
    NtpTime.time_offset = 0
    try:
        for attempt in tenacity.Retrying(stop=custom_attempt_times(True)):
            with attempt:
                logger.info(conf.LOG_HEAD + "正在校对互联网时间")
                try:
                    NtpTime.time_offset = ntplib.NTPClient().request(
                        conf.NTP_SERVER).tx_time - time.time()
                except:
                    logger.warning(conf.LOG_HEAD +
                                   "校对互联网时间失败，正在重试")
                    raise
    except tenacity.RetryError:
        logger.warning(conf.LOG_HEAD + "校对互联网时间失败，改为使用本地时间")


def generateDeviceID() -> str:
    """
    生成随机的x-rpc-device_id
    """
    return str(uuid.uuid4()).upper()


def cookie_str_to_dict(cookie_str: str) -> Dict[str, str]:
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


def cookie_dict_to_str(cookie_dict: Dict[str, str]) -> str:
    """
    将字符串Cookie转换为字典Cookie
    """
    cookie_str = ""
    for key in cookie_dict:
        cookie_str += (key + "=" + cookie_dict[key] + ";")
    return cookie_str


def generateDS(data: Union[str, dict, list] = "", params: Union[str, dict] = ""):
    """
    获取Headers中所需DS

    参数:
        `data`: 可选，网络请求中需要发送的数据
        `params`: 可选，URL参数
    """
    # DS 加密算法:
    # https://github.com/y1ndan/genshinhelper2/pull/34/commits/fd58f253a86d13dc24aaaefc4d52dd8e27aaead1
    if data == "" and params == "":
        t = str(int(NtpTime.time()))
        a = "".join(random.sample(
            string.ascii_lowercase + string.digits, 6))
        re = hashlib.md5(
            f"salt=9nQiU3AV0rJSIBWgdynfoGMGKaklfbM7&t={t}&r={a}".encode()).hexdigest()
        return f"{t},{a},{re}"
    else:
        if not isinstance(data, str):
            data = json.dumps(data)
        if not isinstance(params, str):
            params = urlencode(params)
        t = str(int(NtpTime.time()))
        r = str(random.randint(100001, 200000))
        add = f'&b={data}&q={params}'
        c = hashlib.md5(("salt=t0qEgfub6cvueAPgR5m9aQWWVciEer7v&t=" +
                        t + "&r=" + r + add).encode()).hexdigest()
        return f"{t},{r},{c}"


async def get_file(url: str, retry: bool = True):
    """
    下载文件

    参数:
        `retry`: 是否允许重试
    """
    try:
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                async with httpx.AsyncClient() as client:
                    res = await client.get(url, timeout=conf.TIME_OUT, follow_redirects=True)
                return res.content
    except tenacity.RetryError:
        logger.error(conf.LOG_HEAD + "下载文件 - {} 失败".format(url))
        logger.debug(conf.LOG_HEAD + traceback.format_exc())


def check_login(response: str):
    """
    通过网络请求返回的数据，检查是否登录失效
    """
    try:
        res_dict = json.loads(response)
        if "message" in res_dict:
            response: str = res_dict["message"]
            for string in ("Please login", "登录失效"):
                if response.find(string) != -1:
                    return False
            return True
    except json.JSONDecodeError and KeyError:
        return True
