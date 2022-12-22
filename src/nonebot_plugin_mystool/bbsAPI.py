"""
### 米游社其他API
"""
import traceback
from typing import Dict, List, Literal, NewType, Tuple, Union

import httpx
import nonebot
import tenacity

from .config import mysTool_config as conf
from .data import UserAccount
from .utils import (Subscribe, check_DS, check_login, custom_attempt_times,
                    generateDeviceID, generateDS, logger)

URL_ACTION_TICKET = "https://api-takumi.mihoyo.com/auth/api/getActionTicketBySToken?action_type=game_role&stoken={stoken}&uid={bbs_uid}"
URL_GAME_RECORD = "https://api-takumi-record.mihoyo.com/game_record/card/wapi/getGameRecordCard?uid={}"
URL_GAME_LIST = "https://bbs-api.mihoyo.com/apihub/api/getGameList"
URL_MYB = "https://api-takumi.mihoyo.com/common/homutreasure/v1/web/user/point?app_id=1&point_sn=myb"
URL_DEVICE_LOGIN = "https://bbs-api.mihoyo.com/apihub/api/deviceLogin"
URL_DEVICE_SAVE = "https://bbs-api.mihoyo.com/apihub/api/saveDevice"
URL_GENSHIN_STATUS_WIDGET = "https://api-takumi-record.mihoyo.com/game_record/app/card/api/getWidgetData?game_id=2"
URL_GENSHEN_STATUS_BBS = "https://api-takumi-record.mihoyo.com/game_record/app/genshin/api/dailyNote?role_id={game_uid}&server={region}"

HEADERS_ACTION_TICKET = {
    "Host": "api-takumi.mihoyo.com",
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_MOBILE,
    "User-Agent": conf.device.USER_AGENT_OTHER,
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
HEADERS_GAME_RECORD = {
    "Host": "api-takumi-record.mihoyo.com",
    "Origin": "https://webstatic.mihoyo.com",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": conf.device.USER_AGENT_MOBILE,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Referer": "https://webstatic.mihoyo.com/",
    "Accept-Encoding": "gzip, deflate, br"
}
HEADERS_GAME_LIST = {
    "Host": "bbs-api.mihoyo.com",
    "DS": None,
    "Accept": "*/*",
    "x-rpc-device_id": generateDeviceID(),
    "x-rpc-client_type": "1",
    "x-rpc-channel": conf.device.X_RPC_CHANNEL,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION,
    "Referer": "https://app.mihoyo.com",
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_MOBILE,
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "User-Agent": conf.device.USER_AGENT_OTHER,
    "Connection": "keep-alive",
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_MOBILE
}
HEADERS_MYB = {
    "Host": "api-takumi.mihoyo.com",
    "Origin": "https://webstatic.mihoyo.com",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": conf.device.USER_AGENT_MOBILE,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Referer": "https://webstatic.mihoyo.com/",
    "Accept-Encoding": "gzip, deflate, br"
}
HEADERS_DEVICE = {
    "DS": None,
    "x-rpc-client_type": "2",
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION_ANDROID,
    "x-rpc-channel": conf.device.X_RPC_CHANNEL_ANDROID,
    "x-rpc-device_id": None,
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_ANDROID,
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_ANDROID,
    "Referer": "https://app.mihoyo.com",
    "Content-Type": "application/json; charset=UTF-8",
    "Host": "bbs-api.mihoyo.com",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "User-Agent": conf.device.USER_AGENT_ANDROID_OTHER
}
HEADERS_GENSHIN_STATUS_WIDGET = {
    "Host": "api-takumi-record.mihoyo.com",
    "DS": None,
    "Accept": "*/*",
    "x-rpc-device_id": None,
    "x-rpc-client_type": "1",
    "x-rpc-channel": "appstore",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_MOBILE,
    "Referer": "https://app.mihoyo.com",
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_MOBILE,
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "User-Agent": conf.device.USER_AGENT_WIDGET,
    "Connection": "keep-alive",
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION
}
HEADERS_GENSHIN_STATUS_BBS = {
    "DS": None,
    "x-rpc-device_id": None,
    "Accept": "application/json,text/plain,*/*",
    "Origin": "https://webstatic.mihoyo.com",
    "User-agent": conf.device.USER_AGENT_ANDROID,
    "Referer": "https://webstatic.mihoyo.com/",
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "X-Requested-With": "com.mihoyo.hyperion",
    "x-rpc-client_type": "5"
}


class BaseData:
    def __init__(self, data_dict: dict, error_info: str = "初始化对象: dict数据不正确") -> None:
        self.dict = data_dict
        try:
            for func in dir(self):
                if func.startswith("__"):
                    continue
                getattr(self, func)
        except KeyError and TypeError and ValueError:
            logger.error(f"{conf.LOG_HEAD}{error_info}")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")


class GameRecord(BaseData):
    """
    用户游戏数据
    """

    def __init__(self, gameRecord_dict: dict) -> None:
        BaseData.__init__(self, gameRecord_dict, "用户游戏数据 - 初始化对象: dict数据不正确")

    @property
    def regionName(self) -> str:
        """
        服务器区名
        """
        return self.dict["region_name"]

    @property
    def gameID(self) -> int:
        """
        游戏ID
        """
        return int(self.dict["game_id"])

    @property
    def level(self) -> int:
        """
        用户游戏等级
        """
        return int(self.dict["level"])

    @property
    def region(self) -> str:
        """
        服务器区号
        """
        return self.dict["region"]

    @property
    def uid(self) -> str:
        """
        用户游戏UID
        """
        return self.dict["game_role_id"]

    @property
    def nickname(self) -> str:
        """
        用户游戏昵称
        """
        return self.dict["nickname"]


class GameInfo(BaseData):
    """
    游戏信息数据
    """
    Abbr = NewType("Abbr", str)
    Full_Name = NewType("Full_Name", str)
    ABBR_TO_ID: Dict[int, Tuple[Abbr, Full_Name]] = {}
    '''
    游戏ID(gameID)与缩写和全称的对应关系
    >>> {游戏ID, (缩写, 全称)}
    '''

    def __init__(self, gameInfo_dict: dict) -> None:
        BaseData.__init__(self, gameInfo_dict, "游戏信息数据 - 初始化对象: dict数据不正确")

    @property
    def gameID(self) -> int:
        """
        游戏ID
        """
        return self.dict["id"]

    @property
    def appIcon(self) -> str:
        """
        游戏App图标链接(大)
        """
        return self.dict["app_icon"]

    @property
    def opName(self) -> str:
        """
        游戏代号(英文数字, 例如hk4e)
        """
        return self.dict["op_name"]

    @property
    def enName(self) -> str:
        """
        游戏代号2(英文数字, 例如ys)
        """
        return self.dict["en_name"]

    @property
    def miniIcon(self) -> str:
        """
        游戏图标链接(圆形, 小)
        """
        return self.dict["icon"]

    @property
    def name(self) -> str:
        """
        游戏名称
        """
        return self.dict["name"]


class GenshinStatus:
    """
    原神实时便笺数据
    """

    def __init__(self) -> None:
        self.name: str = ""
        '''游戏昵称'''
        self.gameUID: str = ""
        '''游戏UID'''
        self.region: str = ""
        '''游戏区服(如 "cn_gf01")'''
        self.level: int = -1
        '''游戏等级'''
        self.resin: int = -1
        '''当前树脂数量'''
        self.expedition: Tuple[int] = (-1,)
        '''探索派遣 `(进行中, 最多派遣数)`'''
        self.task: int = -1
        '''每日委托完成数'''
        self.coin: Tuple[int] = (-1,)
        '''洞天财瓮 `(未收取, 最多可容纳宝钱数)`'''
        self.transformer: str = ""
        '''参量质变仪'''

    def fromWidget(self, widget_dict):
        """
        从iOS小组件API的返回数据初始化

        :param widget_dict: iOS小组件API的返回数据
        """
        self.dict = widget_dict

        try:
            self.name: str = widget_dict["nickname"]
            self.gameUID: str = widget_dict["game_role_id"]
            self.region: str = widget_dict["region"]
            self.level: int = widget_dict["level"]

            for status in widget_dict["data"]:
                data: Tuple = tuple(
                    [value for value in status["value"].split("/")])
                if status["name"] == "原粹树脂":
                    self.resin = int(data[0])
                elif status["name"] == "探索派遣":
                    self.expedition = tuple(int(value) for value in data)
                elif status["name"] == "每日委托进度" or status["name"] == "每日委托奖励":
                    if data[0] == "尚未领取" or data[0] == "全部完成":
                        self.task = 4
                    else:
                        self.task = int(data[0])
                elif status["name"] == "洞天财瓮":
                    self.coin = tuple(int(value) for value in data)

            return self
        except KeyError and TypeError and ValueError:
            logger.error(f"{conf.LOG_HEAD}原神实时便笺数据 - 从小组件请求初始化对象: dict数据不正确")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")

    def fromBBS(self, bbs_dict, record: GameRecord):
        """
        从米游社内相关页面API的返回数据初始化

        :param bbs_dict: 米游社内相关页面API的返回数据
        :param record: 用户GameRecord对象
        """
        self.dict = bbs_dict

        try:
            self.name: str = record.nickname
            self.gameUID: str = record.uid
            self.region: str = record.region
            self.level: int = record.level

            status = bbs_dict
            self.resin = status['current_resin']
            self.task = status['finished_task_num']
            self.expedition = (
                status['current_expedition_num'], status['max_expedition_num'])
            self.coin = (status['current_home_coin'], status['max_home_coin'])
            if not status['transformer']['obtained']:
                self.transformer = '未获得'
            elif status['transformer']['recovery_time']['reached']:
                self.transformer = '已准备就绪'
            else:
                self.transformer = f"{status['transformer']['recovery_time']['Day']}天" \
                                   f"{status['transformer']['recovery_time']['Hour']}小时{status['transformer']['recovery_time']['Minute']}分钟"

            return self
        except KeyError and TypeError and ValueError:
            logger.error(
                f"{conf.LOG_HEAD}原神实时便笺数据 - 从米游社页面接口请求初始化对象: dict数据不正确")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")


async def get_action_ticket(account: UserAccount, retry: bool = True) -> Union[str, Literal[-1, -2, -3]]:
    """
    获取ActionTicket，返回str

    :param account: 用户账户数据
    :param retry: 是否允许重试

    - 若返回 `-1` 说明用户登录失效
    - 若返回 `-2` 说明服务器没有正确返回
    - 若返回 `-3` 说明请求失败
    """
    headers = HEADERS_ACTION_TICKET.copy()
    index = 0
    try:
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                    wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                headers["DS"] = generateDS()
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        URL_ACTION_TICKET.format(stoken=account.cookie["stoken"], bbs_uid=account.bbsUID),
                        headers=headers, cookies=account.cookie, timeout=conf.TIME_OUT)
                if not check_login(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}获取ActionTicket - 用户 {account.phone} 登录失效")
                    logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                    return -1
                if not check_DS(res.text) and (
                        (index < len(Subscribe.conf_list) - 1 or not Subscribe.conf_list) or not Subscribe.conf_list):
                    logger.info(
                        f"{conf.LOG_HEAD}获取ActionTicket: DS无效，正在在线获取salt以重新生成...")
                    sub = Subscribe()
                    conf.SALT_IOS = await sub.get(
                        ("Config", "SALT_IOS"), index)
                    conf.device.USER_AGENT_MOBILE = await sub.get(
                        ("DeviceConfig", "USER_AGENT_MOBILE"), index)
                    headers["User-Agent"] = conf.device.USER_AGENT_MOBILE
                    index += 1
                    headers["DS"] = generateDS()
                return res.json()["data"]["ticket"]
    except KeyError and TypeError and ValueError:
        logger.error(f"{conf.LOG_HEAD}获取ActionTicket - 服务器没有正确返回")
        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -2
    except Exception:
        logger.error(f"{conf.LOG_HEAD}获取ActionTicket - 请求失败")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -3


async def get_game_record(account: UserAccount, retry: bool = True) -> Union[List[GameRecord], Literal[-1, -2, -3]]:
    """
    获取用户绑定的游戏账户信息，返回一个GameRecord对象的列表

    :param account: 用户账户数据
    :param retry: 是否允许重试

    - 若返回 `-1` 说明用户登录失效
    - 若返回 `-2` 说明服务器没有正确返回
    - 若返回 `-3` 说明请求失败
    """
    record_list = []
    try:
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                    wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                async with httpx.AsyncClient() as client:
                    res = await client.get(URL_GAME_RECORD.format(account.bbsUID), headers=HEADERS_GAME_RECORD,
                                           cookies=account.cookie, timeout=conf.TIME_OUT)
                if not check_login(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}获取用户游戏数据 - 用户 {account.phone} 登录失效")
                    logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                    return -1
                for record in res.json()["data"]["list"]:
                    record_list.append(GameRecord(record))
                return record_list
    except KeyError and TypeError and ValueError:
        logger.error(f"{conf.LOG_HEAD}获取用户游戏数据 - 服务器没有正确返回")
        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -2
    except Exception:
        logger.error(f"{conf.LOG_HEAD}获取用户游戏数据 - 请求失败")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -3


async def get_game_list(retry: bool = True) -> Union[List[GameInfo], None]:
    """
    获取米哈游游戏的详细信息，若返回`None`说明获取失败

    :param retry: 是否允许重试
    """
    headers = HEADERS_GAME_LIST.copy()
    info_list = []
    try:
        index = 0
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                    wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                headers["DS"] = generateDS()
                async with httpx.AsyncClient() as client:
                    res = await client.get(URL_GAME_LIST, headers=headers, timeout=conf.TIME_OUT)
                if not check_DS(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}获取游戏信息: DS无效，正在在线获取salt以重新生成...")
                    sub = Subscribe()
                    conf.SALT_IOS = await sub.get(
                        ("Config", "SALT_IOS"), index)
                    conf.device.USER_AGENT_MOBILE = await sub.get(
                        ("DeviceConfig", "USER_AGENT_MOBILE"), index)
                    headers["User-Agent"] = conf.device.USER_AGENT_MOBILE
                    index += 1
                    headers["DS"] = generateDS()
                for info in res.json()["data"]["list"]:
                    info_list.append(GameInfo(info))
                return info_list
    except KeyError and TypeError and ValueError:
        logger.error(f"{conf.LOG_HEAD}获取游戏信息 - 服务器没有正确返回")
        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
    except Exception:
        logger.error(f"{conf.LOG_HEAD}获取游戏信息 - 请求失败")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")


async def get_user_myb(account: UserAccount, retry: bool = True) -> Union[int, Literal[-1, -2, -3]]:
    """
    获取用户当前米游币数量


    :param account: 用户账户数据
    :param retry: 是否允许重试

    - 若返回 `-1` 说明用户登录失效
    - 若返回 `-2` 说明服务器没有正确返回
    - 若返回 `-3` 说明请求失败
    """
    try:
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                    wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                async with httpx.AsyncClient() as client:
                    res = await client.get(URL_MYB, headers=HEADERS_MYB, cookies=account.cookie, timeout=conf.TIME_OUT)
                if not check_login(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}获取用户米游币 - 用户 {account.phone} 登录失效")
                    logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                    return -1
                return int(res.json()["data"]["points"])
    except KeyError and TypeError and ValueError:
        logger.error(f"{conf.LOG_HEAD}获取用户米游币 - 服务器没有正确返回")
        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -2
    except Exception:
        logger.error(f"{conf.LOG_HEAD}获取用户米游币 - 请求失败")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -3


async def device_login(account: UserAccount, retry: bool = True) -> Literal[1, -1, -2, -3]:
    """
    设备登录(deviceLogin)(适用于安卓设备)

    :param account: 用户账户数据
    :param retry: 是否允许重试

    - 若返回 `1` 说明成功
    - 若返回 `-1` 说明用户登录失效
    - 若返回 `-2` 说明服务器没有正确返回
    - 若返回 `-3` 说明请求失败
    """
    data = {
        "app_version": conf.device.X_RPC_APP_VERSION,
        "device_id": account.deviceID_2,
        "device_name": conf.device.X_RPC_DEVICE_NAME_ANDROID,
        "os_version": "30",
        "platform": "Android",
        "registration_id": "1a0018970a5c00e814d"
    }
    headers = HEADERS_DEVICE.copy()
    headers["x-rpc-device_id"] = account.deviceID_2
    try:
        index = 0
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                    wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                headers["DS"] = generateDS(data)
                async with httpx.AsyncClient() as client:
                    res = await client.post(URL_DEVICE_LOGIN, headers=headers, json=data, cookies=account.cookie,
                                            timeout=conf.TIME_OUT)
                if not check_login(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}设备登录 - 用户 {account.phone} 登录失效")
                    logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                    return -1
                if not check_DS(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}设备登录: DS无效，正在在线获取salt以重新生成...")
                    conf.SALT_DATA = await Subscribe().get(
                        ("Config", "SALT_DATA"), index)
                    index += 1
                    headers["DS"] = generateDS(data)
                if res.json()["message"] != "OK":
                    raise ValueError
                else:
                    return 1
    except KeyError and TypeError and ValueError:
        logger.error(f"{conf.LOG_HEAD}设备登录 - 服务器没有正确返回")
        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -2
    except Exception:
        logger.error(f"{conf.LOG_HEAD}设备登录 - 请求失败")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -3


async def device_save(account: UserAccount, retry: bool = True) -> Literal[1, -1, -2, -3]:
    """
    设备保存(saveDevice)(适用于安卓设备)

    :param account: 用户账户数据
    :param retry: 是否允许重试

    - 若返回 `1` 说明成功
    - 若返回 `-1` 说明用户登录失效
    - 若返回 `-2` 说明服务器没有正确返回
    - 若返回 `-3` 说明请求失败
    """
    data = {
        "app_version": conf.device.X_RPC_APP_VERSION,
        "device_id": account.deviceID_2,
        "device_name": conf.device.X_RPC_DEVICE_NAME_ANDROID,
        "os_version": "30",
        "platform": "Android",
        "registration_id": "1a0018970a5c00e814d"
    }
    headers = HEADERS_DEVICE.copy()
    headers["x-rpc-device_id"] = account.deviceID_2
    try:
        index = 0
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                    wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                headers["DS"] = generateDS(data)
                async with httpx.AsyncClient() as client:
                    res = await client.post(URL_DEVICE_SAVE, headers=headers, json=data, cookies=account.cookie,
                                            timeout=conf.TIME_OUT)
                if not check_login(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}设备保存 - 用户 {account.phone} 登录失效")
                    logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                    return -1
                if not check_DS(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}设备登录: DS无效，正在在线获取salt以重新生成...")
                    conf.SALT_DATA = await Subscribe().get(
                        ("Config", "SALT_DATA"), index)
                    index += 1
                if res.json()["message"] != "OK":
                    raise ValueError
                else:
                    return 1
    except KeyError and TypeError and ValueError:
        logger.error(f"{conf.LOG_HEAD}设备保存 - 服务器没有正确返回")
        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -2
    except Exception:
        logger.error(f"{conf.LOG_HEAD}设备保存 - 请求失败")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -3


async def genshin_status_widget(account: UserAccount, retry: bool = True) -> Union[GenshinStatus, Literal[-1, -2, -3]]:
    """
    使用iOS小组件API获取原神实时便笺，返回`GenshinStatus`对象

    :param account: 用户账户数据
    :param retry: 是否允许重试

    - 若返回 `-1` 说明用户登录失效
    - 若返回 `-2` 说明服务器没有正确返回
    - 若返回 `-3` 说明请求失败
    """
    headers = HEADERS_GENSHIN_STATUS_WIDGET.copy()
    headers["x-rpc-device_id"] = account.deviceID
    try:
        index = 0
        async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                    wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
            with attempt:
                headers["DS"] = generateDS()
                async with httpx.AsyncClient() as client:
                    res = await client.get(URL_GENSHIN_STATUS_WIDGET, headers=headers, cookies=account.cookie,
                                           timeout=conf.TIME_OUT)
                if not check_login(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}原神实时便笺 - 用户 {account.phone} 登录失效")
                    logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                    return -1
                if not check_DS(res.text):
                    logger.info(
                        f"{conf.LOG_HEAD}原神实时便笺: DS无效，正在在线获取salt以重新生成...")
                    conf.SALT_IOS = await Subscribe().get(
                        ("Config", "SALT_IOS"), index)
                    index += 1
                status = GenshinStatus().fromWidget(res.json()["data"]["data"])
                if not status:
                    raise KeyError
                return status
    except KeyError and TypeError and ValueError:
        logger.error(f"{conf.LOG_HEAD}原神实时便笺(小组件) - 服务器没有正确返回")
        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -2
    except Exception:
        logger.error(f"{conf.LOG_HEAD}原神实时便笺(小组件) - 请求失败")
        logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        return -3


async def genshin_status_bbs(account: UserAccount, retry: bool = True) -> Union[GenshinStatus, Literal[-1, -2, -3, -4]]:
    """
    使用米游社内页面API获取原神实时便笺，返回`GenshinStatus`对象

    :param account: 用户账户数据
    :param retry: 是否允许重试

    - 若返回 `-1` 说明用户登录失效
    - 若返回 `-2` 说明服务器没有正确返回
    - 若返回 `-3` 说明请求失败
    - 若返回 `-4` 说明用户没有任何原神账户
    """
    records: list[GameRecord] = await get_game_record(account=account)
    if records == []:
        return -4
    if isinstance(records, int):
        return -3
    flag = True
    for record in records:
        if GameInfo.ABBR_TO_ID[record.gameID][0] == 'ys':
            try:
                flag = False
                index = 0
                url = URL_GENSHEN_STATUS_BBS.format(
                    game_uid=record.uid, region=record.region)
                headers = HEADERS_GENSHIN_STATUS_BBS.copy()
                headers["x-rpc-device_id"] = account.deviceID_2
                async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                            wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                    with attempt:
                        headers["DS"] = generateDS(
                            params={"role_id": record.uid, "server": record.region})
                        async with httpx.AsyncClient() as client:
                            res = await client.get(url, headers=headers, cookies=account.cookie, timeout=conf.TIME_OUT)
                        if not check_login(res.text):
                            logger.info(
                                f"{conf.LOG_HEAD}原神实时便笺 - 用户 {account.phone} 登录失效")
                            logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                            return -1
                        if not check_DS(res.text):
                            logger.info(
                                f"{conf.LOG_HEAD}原神实时便笺: DS无效，正在在线获取salt以重新生成...")
                            conf.SALT_PARAMS = await Subscribe().get(
                                ("Config", "SALT_PARAMS"), index)
                            index += 1
                        status = GenshinStatus().fromBBS(
                            res.json()["data"], record)
                        if not status:
                            raise KeyError
                        return status
            except KeyError and TypeError and ValueError:
                logger.error(f"{conf.LOG_HEAD}原神实时便笺 - 服务器没有正确返回")
                logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
                return -2
            except Exception:
                logger.error(f"{conf.LOG_HEAD}原神实时便笺 - 请求失败")
                logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
                return -3
    if flag:
        return -4


@nonebot.get_driver().on_startup
async def set_game_list():
    """
    设置游戏ID(gameID)与缩写和全称的对应关系
    """
    game_list = await get_game_list()
    if game_list is None:
        return
    for game in game_list:
        if game.name == "原神":
            GameInfo.ABBR_TO_ID.setdefault(game.gameID, ("ys", game.name))
        elif game.name == "崩坏3":
            GameInfo.ABBR_TO_ID.setdefault(game.gameID, ("bh3", game.name))
        elif game.name == "崩坏学园2":
            GameInfo.ABBR_TO_ID.setdefault(game.gameID, ("bh2", game.name))
        elif game.name == "未定事件簿":
            GameInfo.ABBR_TO_ID.setdefault(game.gameID, ("wd", game.name))
        elif game.name == "大别野":
            GameInfo.ABBR_TO_ID.setdefault(game.gameID, ("bbs", game.name))
        elif game.name == "崩坏：星穹铁道":
            GameInfo.ABBR_TO_ID.setdefault(game.gameID, ("xq", game.name))
        elif game.name == "绝区零":
            GameInfo.ABBR_TO_ID.setdefault(game.gameID, ("jql", game.name))
