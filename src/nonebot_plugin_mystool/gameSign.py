"""
### 米游社游戏签到相关
"""
import traceback
from typing import List, Literal, Union

import httpx
import tenacity

from .bbsAPI import (GameInfo, GameRecord, device_login, device_save,
                     get_game_record)
from .config import mysTool_config as conf
from .data import UserAccount
from .utils import (Subscribe, check_DS, check_login, custom_attempt_times,
                    generateDS, logger)

ACT_ID = {
    "ys": "e202009291139501",
    "bh3": "e202207181446311",
    "bh2": "e202203291431091",
    "wd": "e202202251749321"
}
URLS = {
    "ys": {
        "reward": "https://api-takumi.mihoyo.com/event/bbs_sign_reward/home?act_id={}".format(ACT_ID["ys"]),
        "info": "".join(("https://api-takumi.mihoyo.com/event/bbs_sign_reward/info?act_id={}".format(ACT_ID["ys"]),
                         "&region={region}&uid={uid}")),
        "sign": "https://api-takumi.mihoyo.com/event/bbs_sign_reward/sign"
    },
    "bh3": {
        "reward": "https://api-takumi.mihoyo.com/event/luna/home?lang=zh-cn&act_id={}".format(ACT_ID["bh3"]),
        "info": "".join(("https://api-takumi.mihoyo.com/event/luna/info?lang=zh-cn&act_id={}".format(ACT_ID["bh3"]),
                         "&region={region}&uid={uid}")),
        "sign": "https://api-takumi.mihoyo.com/event/luna/sign"
    },
    "bh2": {
        "reward": "https://api-takumi.mihoyo.com/event/luna/home?lang=zh-cn&act_id={}".format(ACT_ID["bh2"]),
        "info": "".join(("https://api-takumi.mihoyo.com/event/luna/info?lang=zh-cn&act_id={}".format(ACT_ID["bh2"]),
                         "&region={region}&uid={uid}")),
        "sign": "https://api-takumi.mihoyo.com/event/luna/sign"
    },
    "wd": {
        "reward": "https://api-takumi.mihoyo.com/event/luna/home?lang=zh-cn&act_id={}".format(ACT_ID["wd"]),
        "info": "".join(("https://api-takumi.mihoyo.com/event/luna/info?lang=zh-cn&act_id={}".format(ACT_ID["wd"]),
                         "&region={region}&uid={uid}")),
        "sign": "https://api-takumi.mihoyo.com/event/luna/sign"
    }
}

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
    "x-rpc-platform": conf.device.X_RPC_PLATFORM,
    "DS": None
}


class Award:
    """
    签到奖励数据
    """

    def __init__(self, awards_dict: dict) -> None:
        self.awards_dict = awards_dict
        try:
            for func in dir(Award):
                if func.startswith("__"):
                    continue
                getattr(self, func)
        except KeyError:
            logger.error(f"{conf.LOG_HEAD}签到奖励数据 - 初始化对象: dict数据不正确")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")

    @property
    def name(self) -> str:
        """
        签到获得的物品名称
        """
        return self.awards_dict["name"]

    @property
    def icon(self) -> str:
        """
        物品图片链接
        """
        return self.awards_dict["icon"]

    @property
    def count(self) -> int:
        """
        物品数量
        """
        return self.awards_dict["cnt"]


class Info:
    """
    签到记录数据
    """

    def __init__(self, info_dict: dict) -> None:
        self.info_dict = info_dict
        try:
            for func in dir(Info):
                if func.startswith("__"):
                    continue
                getattr(self, func)
        except KeyError:
            logger.error(f"{conf.LOG_HEAD}签到记录数据 - 初始化对象: dict数据不正确")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")

    @property
    def isSign(self) -> bool:
        """
        今日是否已经签到
        """
        return self.info_dict["is_sign"]

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


class GameSign:
    """
    游戏签到相关(需先初始化对象)
    """
    SUPPORTED_GAMES = ["ys", "bh3", "bh2", "wd"]
    '''目前支持签到的游戏'''

    def __init__(self, account: UserAccount) -> None:
        self.cookie = account.cookie
        self.account = account
        self.signResult: dict = None
        '''签到返回结果'''

    async def reward(self, game: Literal["ys", "bh3"], retry: bool = True):
        """
        获取签到奖励信息，若返回`None`说明失败

        :param game: 目标游戏缩写
        :param retry: 是否允许重试
        """
        try:
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                        wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = None
                    async with httpx.AsyncClient() as client:
                        res = await client.get(URLS[game]["reward"], headers=HEADERS_REWARD, timeout=conf.TIME_OUT)
                    award_list: List[Award] = []
                    for award in res.json()["data"]["awards"]:
                        award_list.append(Award(award))
                    return award_list
        except KeyError and ValueError and TypeError:
            logger.error(f"{conf.LOG_HEAD}获取签到奖励信息 - 服务器没有正确返回")
            logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        except Exception:
            logger.error(f"{conf.LOG_HEAD}获取签到奖励信息 - 请求失败")
            if isinstance(res, httpx.Response):
                logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")

    async def info(self, game: Literal["ys", "bh3"], gameUID: str, region: str = None, retry: bool = True) -> Union[
        Info, Literal[-1, -2, -3, -4]]:
        """
        获取签到记录，返回Info对象

        :param game: 目标游戏缩写
        :param gameUID: 用户游戏UID
        :param region: 用户游戏区服(若为`None`将会自动获取)
        :param retry: 是否允许重试

        - 若返回 `-1` 说明用户登录失效
        - 若返回 `-2` 说明服务器没有正确返回
        - 若返回 `-3` 说明请求失败
        - 若返回 `-4` 未找到对应游戏UID的游戏账户
        """
        headers = HEADERS_OTHER.copy()
        headers["x-rpc-device_id"] = self.account.deviceID

        game_record: List[GameRecord] = await get_game_record(self.account)
        if game_record == -1:
            return -1
        elif game_record == -2:
            return -2
        elif game_record == -3:
            return -3

        if not region:
            for record in game_record:
                if record.uid == gameUID:
                    region = record.region
        if not region:
            return -4

        try:
            index = 0
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                        wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = None
                    headers["DS"] = generateDS()
                    async with httpx.AsyncClient() as client:
                        res = await client.get(URLS[game]["info"].format(region=region, uid=gameUID), headers=headers,
                                               cookies=self.cookie, timeout=conf.TIME_OUT)
                    if not check_login(res.text):
                        logger.info(
                            f"{conf.LOG_HEAD}获取签到记录 - 用户 {self.account.phone} 登录失效")
                        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                        return -1
                    if not check_DS(res.text):
                        logger.info(
                            f"{conf.LOG_HEAD}获取签到记录: DS无效，正在在线获取salt以重新生成...")
                        sub = Subscribe()
                        conf.SALT_IOS = await sub.get(
                            ("Config", "SALT_IOS"), index)
                        conf.device.USER_AGENT_MOBILE = await sub.get(
                            ("DeviceConfig", "USER_AGENT_MOBILE"), index)
                        headers["User-Agent"] = conf.device.USER_AGENT_MOBILE
                        index += 1
                        headers["DS"] = generateDS()
                    return Info(res.json()["data"])
        except KeyError and ValueError and TypeError:
            logger.error(f"{conf.LOG_HEAD}获取签到记录 - 服务器没有正确返回")
            logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
            return -2
        except Exception:
            logger.error(f"{conf.LOG_HEAD}获取签到记录 - 请求失败")
            if isinstance(res, httpx.Response):
                logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
            return -3

    async def sign(self, game: Literal["ys", "bh3", "bh2", "wd"], gameUID: str,
                   platform: Literal["ios", "android"] = "ios", retry: bool = True) -> Literal[
        1, -1, -2, -3, -4, -5, -6]:
        """
        签到

        :param game: 目标游戏缩写
        :param gameUID: 用户游戏UID
        :param platform: 设备平台
        :param retry: 是否允许重试

        - 若执行成功，返回 `1`
        - 若返回 `-1` 说明用户登录失效
        - 若返回 `-2` 说明服务器没有正确返回
        - 若返回 `-3` 说明请求失败
        - 若返回 `-4` 说明暂不支持该游戏
        - 若返回 `-5` 说明可能被验证码阻拦
        - 若返回 `-6` 说明未找到游戏账号
        """
        if game not in self.SUPPORTED_GAMES:
            logger.info(f"{conf.LOG_HEAD}暂不支持游戏 {game} 的游戏签到")
            return -4

        record_list: List[GameRecord] = await get_game_record(self.account)
        filter_record = list(filter(lambda record: record.uid ==
                                                   gameUID and GameInfo.ABBR_TO_ID[record.gameID][0] == game,
                                    record_list))
        if not filter_record:
            return -6
        data = {
            "act_id": ACT_ID[game],
            "region": filter_record[0].region,
            "uid": gameUID
        }

        headers = HEADERS_OTHER.copy()
        if platform == "ios":
            headers["x-rpc-device_id"] = self.account.deviceID
            headers["DS"] = generateDS()
        else:
            headers["x-rpc-device_id"] = self.account.deviceID_2
            headers["x-rpc-device_model"] = conf.device.X_RPC_DEVICE_MODEL_ANDROID
            headers["User-Agent"] = conf.device.USER_AGENT_ANDROID
            headers["x-rpc-device_name"] = conf.device.X_RPC_DEVICE_NAME_ANDROID
            headers["x-rpc-channel"] = conf.device.X_RPC_CHANNEL_ANDROID
            headers["x-rpc-sys_version"] = conf.device.X_RPC_SYS_VERSION_ANDROID
            headers["x-rpc-client_type"] = "2"
            headers.pop("x-rpc-platform")
            await device_login(self.account)
            await device_save(self.account)
            headers["DS"] = generateDS(platform="android")
        try:
            index = 0
            async for attempt in tenacity.AsyncRetrying(stop=custom_attempt_times(retry), reraise=True,
                                                        wait=tenacity.wait_fixed(conf.SLEEP_TIME_RETRY)):
                with attempt:
                    res = None
                    async with httpx.AsyncClient() as client:
                        res = await client.post(URLS[game]["sign"], headers=headers, cookies=self.cookie,
                                                timeout=conf.TIME_OUT, json=data)
                    if not check_login(res.text):
                        logger.info(
                            f"{conf.LOG_HEAD}签到 - 用户 {self.account.phone} 登录失效")
                        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                        return -1
                    if not check_DS(res.text):
                        logger.info(
                            f"{conf.LOG_HEAD}签到: DS无效，正在在线获取salt以重新生成...")
                        sub = Subscribe()
                        if platform == "ios":
                            conf.SALT_IOS = await sub.get(
                                ("Config", "SALT_IOS"), index)
                            conf.device.USER_AGENT_MOBILE = await sub.get(
                                ("DeviceConfig", "USER_AGENT_MOBILE"), index)
                            headers["User-Agent"] = conf.device.USER_AGENT_MOBILE
                            headers["DS"] = generateDS()
                        else:
                            conf.SALT_ANDROID = await sub.get(
                                ("Config", "SALT_ANDROID"), index)
                            conf.device.USER_AGENT_ANDROID = await sub.get(
                                ("DeviceConfig", "USER_AGENT_ANDROID"), index)
                            headers["User-Agent"] = conf.device.USER_AGENT_ANDROID
                            headers["DS"] = generateDS(platform="android")
                        index += 1
                    self.signResult = res.json()
                    if game == "ys" and self.signResult["message"] == "旅行者，你已经签到过了":
                        return 1
                    if game not in ["bh3", "wd", "bh2"] and self.signResult["data"]["risk_code"] != 0:
                        logger.warning(
                            f"{conf.LOG_HEAD}签到 - 用户 {self.account.phone} 可能被验证码阻拦".format())
                        logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
                        return -5
                    return 1
        except KeyError and ValueError and TypeError:
            logger.error(f"{conf.LOG_HEAD}签到 - 服务器没有正确返回")
            logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
            return -2
        except Exception:
            logger.error(f"{conf.LOG_HEAD}签到 - 请求失败")
            if isinstance(res, httpx.Response):
                logger.debug(f"{conf.LOG_HEAD}网络请求返回: {res.text}")
            logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
            return -3
