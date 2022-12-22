"""
### 工具函数
"""
import hashlib
import json
import os
import random
import string
import time
import traceback
import uuid
from typing import (TYPE_CHECKING, Any, Dict, List, Literal, NewType, Tuple,
                    Union)
from urllib.parse import urlencode

import httpx
import nonebot
import nonebot.log
import nonebot.plugin
import ntplib
import tenacity
from nonebot.log import logger

from .config import mysTool_config as conf

if TYPE_CHECKING:
    from loguru import Logger

driver = nonebot.get_driver()

PLUGIN = nonebot.plugin.get_plugin(conf.PLUGIN_NAME)
'''本插件数据'''


def set_logger(logger: "Logger"):
    """
    给日志记录器对象增加输出到文件的Handler
    """
    # 根据"name"筛选日志，如果在 plugins 目录加载，则通过 LOG_HEAD 识别
    # 如果不是插件输出的日志，但是与插件有关，则也进行保存
    logger.add(conf.LOG_PATH, diagnose=False, format=nonebot.log.default_format,
               filter=lambda record: record["name"] == conf.PLUGIN_NAME or
                                     (conf.LOG_HEAD != "" and record["message"].find(conf.LOG_HEAD) == 0) or
                                     record["message"].find(f"plugins.{conf.PLUGIN_NAME}") != -1,
               rotation=conf.LOG_ROTATION)
    return logger


logger = set_logger(logger)


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
                logger.info(f"{conf.LOG_HEAD}正在校对互联网时间")
                try:
                    NtpTime.time_offset = ntplib.NTPClient().request(
                        conf.NTP_SERVER).tx_time - time.time()
                    format_offset = "%.2f" % NtpTime.time_offset
                    logger.info(
                        f"{conf.LOG_HEAD}系统时间与网络时间的误差为 {format_offset} 秒")
                    if abs(NtpTime.time_offset) > 0.2:
                        logger.warning(
                            f"{conf.LOG_HEAD}系统时间与网络时间误差偏大，可能影响商品兑换成功概率，建议同步系统时间")
                except Exception:
                    logger.warning(f"{conf.LOG_HEAD}校对互联网时间失败，正在重试")
                    raise
    except tenacity.RetryError:
        logger.warning(f"{conf.LOG_HEAD}校对互联网时间失败，改为使用本地时间")


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


def generateDS(data: Union[str, dict, list] = "", params: Union[str, dict] = "",
               platform: Literal["ios", "android"] = "ios"):
    """
    获取Headers中所需DS

    :param data: 可选，网络请求中需要发送的数据
    :param params: 可选，URL参数
    :param platform: 可选，平台，ios或android
    """
    if data == "" and params == "":
        if platform == "ios":
            salt = conf.SALT_IOS
        else:
            salt = conf.SALT_ANDROID
        t = str(int(NtpTime.time()))
        a = "".join(random.sample(
            string.ascii_lowercase + string.digits, 6))
        re = hashlib.md5(
            f"salt={salt}&t={t}&r={a}".encode()).hexdigest()
        return f"{t},{a},{re}"
    else:
        salt = conf.SALT_DATA
        if not isinstance(data, str):
            data = json.dumps(data)
        if not isinstance(params, str):
            params = urlencode(params)
            salt = conf.SALT_PARAMS
        t = str(int(time.time()))
        r = str(random.randint(100000, 200000))
        c = hashlib.md5(
            f"salt={salt}&t={t}&r={r}&b={data}&q={params}".encode()).hexdigest()
        return f"{t},{r},{c}"


async def get_file(url: str, retry: bool = True):
    """
    下载文件

    :param url: 文件URL
    :param retry: 是否允许重试
    :return: 文件数据
    """
    try:
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry),
                                                    wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                async with httpx.AsyncClient() as client:
                    res = await client.get(url, timeout=conf.TIME_OUT, follow_redirects=True)
                return res.content
    except tenacity.RetryError:
        logger.error(f"{conf.LOG_HEAD}下载文件 - {url} 失败")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")


def check_login(response: str):
    """
    通过网络请求返回的数据，检查是否登录失效

    如果返回数据为`None`，返回`True`

    :param response: 网络请求返回的数据
    :return: 是否登录失效
    """
    try:
        if response is None:
            return True
        res_dict = json.loads(response)
        if "message" in res_dict:
            response: str = res_dict["message"]
            for string in ("Please login", "登录失效", "尚未登录"):
                if response.find(string) != -1:
                    return False
            return True
    except (json.JSONDecodeError, KeyError):
        return True


def check_DS(response: str):
    """
    通过网络请求返回的数据，检查Header中DS是否有效

    如果返回数据为`None`，返回`True`

    :param response: 网络请求返回的数据
    :return: DS是否有效
    """
    try:
        if response is None:
            return True
        res_dict = json.loads(response)
        if res_dict["message"] == "invalid request":
            return False
        else:
            return True
    except (json.JSONDecodeError, KeyError):
        return True


class Subscribe:
    """
    在线配置相关(需实例化)
    """
    ConfigClass = NewType("ConfigClass", str)
    Attribute = NewType("Attribute", str)
    URL = os.path.join(
        conf.GITHUB_PROXY, "https://github.com/Ljzd-PRO/nonebot-plugin-mystool/raw/dev/subscribe/config.json")
    conf_list: List[Dict[str, Any]] = []
    '''当前插件版本可用的配置资源'''

    async def download(self) -> bool:
        """
        读取在线配置资源
        :return: 是否成功
        """
        try:
            for attempt in tenacity.Retrying(stop=custom_attempt_times(True)):
                with attempt:
                    file = await get_file(self.URL)
                    file = json.loads(file.decode())
                    if not file:
                        return False
                    self.conf_list = list(
                        filter(lambda conf: PLUGIN.metadata.extra["version"] in conf["version"], file))
                    self.conf_list.sort(
                        key=lambda conf: conf["time"], reverse=True)
                    return True
        except (json.JSONDecodeError, KeyError):
            logger.error(f"{conf.LOG_HEAD}获取在线配置资源 - 解析文件失败")
            return False

    async def get(self, key: Tuple[ConfigClass, Attribute], index: int = 0, force: bool = False) -> Union[Any, None]:
        """
        优先读取来自网络的配置，若获取失败，则返回本地默认配置。\n
        若找不到属性或`index`超出范围，返回`None`

        :param key: (配置类名, 属性名)
        :param index: 配置在`Subscribe.conf_list`中的位置
        :param force: 是否强制在线读取配置，而不使用本地缓存的
        :return: 属性值
        """
        success = True
        if not self.conf_list or force:
            logger.info(f"{conf.LOG_HEAD}读取配置 - 开始下载配置...")
            success = await self.download()

        if not success or index >= len(self.conf_list) or index < 0:
            if not success:
                logger.error(f"{conf.LOG_HEAD}读取配置 - 读取在线配置失败，转为使用默认配置")
            if key[0] == "DeviceConfig":
                try:
                    return list(filter(lambda attr: attr == key[1], dir(conf.device)))[0]
                except IndexError:
                    return
            else:
                try:
                    return list(filter(lambda attr: attr == key[1], dir(conf)))[0]
                except IndexError:
                    return

        return self.conf_list[index]["config"][key[0]][key[1]]
