import httpx
import traceback
from nonebot.log import logger
from .config import mysTool_config as conf
from .utils import *
from .data import UserAccount
from typing import Literal

ACT_ID = {
    "ys": "e202009291139501"
}
URLS = {
    "ys": {
        "reward": "https://api-takumi.mihoyo.com/event/bbs_sign_reward/home?act_id={}".format(ACT_ID["ys"]),
        "info": "https://api-takumi.mihoyo.com/event/bbs_sign_reward/info?act_id={actID}&region={region}&uid={uid}",
        "sign": "https://api-takumi.mihoyo.com/event/bbs_sign_reward/sign"
    }
}
URL_GAME_ROLE = "https://api-takumi.mihoyo.com/binding/api/getUserGameRoles?point_sn=myb&action_ticket={actionTicket}&game_biz={game_biz}"

HEADERS_REWARD = {
    "Host": "api-takumi.mihoyo.com",
    "Origin": "https://webstatic.mihoyo.com",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": conf.device.USER_AGENT_MOBILE,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Referer": "https://webstatic.mihoyo.com/",
    "Accept-Encoding": "gzip, deflate, br"
}
HEADERS_OTHER = {
    "Host": "api-takumi.mihoyo.com",
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_MOBILE,
    "User-Agent": conf.device.USER_AGENT_MOBILE,
    "Referer": "https://webstatic.mihoyo.com/",
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_MOBILE,
    "Origin": "https://webstatic.mihoyo.com",
    "Connection": "keep-alive",
    "x-rpc-channel": conf.device.X_RPC_CHANNEL,
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "x-rpc-device_id": None,
    "x-rpc-client_type": "5",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=utf-8",
    "Accept-Encoding": "gzip, deflate, br",
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION,
    "x-rpc-platform": conf.device.X_RPC_PLATFORM
}


class Award:
    """
    签到奖励数据
    """

    def __init__(self, awards_dict: dict) -> None:
        self.awards_dict = awards_dict

    @property
    def name(self) -> str:
        return self.awards_dict["name"]

    @property
    def icon(self) -> str:
        return self.awards_dict["icon"]

    @property
    def name(self) -> int:
        return self.awards_dict["cnt"]


class Info:
    """
    签到记录数据
    """

    def __init__(self, info_dict: dict) -> None:
        self.info_dict = info_dict

    @property
    def isSign(self) -> bool:
        """
        今日是否已经签到
        """
        return self.info_dict["is_sign"]

    @property
    def firstBind(self) -> bool:
        """
        是否是第一次绑定
        """
        return self.info_dict["first_bind"]

    @property
    def monthFirst(self) -> bool:
        """
        是否是月初第一天
        """
        return self.info_dict["month_first"]

    @property
    def totalDays(self) -> int:
        """
        已签多少天
        """
        return self.info_dict["total_sign_day"]

    @property
    def missedDays(self) -> int:
        """
        漏签多少天
        """
        return self.info_dict["sign_cnt_missed"]


class Sign:
    """
    签到相关(需先初始化对象)
    """

    def __init__(self, account: UserAccount) -> None:
        self.cookie = account.cookie
        self.deviceID = account.deviceID

    async def reward(self, game: Literal["ys"]):
        """
        获取签到奖励信息
        """
        async with httpx.AsyncClient() as client:
            res = await client.get(URLS[game]["reward"], headers=HEADERS_REWARD)
        try:
            return Award(res.json()["data"]["awards"])
        except KeyError:
            logger.error(conf.LOG_HEAD + "获取签到奖励信息 - 服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
        except:
            logger.error(conf.LOG_HEAD + "获取签到奖励信息 - 请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())

    async def info(self, game: Literal["ys"]):
        """
        获取签到记录
        """
        headers = HEADERS_OTHER.copy()
        headers["x-rpc-device_id"] = self.deviceID
        async with httpx.AsyncClient() as client:
            res = await client.get(URLS[game]["info"], headers=headers, cookies=self.cookie)
        try:
            return Info(res.json()["data"])
        except KeyError:
            logger.error(conf.LOG_HEAD + "获取签到记录 - 服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
        except:
            logger.error(conf.LOG_HEAD + "获取签到记录 - 请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
