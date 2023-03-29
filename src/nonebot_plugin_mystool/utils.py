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
from typing import (TYPE_CHECKING, Any, Dict, List, Literal,
                    Union)
from urllib.parse import urlencode

import httpx
import nonebot
import nonebot.log
import nonebot.plugin
import ntplib
import tenacity
from nonebot.log import logger

from .config import config as conf

if TYPE_CHECKING:
    from loguru import Logger

driver = nonebot.get_driver()


class CommandBegin:
    """
    命令开头字段
    （包括例如'/'和插件命令起始字段例如'mystool'）
    已重写__str__方法
    """
    string = ""
    '''命令开头字段（包括例如'/'和插件命令起始字段例如'mystool'）'''

    @classmethod
    def set_command_begin(cls):
        """
        机器人启动时设置命令开头字段
        """
        if nonebot.get_driver().config.command_start:
            cls.string = list(nonebot.get_driver().config.command_start)[0] + conf.COMMAND_START
        else:
            cls.string = conf.COMMAND_START

    @classmethod
    def __str__(cls):
        return cls.string


def get_last_command_sep():
    """
    获取第最后一个命令分隔符
    """
    if driver.config.command_sep:
        return list(driver.config.command_sep)[-1]


driver.on_startup(CommandBegin.set_command_begin)
COMMAND_BEGIN = CommandBegin()
'''命令开头字段（包括例如'/'和插件命令起始字段例如'mystool'）'''


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
"""本插件所用日志记录器对象（包含输出到文件）"""

PLUGIN = nonebot.plugin.get_plugin(conf.PLUGIN_NAME)
'''本插件数据'''

if not PLUGIN:
    logger.warning("插件数据(Plugin)获取失败，如果插件是从本地加载的，需要修改配置文件中 PLUGIN_NAME 为插件目录，否则将导致无法获取插件帮助信息等")


class NtpTime:
    """
    `NtpTime.time() #获取校准后的时间（如果校准成功）`
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

    :param retry True - 重试次数达到配置中 MAX_RETRY_TIMES 时停止; False - 执行次数达到1时停止，即不进行重试
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
        logger.warning(f"{conf.LOG_HEAD}校对互联网时间失败")


def generate_device_id() -> str:
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


def generate_ds(data: Union[str, dict, list] = "", params: Union[str, dict] = "",
                platform: Literal["ios", "android"] = "ios"):
    """
    获取Headers中所需DS

    :param data: 可选，网络请求中需要发送的数据
    :param params: 可选，URL参数
    :param platform: 可选，平台，ios或android
    """
    if data == "" and params == "":
        if platform == "ios":
            salt = conf.salt.SALT_IOS
        else:
            salt = conf.salt.SALT_ANDROID
        t = str(int(NtpTime.time()))
        a = "".join(random.sample(
            string.ascii_lowercase + string.digits, 6))
        re = hashlib.md5(
            f"salt={salt}&t={t}&r={a}".encode()).hexdigest()
        return f"{t},{a},{re}"
    else:
        salt = conf.salt.SALT_DATA
        if not isinstance(data, str):
            data = json.dumps(data)
        if not isinstance(params, str):
            params = urlencode(params)
            salt = conf.salt.SALT_PARAMS
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


def check_ds(response: str):
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


def blur_phone(phone: Union[str, int]) -> str:
    """
    模糊手机号

    :param phone: 手机号
    :return: 模糊后的手机号
    """
    if isinstance(phone, int):
        phone = str(phone)
    return f"{phone[:3]}****{phone[-4:]}"


class Subscribe:
    """
    在线配置相关(需实例化)
    """
    URL = os.path.join(
        conf.GITHUB_PROXY, "https://github.com/Ljzd-PRO/nonebot-plugin-mystool/raw/dev/subscribe/config.json")
    conf_list: List[Dict[str, Any]] = []
    '''当前插件版本可用的配置资源'''

    def __init__(self):
        self.index = 0

    @classmethod
    async def download(cls) -> bool:
        """
        读取在线配置资源
        :return: 是否成功
        """
        try:
            for attempt in tenacity.Retrying(stop=custom_attempt_times(True)):
                with attempt:
                    file = await get_file(cls.URL)
                    file = json.loads(file.decode())
                    if not file:
                        return False
                    cls.conf_list = list(
                        filter(lambda co: PLUGIN.metadata.extra["version"] in co["version"], file))
                    cls.conf_list.sort(
                        key=lambda co: conf["time"], reverse=True)
                    return True
        except (json.JSONDecodeError, KeyError):
            logger.error(f"{conf.LOG_HEAD}获取在线配置资源 - 解析文件失败")
            return False

    async def load(self, force: bool = False) -> bool:
        """
        优先加载来自网络的配置，若获取失败，则返回本地默认配置。\n
        若下载失败返回`False`

        :param force: 是否强制在线读取配置，而不使用本地缓存的
        """
        success = True
        if not Subscribe.conf_list or force or self.index >= len(Subscribe.conf_list):
            logger.info(f"{conf.LOG_HEAD}读取配置 - 开始下载配置...")
            success = await self.download()
            self.index = 0
        if not success:
            return False
        else:
            conf.parse_obj(Subscribe.conf_list[self.index]["config"])
            self.index += 1
            return True
