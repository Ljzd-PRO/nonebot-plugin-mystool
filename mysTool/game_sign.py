import httpx
import traceback
from nonebot.log import logger
from .config import mysTool_config as conf
from .utils import *

ACT_ID = {
    "ys": "e202009291139501"
}
URL_REWARD = {
    "ys": "https://api-takumi.mihoyo.com/event/bbs_sign_reward/home?act_id={}".format(ACT_ID["ys"])
}
URL_GAME_ROLE = "https://api-takumi.mihoyo.com/binding/api/getUserGameRoles?point_sn=myb&action_ticket={actionTicket}&game_biz={game_biz}"
URL_SIGN = "https://api-takumi.mihoyo.com/event/bbs_sign_reward/sign"
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

class Award:
    def __init__(self, awards_dict:dict) -> None:
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

class Sign:


    def __init__(self, cookie:dict, deviceID:str) -> None:
        self.cookie = cookie
        self.deviceID = deviceID

    async def reward(self, game:str):
        res: httpx.Response = await httpx.get(URL_REWARD[game], headers=HEADERS_REWARD)
        try:
            return Award(res.json()["data"]["awards"])
        except KeyError:
            print("服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
        except:
            print("网络连接失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())

    async def sign(game:str):
        ...
