"""
### 工具函数
"""
import hashlib
import io
import json
import random
import string
import time
import uuid
from typing import (TYPE_CHECKING, Dict, Literal,
                    Union, Optional)
from urllib.parse import urlencode

import httpx
import nonebot
import nonebot.log
import nonebot.plugin
import tenacity
from nonebot import Adapter, Bot
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import MessageEvent as OnebotV11MessageEvent, PrivateMessageEvent, GroupMessageEvent, \
    Adapter as OnebotV11Adapter, Bot as OnebotV11Bot
from nonebot.adapters.qqguild import DirectMessageCreateEvent, MessageCreateEvent, \
    Adapter as QQGuildAdapter, Bot as QQGuildBot, MessageSegment as QQGuildMessageSegment, Message as QQGuildMessage
from nonebot.adapters.qqguild.api import DMS
from nonebot.adapters.qqguild.exception import ActionFailed
from nonebot.internal.matcher import Matcher
from nonebot.log import logger
from qrcode import QRCode

from .data_model import GeetestResult
from .plugin_data import PluginDataManager, Preference

if TYPE_CHECKING:
    from loguru import Logger

_conf = PluginDataManager.plugin_data

GeneralMessageEvent = Union[OnebotV11MessageEvent, MessageCreateEvent, DirectMessageCreateEvent]
"""消息事件类型"""
GeneralPrivateMessageEvent = Union[PrivateMessageEvent, DirectMessageCreateEvent]
"""私聊消息事件类型"""
GeneralGroupMessageEvent = Union[GroupMessageEvent, MessageCreateEvent]
"""群聊消息事件类型"""


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


def set_logger(logger: "Logger"):
    """
    给日志记录器对象增加输出到文件的Handler
    """
    # 根据"name"筛选日志，如果在 plugins 目录加载，则通过 LOG_HEAD 识别
    # 如果不是插件输出的日志，但是与插件有关，则也进行保存
    logger.add(_conf.preference.log_path, diagnose=False, format=nonebot.log.default_format,
               filter=lambda record: record["name"] == _conf.preference.plugin_name or
                                     (_conf.preference.log_head != "" and record["message"].find(
                                         _conf.preference.log_head) == 0) or
                                     record["message"].find(f"plugins.{_conf.preference.plugin_name}") != -1,
               rotation=_conf.preference.log_rotation)
    return logger


logger = set_logger(logger)
"""本插件所用日志记录器对象（包含输出到文件）"""

PLUGIN = nonebot.plugin.get_plugin(_conf.preference.plugin_name)
'''本插件数据'''

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
        t = str(int(time.time()))
        a = "".join(random.sample(
            string.ascii_lowercase + string.digits, 6))
        re = hashlib.md5(
            f"salt={salt}&t={t}&r={a}".encode()).hexdigest()
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
        return f"{t},{r},{c}"


async def get_validate(gt: str = None, challenge: str = None, retry: bool = True):
    """
    使用打码平台获取人机验证validate

    :param gt: 验证码gt
    :param challenge: challenge
    :param retry: 是否允许重试
    :return: 如果配置了平台URL，且 gt, challenge 不为空，返回 GeetestResult
    """
    content = _conf.preference.geetest_json or Preference().geetest_json
    for key, value in content.items():
        if isinstance(value, str):
            content[key] = value.format(gt=gt, challenge=challenge)

    if gt and challenge and _conf.preference.geetest_url:
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
                        return GeetestResult(validate=geetest_data['data']['validate'], seccode="")
        except tenacity.RetryError:
            logger.exception(f"{_conf.preference.log_head}获取人机验证validate失败")
    else:
        return GeetestResult("", "")


def generate_seed_id(length: int = 8) -> str:
    """
    生成随机的 seed_id（即长度为8的十六进制数）

    :param length: 16进制数长度
    """
    max_num = int("FF" * length, 16)
    return hex(random.randint(0, max_num))[2:]


def generate_fp_locally(length: int = 13):
    """
    于本地生成 device_fp

    :param length: device_fp 长度
    """
    characters = string.digits + "abcdef"
    return ''.join(random.choices(characters, k=length))


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


def generate_qr_img(data: str):
    """
    生成二维码图片

    :param data: 二维码数据

    >>> b = generate_qr_img("https://github.com/Ljzd-PRO/nonebot-plugin-mystool")
    >>> isinstance(b, bytes)
    """
    qr_code = QRCode()
    qr_code.add_data(data)
    qr_code.make()
    image = qr_code.make_image()
    image_bytes = io.BytesIO()
    image.save(image_bytes)
    return image_bytes.getvalue()


async def send_private_msg(
        user_id: str,
        message: Union[str, Message],
        use: Union[Bot, Adapter] = None,
        guild_id: int = None
):
    """
    主动发送私信消息

    :param user_id: 目标用户ID
    :param message: 消息内容
    :param use: 使用的Bot或Adapter，为None则使用所有Bot
    :param guild_id: 用户所在频道ID，为None则从用户数据中获取
    :return: 是否发送成功
    """
    if isinstance(use, (OnebotV11Bot, QQGuildBot)):
        bots = [use]
    elif isinstance(use, (OnebotV11Adapter, QQGuildAdapter)):
        bots = use.bots.values()
    else:
        bots = nonebot.get_bots().values()
    if isinstance(use, (OnebotV11Bot, OnebotV11Adapter)):
        for bot in bots:
            await bot.send_private_msg(user_id=int(user_id), message=message)
        return True
    elif isinstance(use, (QQGuildBot, QQGuildAdapter)):
        message = QQGuildMessageSegment.text(message) if isinstance(message, str) else message
        message = message if isinstance(message, QQGuildMessage) else QQGuildMessage(message)

        content = message.extract_content() or None
        if embed := (message["embed"] or None):
            embed = embed[-1].data["embed"]
        if ark := (message["ark"] or None):
            ark = ark[-1].data["ark"]
        if image := (message["attachment"] or None):
            image = image[-1].data["url"]
        if file_image := (message["file_image"] or None):
            file_image = file_image[-1].data["content"]
        if markdown := (message["markdown"] or None):
            markdown = markdown[-1].data["markdown"]
        if reference := (message["reference"] or None):
            reference = reference[-1].data["reference"]

        if guild_id is None:
            if user := _conf.users.get(user_id):
                if not (guilds := user.qq_guilds.get(user_id)):
                    logger.warning(f"{_conf.preference.log_head}用户 {user_id} 数据中没有任何频道ID")
                    return False
                guild_ids = iter(guilds)
            else:
                logger.warning(f"{_conf.preference.log_head}用户数据中不存在用户 {user_id}，无法获取频道ID")
                return False
        else:
            guild_ids = iter([guild_id])

        while (guild_id := next(guild_ids, None)) is not None:
            try:
                for bot in bots:
                    dms: DMS = await bot.post_dms(recipient_id=user_id, source_guild_id=guild_id)
                    await bot.post_dms_messages(
                        guild_id=dms.guild_id,  # type: ignore
                        content=content,
                        embed=embed,  # type: ignore
                        ark=ark,  # type: ignore
                        image=image,  # type: ignore
                        file_image=file_image,  # type: ignore
                        markdown=markdown,  # type: ignore
                        message_reference=reference,  # type: ignore
                    )
            except ActionFailed:
                logger.exception(
                    f"{_conf.preference.log_head}尝试主动发送私信消息失败。"
                    f"频道ID：{guild_id}，用户ID：{user_id}，消息内容：\n"
                    f"{message}"
                )
            else:
                return True
        return False


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
