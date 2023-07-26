"""
### 米游社的游戏签到相关API
"""
from typing import List, Optional, Tuple, Literal, Set, Type, Callable, Any, Coroutine
from urllib.parse import urlencode

import httpx
import tenacity

from .data_model import GameRecord, BaseApiStatus, Award, GameSignInfo, GeetestResult
from .plugin_data import PluginDataManager
from .simple_api import ApiResultHandler, HEADERS_API_TAKUMI_MOBILE, is_incorrect_return, device_login, device_save
from .user_data import UserAccount
from .utils import logger, generate_ds, \
    get_async_retry, get_validate

_conf = PluginDataManager.plugin_data


class BaseGameSign:
    """
    游戏签到基类
    """
    NAME = ""
    """游戏名字"""

    ACT_ID = ""
    URL_REWARD = "https://api-takumi.mihoyo.com/event/luna/home"
    URL_INFO = "https://api-takumi.mihoyo.com/event/luna/info"
    URL_SIGN = "https://api-takumi.mihoyo.com/event/luna/sign"
    HEADERS_REWARD = {
        "Host": "api-takumi.mihoyo.com",
        "Origin": "https://webstatic.mihoyo.com",
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": _conf.device_config.USER_AGENT_MOBILE,
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Referer": "https://webstatic.mihoyo.com/",
        "Accept-Encoding": "gzip, deflate, br"
    }
    GAME_ID = 0

    AVAILABLE_GAME_SIGNS: Set[Type["BaseGameSign"]] = set()
    """可用的子类"""

    def __init__(self, account: UserAccount, records: List[GameRecord]):
        self.account = account
        self.record = next(filter(lambda x: x.game_id == self.GAME_ID, records), None)
        reward_params = {
            "lang": "zh-cn",
            "act_id": self.ACT_ID
        }
        self.URL_REWARD = f"{self.URL_REWARD}?{urlencode(reward_params)}"
        info_params = {
            "lang": "zh-cn",
            "act_id": self.ACT_ID,
            "region": self.record.region if self.record else None,
            "uid": self.record.game_role_id if self.record else None
        }
        self.URL_INFO = f"{self.URL_INFO}?{urlencode(info_params)}"

    @property
    def has_record(self) -> bool:
        """
        是否有游戏账号
        """
        return self.record is not None

    async def get_rewards(self, retry: bool = True) -> Tuple[BaseApiStatus, Optional[List[Award]]]:
        """
        获取签到奖励信息

        :param retry: 是否允许重试
        """
        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    async with httpx.AsyncClient() as client:
                        res = await client.get(self.URL_REWARD, headers=self.HEADERS_REWARD,
                                               timeout=_conf.preference.timeout)
                    award_list = []
                    for award in res.json()["data"]["awards"]:
                        award_list.append(Award.parse_obj(award))
                    return BaseApiStatus(success=True), award_list
        except tenacity.RetryError as e:
            if is_incorrect_return(e):
                logger.exception(f"获取签到奖励信息 - 服务器没有正确返回")
                logger.debug(f"网络请求返回: {res.text}")
                return BaseApiStatus(incorrect_return=True), None
            else:
                logger.exception(f"获取签到奖励信息 - 请求失败")
                return BaseApiStatus(network_error=True), None

    async def get_info(self, platform: Literal["ios", "android"] = "ios", retry: bool = True) -> Tuple[
        BaseApiStatus, Optional[GameSignInfo]]:
        """
        获取签到记录

        :param platform: 使用的设备平台
        :param retry: 是否允许重试
        """
        headers = HEADERS_API_TAKUMI_MOBILE.copy()
        headers["x-rpc-device_id"] = self.account.device_id_ios if platform == "ios" else self.account.device_id_android

        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    headers["DS"] = generate_ds() if platform == "ios" else generate_ds(platform="android")
                    async with httpx.AsyncClient() as client:
                        res = await client.get(self.URL_INFO, headers=headers,
                                               cookies=self.account.cookies.dict(), timeout=_conf.preference.timeout)
                    api_result = ApiResultHandler(res.json())
                    if api_result.login_expired:
                        logger.info(
                            f"获取签到数据 - 用户 {self.account.bbs_uid} 登录失效")
                        logger.debug(f"网络请求返回: {res.text}")
                        return BaseApiStatus(login_expired=True), None
                    if api_result.invalid_ds:
                        logger.info(
                            f"获取签到数据 - 用户 {self.account.bbs_uid} DS 校验失败")
                        logger.debug(f"网络请求返回: {res.text}")
                        return BaseApiStatus(invalid_ds=True), None
                    return BaseApiStatus(success=True), GameSignInfo.parse_obj(api_result.data)
        except tenacity.RetryError as e:
            if is_incorrect_return(e):
                logger.exception(f"获取签到数据 - 服务器没有正确返回")
                logger.debug(f"网络请求返回: {res.text}")
                return BaseApiStatus(incorrect_return=True), None
            else:
                logger.exception(f"获取签到数据 - 请求失败")
                return BaseApiStatus(network_error=True), None

    async def sign(self,
                   platform: Literal["ios", "android"] = "ios",
                   on_geetest_callback: Callable[[], Any] = None,
                   retry: bool = True) -> BaseApiStatus:
        """
        签到

        :param platform: 设备平台
        :param on_geetest_callback: 开始尝试进行人机验证时调用的回调函数
        :param retry: 是否允许重试
        """
        if not self.record:
            return BaseApiStatus(success=True)
        content = {
            "act_id": self.ACT_ID,
            "region": self.record.region,
            "uid": self.record.game_role_id
        }
        headers = HEADERS_API_TAKUMI_MOBILE.copy()
        if platform == "ios":
            headers["x-rpc-device_id"] = self.account.device_id_ios
            headers["DS"] = generate_ds()
        else:
            headers["x-rpc-device_id"] = self.account.device_id_android
            headers["x-rpc-device_model"] = _conf.device_config.X_RPC_DEVICE_MODEL_ANDROID
            headers["User-Agent"] = _conf.device_config.USER_AGENT_ANDROID
            headers["x-rpc-device_name"] = _conf.device_config.X_RPC_DEVICE_NAME_ANDROID
            headers["x-rpc-channel"] = _conf.device_config.X_RPC_CHANNEL_ANDROID
            headers["x-rpc-sys_version"] = _conf.device_config.X_RPC_SYS_VERSION_ANDROID
            headers["x-rpc-client_type"] = "2"
            headers.pop("x-rpc-platform")
            await device_login(self.account)
            await device_save(self.account)
            headers["DS"] = generate_ds(data=content)

        challenge = ""
        """人机验证任务 challenge"""
        geetest_result = GeetestResult("", "")
        """人机验证结果"""

        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    if geetest_result.validate:
                        headers["x-rpc-validate"] = geetest_result.validate
                        headers["x-rpc-challenge"] = challenge
                        headers["x-rpc-seccode"] = f'{geetest_result.validate}|jordan'

                    async with httpx.AsyncClient() as client:
                        res = await client.post(
                            self.URL_SIGN,
                            headers=headers,
                            cookies=self.account.cookies.dict(),
                            timeout=_conf.preference.timeout,
                            json=content
                        )

                    api_result = ApiResultHandler(res.json())
                    if api_result.login_expired:
                        logger.info(
                            f"游戏签到 - 用户 {self.account.bbs_uid} 登录失效")
                        logger.debug(f"网络请求返回: {res.text}")
                        return BaseApiStatus(login_expired=True)
                    if api_result.invalid_ds:
                        logger.info(
                            f"游戏签到 - 用户 {self.account.bbs_uid} DS 校验失败")
                        logger.debug(f"网络请求返回: {res.text}")
                        return BaseApiStatus(invalid_ds=True)
                    if api_result.data.get("risk_code") != 0:
                        logger.warning(
                            f"{_conf.preference.log_head}游戏签到 - 用户 {self.account.bbs_uid} 可能被人机验证阻拦")
                        logger.debug(f"{_conf.preference.log_head}网络请求返回: {res.text}")
                        gt = api_result.data.get("gt", None)
                        challenge = api_result.data.get("challenge", None)
                        if gt and challenge:
                            geetest_result = await get_validate(gt, challenge)
                            if _conf.preference.geetest_url:
                                if on_geetest_callback and attempt.retry_state.attempt_number == 1:
                                    if isinstance(on_geetest_callback, Coroutine):
                                        await on_geetest_callback
                                    else:
                                        on_geetest_callback()
                                continue
                            else:
                                return BaseApiStatus(need_verify=True)
            return BaseApiStatus(success=True)

        except tenacity.RetryError as e:
            if is_incorrect_return(e):
                logger.exception(f"游戏签到 - 服务器没有正确返回")
                logger.debug(f"网络请求返回: {res.text}")
                return BaseApiStatus(incorrect_return=True)
            elif _conf.preference.geetest_url and gt and challenge:
                logger.error(f"游戏签到 - 进行人机验证失败")
                return BaseApiStatus(need_verify=True)
            else:
                logger.exception(f"游戏签到 - 请求失败")
                return BaseApiStatus(network_error=True)


class GenshinImpactSign(BaseGameSign):
    """
    原神 游戏签到
    """
    NAME = "原神"
    ACT_ID = "e202009291139501"
    GAME_ID = 2
    URL_REWARD = "https://api-takumi.mihoyo.com/event/bbs_sign_reward/home"
    URL_INFO = "https://api-takumi.mihoyo.com/event/bbs_sign_reward/info"
    URL_SIGN = "https://api-takumi.mihoyo.com/event/bbs_sign_reward/sign"


class HonkaiImpact3Sign(BaseGameSign):
    """
    崩坏3 游戏签到
    """
    NAME = "崩坏3"
    ACT_ID = "e202207181446311"
    GAME_ID = 1


class HoukaiGakuen2Sign(BaseGameSign):
    """
    崩坏学园2 游戏签到
    """
    NAME = "崩坏学园2"
    ACT_ID = "e202203291431091"
    GAME_ID = 3


class TearsOfThemisSign(BaseGameSign):
    """
    未定事件簿 游戏签到
    """
    NAME = "未定事件簿"
    ACT_ID = "e202202251749321"
    GAME_ID = 4


class StarRailSign(BaseGameSign):
    """
    崩坏：星穹铁道 游戏签到
    """
    NAME = "崩坏：星穹铁道"
    ACT_ID = "e202304121516551"
    GAME_ID = 6


BaseGameSign.AVAILABLE_GAME_SIGNS.add(GenshinImpactSign)
BaseGameSign.AVAILABLE_GAME_SIGNS.add(HonkaiImpact3Sign)
BaseGameSign.AVAILABLE_GAME_SIGNS.add(HoukaiGakuen2Sign)
BaseGameSign.AVAILABLE_GAME_SIGNS.add(TearsOfThemisSign)
BaseGameSign.AVAILABLE_GAME_SIGNS.add(StarRailSign)
