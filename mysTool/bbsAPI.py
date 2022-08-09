"""
### 米游社其他API
"""
import httpx
import traceback
from .config import mysTool_config as conf
from .data import UserAccount
from .utils import generateDeviceID, generateDS
from nonebot.log import logger

URL_ACTION_TICKET = "https://api-takumi.mihoyo.com/auth/api/getActionTicketBySToken?action_type=game_role&stoken={stoken}&uid={bbs_uid}"
URL_GAME_RECORD = "https://api-takumi-record.mihoyo.com/game_record/card/wapi/getGameRecordCard?uid={}"
URL_GAME_LIST = "https://bbs-api.mihoyo.com/apihub/api/getGameList"
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


class GameRecord:
    """
    用户游戏数据
    """

    def __init__(self, gameRecord_dict: dict) -> None:
        self.gameRecord_dict = gameRecord_dict

    @property
    def regionName(self) -> str:
        """
        服务器区名
        """
        return self.gameRecord_dict["region_name"]

    @property
    def gameID(self) -> str:
        """
        游戏ID
        """
        return self.gameRecord_dict["game_id"]

    @property
    def level(self) -> str:
        """
        用户游戏等级
        """
        return self.gameRecord_dict["level"]

    @property
    def region(self) -> str:
        """
        服务器区号
        """
        return self.gameRecord_dict["region"]

    @property
    def uid(self) -> str:
        """
        用户游戏UID
        """
        return self.gameRecord_dict["game_role_id"]

    @property
    def nickname(self) -> str:
        """
        用户游戏昵称
        """
        return self.gameRecord_dict["nickname"]


class GameInfo:
    """
    游戏信息数据
    """

    def __init__(self, gameInfo_dict: dict) -> None:
        self.gameInfo_dict = gameInfo_dict

    @property
    def gameID(self) -> int:
        """
        游戏ID
        """
        return self.gameInfo_dict["id"]

    @property
    def appIcon(self) -> str:
        """
        游戏App图标链接(大)
        """
        return self.gameInfo_dict["app_icon"]

    @property
    def opName(self) -> str:
        """
        游戏代号(英文数字, 例如hk4e)
        """
        return self.gameInfo_dict["op_name"]

    @property
    def enName(self) -> str:
        """
        游戏代号2(英文数字, 例如ys)
        """
        return self.gameInfo_dict["en_name"]

    @property
    def miniIcon(self) -> str:
        """
        游戏图标链接(圆形, 小)
        """
        return self.gameInfo_dict["icon"]

    @property
    def name(self) -> str:
        """
        游戏名称
        """
        return self.gameInfo_dict["name"]


async def get_action_ticket(account: UserAccount) -> str:
    headers = HEADERS_ACTION_TICKET.copy()
    headers["DS"] = generateDS()
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(URL_ACTION_TICKET, headers=headers, cookies=account.cookie)
        return res["data"]["ticket"]
    except KeyError:
        logger.error(conf.LOG_HEAD + "获取ActionTicket - 服务器没有正确返回")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())
    except:
        logger.error(conf.LOG_HEAD + "获取ActionTicket - 请求失败")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())


async def get_game_record(account: UserAccount) -> list[GameRecord]:
    record_list = []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(URL_GAME_RECORD.format(account.bbsUID), headers=HEADERS_GAME_RECORD, cookies=account.cookie)
        for record in res.json()["data"]["list"]:
            record_list.append(GameRecord(record))
        return record_list
    except KeyError:
        logger.error(conf.LOG_HEAD + "获取用户游戏数据 - 服务器没有正确返回")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())
    except:
        logger.error(conf.LOG_HEAD + "获取用户游戏数据 - 请求失败")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())


async def get_game_list():
    headers = HEADERS_GAME_LIST.copy()
    headers["DS"] = generateDS()
    info_list = []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(URL_GAME_LIST, headers=headers)
        for info in res["data"]["list"]:
            info_list.append(GameInfo(info))
    except KeyError:
        logger.error(conf.LOG_HEAD + "获取游戏信息 - 服务器没有正确返回")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())
    except:
        logger.error(conf.LOG_HEAD + "获取游戏信息 - 请求失败")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())
