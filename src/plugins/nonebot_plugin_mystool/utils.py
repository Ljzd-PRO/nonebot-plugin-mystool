"""
### 工具函数
"""
import hashlib
import json
import random
import string
import time
import uuid
from typing import (TYPE_CHECKING, Dict, Literal,
                    Union, Optional)
from urllib.parse import urlencode
from nonebot.adapters.onebot.v11 import (Bot, MessageSegment,
                                         PrivateMessageEvent, GroupMessageEvent, Message, MessageEvent)
from nonebot.adapters.console import (MessageEvent as ConsoleMessageEvent,
                                      Message as ConsoleMessage)
from nonebot.adapters.qqguild import (MessageEvent as GuildMessageEvent,
                                      Message as GuildMessage,
                                      MessageCreateEvent as GuildMessageCreateEvent)
from nonebot.adapters.telegram import Message as TelegramMessage
from nonebot.adapters.telegram.event import (MessageEvent as TelegramMessageEvent,
                                            GroupMessageEvent as TelegramGroupMessageEvent,
                                            PrivateMessageEvent as TelegramPrivateMessageEvent,
                                            Message as TelegramMessage)
import httpx
import nonebot
import nonebot.log
import nonebot.plugin
import ntplib
import tenacity
from nonebot.internal.matcher import Matcher
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.internal.params import Depends
from nonebot.consts import (
    PREFIX_KEY,
    CMD_ARG_KEY
)

from .data_model import GeetestResult, GeetestResultV4
from .plugin_data import PluginDataManager

if TYPE_CHECKING:
    from loguru import Logger

_conf = PluginDataManager.plugin_data_obj

URL_BBS_GET_CAPTCHA = "https://bbs-api.miyoushe.com/misc/api/createVerification?is_high=true"
URL_BBS_CAPTCHA_VERIFY = "https://bbs-api.miyoushe.com/misc/api/verifyVerification"

ALL_MessageEvent = Union[MessageEvent, ConsoleMessageEvent, GuildMessageCreateEvent, TelegramMessageEvent]
ALL_P_MessageEvent = Union[PrivateMessageEvent, ConsoleMessageEvent, GuildMessageCreateEvent, TelegramPrivateMessageEvent]
ALL_G_MessageEvent = Union[GroupMessageEvent, ConsoleMessageEvent, GuildMessageCreateEvent, TelegramGroupMessageEvent]
ALL_Message = Union[Message, ConsoleMessage, GuildMessage, TelegramMessage]

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
            cls.string = list(nonebot.get_driver().config.command_start)[0] + _conf.preference.command_start
        else:
            cls.string = _conf.preference.command_start

    @classmethod
    def __str__(cls):
        return cls.string


def get_last_command_sep():
    """
    获取第最后一个命令分隔符
    """
    if nonebot.get_driver().config.command_sep:
        return list(nonebot.get_driver().config.command_sep)[-1]


COMMAND_BEGIN = CommandBegin()
'''命令开头字段（包括例如'/'和插件命令起始字段例如'mystool'）'''

@nonebot.get_driver().on_startup
def set_logger():
    """
    给日志记录器对象增加输出到文件的Handler
    """
    # 根据"name"筛选日志，如果在 plugins 目录加载，则通过 LOG_HEAD 识别
    # 如果不是插件输出的日志，但是与插件有关，则也进行保存
    logger.add(_conf.preference.log_path, diagnose=False, 
               format="[<lvl>{level}</lvl>] "
                        "<cyan>{module}</cyan>.<cyan>{function}</cyan>"
                        ":<cyan>{line}</cyan> - "
                        "<level>{message}</level>",
               filter=lambda record: record["name"] == _conf.preference.plugin_name or
                                     (_conf.preference.log_head != "" and record["message"].find(
                                         _conf.preference.log_head) == 0) or
                                     record["message"].find(f"plugins.{_conf.preference.plugin_name}") != -1,
               rotation=_conf.preference.log_rotation)
    return logger


#logger = set_logger()
"""本插件所用日志记录器对象（包含输出到文件）"""

PLUGIN = nonebot.plugin.get_plugin(_conf.preference.plugin_name)
'''本插件数据'''
logger.info(PLUGIN.metadata)
if not PLUGIN:
    logger.warning(
        "插件数据(Plugin)获取失败，如果插件是从本地加载的，需要修改配置文件中 PLUGIN_NAME 为插件目录，否则将导致无法获取插件帮助信息等")


def custom_attempt_times(retry: bool):
    """
    自定义的重试机制停止条件\n
    根据是否要重试的bool值，给出相应的`tenacity.stop_after_attempt`对象

    :param retry True - 重试次数达到配置中 MAX_RETRY_TIMES 时停止; False - 执行次数达到1时停止，即不进行重试
    """
    if retry:
        return tenacity.stop_after_attempt(_conf.preference.max_retry_times + 1)
    else:
        return tenacity.stop_after_attempt(1)


def get_async_retry(retry: bool):
    """
    获取异步重试装饰器

    :param retry: True - 重试次数达到偏好设置中 max_retry_times 时停止; False - 执行次数达到1时停止，即不进行重试
    """
    return tenacity.AsyncRetrying(
        stop=custom_attempt_times(retry),
        retry=tenacity.retry_if_exception_type(BaseException),
        wait=tenacity.wait_fixed(_conf.preference.retry_interval),
    )


class NtpTime:
    """
    NTP时间校准相关
    """
    time_offset = 0
    """本地时间与互联网时间的偏差"""

    @classmethod
    def sync(cls):
        """
        校准时间
        """
        if _conf.preference.enable_ntp_sync:
            if not _conf.preference.ntp_server:
                logger.error("开启了互联网时间校对，但未配置NTP服务器 preference.ntp_server，放弃时间同步")
                return False
            try:
                for attempt in get_async_retry(True):
                    with attempt:
                        cls.time_offset = ntplib.NTPClient().request(
                            _conf.preference.ntp_server).tx_time - time.time()
            except tenacity.RetryError:
                logger.exception("校对互联网时间失败，改为使用本地时间")
                return False
            logger.info("互联网时间校对完成")
            return True
        else:
            logger.info("未开启互联网时间校对，跳过时间同步")
            return True

    @classmethod
    def time(cls) -> float:
        """
        获取校准后的时间（如果校准成功）
        """
        return time.time() + cls.time_offset


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


def generate_ds(data: Union[str, dict, list, None] = None, params: Union[str, dict, None] = None,
                platform: Literal["ios", "android"] = "ios", salt: Optional[str] = None):
    """
    获取Headers中所需DS

    :param data: 可选，网络请求中需要发送的数据
    :param params: 可选，URL参数
    :param platform: 可选，平台，ios或android
    :param salt: 可选，自定义salt
    """
    if data is None and params is None or \
            salt is not None and salt != _conf.salt_config.SALT_PROD:
        if platform == "ios":
            salt = salt or _conf.salt_config.SALT_IOS
        else:
            salt = salt or _conf.salt_config.SALT_ANDROID
        t = str(int(NtpTime.time()))
        a = "".join(random.sample(
            string.ascii_lowercase + string.digits, 6))
        re = hashlib.md5(
            f"salt={salt}&t={t}&r={a}".encode()).hexdigest()
        #logger.debug(f"salt={salt}&t={t}&r={a}")
        return f"{t},{a},{re}"
    else:
        if params:
            salt = _conf.salt_config.SALT_PARAMS if not salt else salt
        else:
            salt = _conf.salt_config.SALT_DATA if not salt else salt

        if not data:
            if salt == _conf.salt_config.SALT_PROD:
                data = {}
            else:
                data = ""
        if not params:
            params = ""

        if not isinstance(data, str):
            data = json.dumps(data)
        if not isinstance(params, str):
            params = urlencode(params)

        t = str(int(time.time()))
        r = str(random.randint(100000, 200000))
        c = hashlib.md5(
            f"salt={salt}&t={t}&r={r}&b={data}&q={params}".encode()).hexdigest()
        #logger.debug(f"salt={salt}&t={t}&r={r}&b={data}&q={params}")
        return f"{t},{r},{c}"


async def get_validate(gt: str = None, challenge: str = None, geetest_type: str = "") -> GeetestResult:
    """
    使用打码平台获取人机验证validate

    :param gt: 验证码gt
    :param challenge: challenge
    :param retry: 是否允许重试
    :return: 如果配置了平台URL，且 gt, challenge 不为空，返回 GeetestResult
    """
    content = {
        "gt": gt,
        "challenge": challenge
    }
    if gt and challenge and _conf.preference.geetest_url:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    _conf.preference.geetest_url,
                    timeout=60,
                    json=content)
            geetest_data = res.json()
            logger.info(f"打码:{geetest_data}")
            validate=geetest_data['data']['validate']
            return GeetestResult(validate=validate, challenge=challenge)
        except tenacity.RetryError:
            logger.exception(f"{_conf.preference.log_head}获取人机验证validate失败")
    return GeetestResult("", "")

async def get_validate_fromv4(captcha_id: str = None, mmt_key: str = None, retry: bool = True):
    """
    使用打码平台获取人机验证极验v4验证码

    :param captcha_id: captcha_id
    :param mmt_key: mmt_key
    :param retry: 是否允许重试
    :return: 如果配置了平台URL，且 gt, challenge 不为空，返回 GeetestResult
    """
    content = {
        "gt": captcha_id,
        "mmt_key": mmt_key,
        "type": "gt4"
    }
    for key, value in content.items():
        if isinstance(value, str):
            content[key] = value.format(captcha_id=captcha_id, mmt_key=mmt_key)

    if captcha_id and mmt_key and _conf.preference.geetest_url:
        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    async with httpx.AsyncClient() as client:
                        res = await client.post(
                            _conf.preference.geetest_url,
                            timeout=60,
                            json=content)
                    geetest_data = res.json()
                    if geetest_data['data']['result'] != 'fail':
                        return GeetestResultV4.parse_obj(geetest_data['data']['seccode'])
        except tenacity.RetryError:
            logger.exception(f"{_conf.preference.log_head}获取人机验证validate失败")
    else:
        return None
    
async def get_pass_challenge(headers:dict, cookies: dict) -> Optional[tuple[str, str]]:
    """
    使用打码平台获取人机验证validate并验证，返回通过验证的challenge
    """
    async with httpx.AsyncClient() as client:
        headers["DS"] = generate_ds(platform="android")
        req = await client.get(url=URL_BBS_GET_CAPTCHA, headers=headers, cookies=cookies)
        data = req.json()
        if data["retcode"] != 0:
            return None
        geetest_result = await get_validate(gt=data["data"]["gt"], challenge=data["data"]["challenge"])
        if geetest_result.validate:
            check_req = await client.post(url=URL_BBS_CAPTCHA_VERIFY, headers=headers, cookies=cookies,
                                    json={"geetest_challenge": geetest_result.challenge,
                                        "geetest_seccode": geetest_result.validate + "|jordan",
                                        "geetest_validate": geetest_result.validate})
            check = check_req.json()
            logger.info(f"CL验证{check}")
            if check["retcode"] == 0:
                return check["data"]["challenge"]
    return None
    
async def get_file(url: str, retry: bool = True):
    """
    下载文件

    :param url: 文件URL
    :param retry: 是否允许重试
    :return: 文件数据
    """
    try:
        async for attempt in get_async_retry(retry):
            with attempt:
                async with httpx.AsyncClient() as client:
                    res = await client.get(url, timeout=_conf.preference.timeout, follow_redirects=True)
                return res.content
    except tenacity.RetryError:
        logger.exception(f"{_conf.preference.log_head}下载文件 - {url} 失败")

def blur_phone(phone: Union[str, int]) -> str:
    """
    模糊手机号

    :param phone: 手机号
    :return: 模糊后的手机号
    """
    if isinstance(phone, int):
        phone = str(phone)
    return f"{phone[:3]}****{phone[-4:]}"

# TODO: 一个用于构建on_command事件相应器的函数，
#  将使用偏好设置里的priority优先级和block设置，
#  可能可以作为装饰器使用
#   （需要先等用户数据改用Pydantic作为数据模型）
def command_matcher(command: str, priority: int = None, block: bool = None) -> Matcher:
    """
    用于构建on_command事件相应器的函数，
    将使用偏好设置里的priority优先级和block设置

    :param command: 指令名
    :param priority: 优先级，为 None 则读取偏好设置
    :param block: 是否阻塞，为 None 则读取偏好设置
    :return: 事件响应器
    """
    ...

def _command_args(state: T_State) -> Optional[list[str]]:
    args = str(state[PREFIX_KEY][CMD_ARG_KEY]).strip().split(" ")
    return args if args!= [''] else [state["default_args"]]

def CommandArgs() -> Optional[list[str]]:
    """
    消息命令参数

    :param message: 默认消息
    """
    return Depends(_command_args)
