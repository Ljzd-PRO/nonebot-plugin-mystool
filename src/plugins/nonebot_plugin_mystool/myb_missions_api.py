"""
### 米游社的米游币任务相关API
"""
import asyncio
from typing import List, Optional, Tuple, Set, Type, Union

import httpx
import tenacity
import random

from .data_model import BaseApiStatus, MissionStatus, MissionData, \
    MissionState
from .plugin_data import PluginDataManager
from .simple_api import ApiResultHandler, is_incorrect_return
from .user_data import UserAccount
from .exceptions import MystoolException
from .utils import logger, generate_ds, \
    get_async_retry, get_pass_challenge

_conf = PluginDataManager.plugin_data_obj

URL_SIGN = "https://bbs-api.miyoushe.com/apihub/app/api/signIn"
URL_GET_POST = "https://bbs-api.miyoushe.com/post/api/getForumPostList?is_hot=false&is_good=false&sort_type=2&last_id=&page_size=20&forum_id={}"

URL_READ = "https://bbs-api.miyoushe.com/post/api/getPostFull?post_id={}"
URL_LIKE = "https://bbs-api.miyoushe.com/apihub/sapi/upvotePost"
URL_SHARE = "https://bbs-api.miyoushe.com/apihub/api/getShareConf?entity_id={}&entity_type=1"
URL_MISSION = "https://bbs-api.miyoushe.com/apihub/wapi/getMissions?point_sn=myb"
URL_MISSION_STATE = "https://bbs-api.miyoushe.com/apihub/wapi/getUserMissionsState?point_sn=myb"

HEADERS_BASE = {
    "Host": "bbs-api.miyoushe.com",
    "Referer": "https://app.mihoyo.com",
    'User-Agent': _conf.device_config.USER_AGENT_ANDROID_OTHER,
    "x-rpc-app_version": _conf.device_config.X_RPC_APP_VERSION,
    "x-rpc-channel": _conf.device_config.X_RPC_CHANNEL_ANDROID,
    "x-rpc-client_type": "2",
    "x-rpc-device_id": None,
    "x-rpc-device_model": _conf.device_config.X_RPC_DEVICE_MODEL_ANDROID,
    "x-rpc-device_name": _conf.device_config.X_RPC_DEVICE_NAME_ANDROID,
    "x-rpc-sys_version": _conf.device_config.X_RPC_SYS_VERSION_ANDROID,
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "DS": None
}
HEADERS_MISSION = {
    "Host": "api-takumi.mihoyo.com",
    "Origin": "https://webstatic.mihoyo.com",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": _conf.device_config.USER_AGENT_MOBILE,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Referer": "https://webstatic.mihoyo.com/",
    "Accept-Encoding": "gzip, deflate, br"
}
HEADERS_GET_POSTS = {
    "Host": "bbs-api.miyoushe.com",
    "Accept": "*/*",
    "x-rpc-client_type": "1",
    "x-rpc-device_id": None,
    "x-rpc-channel": _conf.device_config.X_RPC_CHANNEL,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-rpc-sys_version": _conf.device_config.X_RPC_SYS_VERSION,
    "Referer": "https://app.mihoyo.com",
    "x-rpc-device_name": _conf.device_config.X_RPC_DEVICE_NAME_MOBILE,
    "x-rpc-app_version": _conf.device_config.X_RPC_APP_VERSION,
    "User-Agent": _conf.device_config.USER_AGENT_OTHER,
    "Connection": "keep-alive"
}

class BaseMission:
    """
    米游币任务基类
    """
    NAME = ""
    """米游社分区名字"""
    GIDS = 0
    FID = 0

    SIGN = "continuous_sign"
    '''签到任务的 mission_key'''
    VIEW = "view_post_0"
    '''阅读任务的 mission_key'''
    LIKE = "post_up_0"
    '''点赞任务的 mission_key'''
    SHARE = "share_post_0"
    '''分享任务的 mission_key'''

    AVAILABLE_GAMES: Set[Type["BaseMission"]] = set()
    """可用的子类"""

    def __init__(self, account: UserAccount) -> None:
        """
        米游币任务相关

        :param account: 账号对象
        """
        self.account = account

    async def sign(self, retry: bool = True) -> MissionStatus:
        """
        签到

        :param retry: 是否允许重试
        :return: (BaseApiStatus, 签到获得的米游币数量)
        """
        content = {"gids": self.GIDS}
        challenge = None
        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    headers = HEADERS_BASE.copy()
                    headers["x-rpc-device_id"] = self.account.device_id_android
                    headers["DS"] = generate_ds(data=content)
                    if challenge:
                        headers["x-rpc-challenge"] = challenge
                    async with httpx.AsyncClient() as client:
                        res = await client.post(
                            URL_SIGN,
                            headers=headers,
                            json=content,
                            timeout=_conf.preference.timeout,
                            cookies=self.account.cookies.dict(v2_stoken=True, cookie_type=True)
                        )
                    api_result = ApiResultHandler(res.json())
                    logger.info(f"正在签到: {self.NAME} {api_result.content}")
                    if api_result.login_expired:
                        logger.info(
                            f"米游币任务 - 讨论区签到: 用户 {self.account.bbs_uid} 登录失效")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(login_expired=True)
                    if api_result.invalid_ds:
                        logger.info(
                            f"米游币任务 - 讨论区签到: 用户 {self.account.bbs_uid} DS 校验失败")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(invalid_ds=True)
                    if api_result.need_verify:
                        logger.info(
                            f"米游币任务 - 讨论区签到: 用户 {self.account.bbs_uid} 需要验证码")
                        logger.debug(f"网络请求返回: {res.text}")
                        if _conf.preference.geetest_url:
                            if attempt.retry_state.attempt_number == 1 and not challenge:
                                challenge = await get_pass_challenge(headers=headers, cookies=self.account.cookies.dict(v2_stoken=True, cookie_type=True))
                                raise MystoolException("讨论区签到遇到验证码, 重试")
                        else:
                            return MissionStatus(need_verify=True)
                    if challenge:
                        return MissionStatus(success=True, need_verify=True)
                    else:
                        return MissionStatus(success=True)
        except MystoolException:
            return MissionStatus(need_verify=True)
        except tenacity.RetryError as e:
            if is_incorrect_return(e):
                logger.error(f"米游币任务 - 讨论区签到: 服务器没有正确返回")
                logger.debug(f"网络请求返回: {res.text}")
                return MissionStatus(incorrect_return=True)
            else:
                logger.exception("米游币任务 - 讨论区签到: 请求失败")
                return MissionStatus(network_error=True)

    async def get_posts(self, retry: bool = True) -> Tuple[BaseApiStatus, Optional[List[str]]]:
        """
        获取文章ID列表，若失败返回 `None`

        :param retry: 是否允许重试
        :return: (BaseApiStatus, 文章ID列表)
        """
        post_list = []
        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    headers = HEADERS_BASE.copy()
                    headers["x-rpc-device_id"] = self.account.device_id_android
                    headers["DS"] = generate_ds(platform="android")
                    async with httpx.AsyncClient() as client:
                        res = await client.get(
                            URL_GET_POST.format(26),
                            headers=headers,
                            timeout=_conf.preference.timeout
                        )
                    api_result = ApiResultHandler(res.json())
                    for post in api_result.data["list"]:
                        if post["self_operation"]["attitude"] == 0:
                            post_dara = {"post_id": post['post']['post_id'], "title": post['post']['subject']}
                            post_list.append(post_dara) if post_dara not in post_list else None
                    if len(post_list) < 5:
                        raise MystoolException("文章数量不足")
                    break
            return BaseApiStatus(success=True), post_list
        except tenacity.RetryError as e:
            if is_incorrect_return(e):
                logger.error(f"米游币任务 - 获取文章列表: 服务器没有正确返回")
                logger.debug(f"网络请求返回: {res.text}")
                return BaseApiStatus(incorrect_return=True), None
            else:
                logger.exception(f"米游币任务 - 获取文章列表: 请求失败")
                return BaseApiStatus(network_error=True), None

    async def read(self, read_times: int = 5, retry: bool = True) -> MissionStatus:
        """
        阅读

        :param read_times: 阅读文章数
        :param retry: 是否允许重试
        """
        count = 0
        get_post_status, post_list = await self.get_posts(retry)
        post_list = random.sample(post_list[0:8], 5)
        if not get_post_status:
            return MissionStatus(failed_getting_post=True)
        while count < read_times:
            for post_data in post_list:
                post_id = post_data["post_id"]
                title = post_data["title"]
                if count == read_times:
                    break
                try:
                    async for attempt in get_async_retry(retry):
                        with attempt:
                            headers = HEADERS_BASE.copy()
                            headers["x-rpc-device_id"] = self.account.device_id_android
                            headers["DS"] = generate_ds(platform="android")
                            async with httpx.AsyncClient() as client:
                                res = await client.get(
                                    URL_READ.format(post_id),
                                    headers=headers,
                                    timeout=_conf.preference.timeout,
                                    cookies=self.account.cookies.dict(v2_stoken=True, cookie_type=True)
                                )
                            api_result = ApiResultHandler(res.json())
                            name = api_result.data["post"]["post"]["subject"]
                            logger.debug(f"正在阅读: {name}")
                            if api_result.login_expired:
                                logger.info(
                                    f"米游币任务 - 阅读: 用户 {self.account.bbs_uid} 登录失效")
                                logger.debug(f"网络请求返回: {res.text}")
                                return MissionStatus(login_expired=True)
                            if api_result.invalid_ds:
                                logger.info(
                                    f"米游币任务 - 阅读: 用户 {self.account.bbs_uid} DS 校验失败")
                                logger.debug(f"网络请求返回: {res.text}")
                                return MissionStatus(invalid_ds=True)
                            if api_result.message == "帖子不存在":
                                continue
                            temp = api_result.data.get("post")
                            if temp is not None and "self_operation" not in temp:
                                raise ValueError
                            count += 1
                except tenacity.RetryError as e:
                    if is_incorrect_return(e, ValueError):
                        logger.error(f"米游币任务 - 阅读: 服务器没有正确返回")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(incorrect_return=True)
                    else:
                        logger.exception(f"米游币任务 - 阅读: 请求失败")
                        return MissionStatus(network_error=True)
                if count != read_times:
                    await asyncio.sleep(_conf.preference.sleep_time)
            get_post_status, posts = await self.get_posts(retry)
            if not get_post_status:
                return MissionStatus(failed_getting_post=True)

        return MissionStatus(success=True)

    async def like(self, like_times: int = 10, retry: bool = True) -> MissionStatus:
        """
        点赞文章

        :param like_times: 点赞次数
        :param retry: 是否允许重试
        """
        count = 0
        challenge = None
        geetest_num = 0
        get_post_status, post_list = await self.get_posts(retry)
        post_list = random.sample(post_list[5:17], 10)
        if not get_post_status:
            return MissionStatus(failed_getting_post=True)
        while count < like_times:
            for post_data in post_list:
                post_id = post_data["post_id"]
                title = post_data["title"]
                if count == like_times:
                    break
                try:
                    async for attempt in get_async_retry(retry):
                        with attempt:
                            headers = HEADERS_BASE.copy()
                            headers["x-rpc-device_id"] = self.account.device_id_android
                            headers["DS"] = generate_ds(platform="android")
                            if challenge and challenge != True:
                                logger.info(challenge)
                                headers["x-rpc-challenge"] = challenge
                            async with httpx.AsyncClient() as client:
                                res = await client.post(
                                    URL_LIKE, headers=headers,
                                    json={'post_id': post_id, 'is_cancel': False},
                                    timeout=_conf.preference.timeout,
                                    cookies=self.account.cookies.dict(v2_stoken=True, cookie_type=True)
                                )
                            api_result = ApiResultHandler(res.json())
                            logger.info(f"点赞: {title} {api_result.content}")
                            if api_result.login_expired:
                                logger.info(
                                    f"米游币任务 - 点赞: 用户 {self.account.bbs_uid} 登录失效")
                                logger.debug(f"网络请求返回: {res.text}")
                                return MissionStatus(login_expired=True)
                            if api_result.invalid_ds:
                                logger.info(
                                    f"米游币任务 - 点赞: 用户 {self.account.bbs_uid} DS 校验失败")
                                logger.debug(f"网络请求返回: {res.text}")
                                return MissionStatus(invalid_ds=True)
                            if api_result.need_verify:
                                logger.info(
                                    f"米游币任务 - 点赞: 用户 {self.account.bbs_uid} 需要验证码")
                                logger.debug(f"网络请求返回: {res.text}")
                                if _conf.preference.geetest_url:
                                    if attempt.retry_state.attempt_number == 1 and geetest_num <= 3:
                                        challenge = await get_pass_challenge(headers=headers, cookies=self.account.cookies.dict(v2_stoken=True, cookie_type=True))
                                        geetest_num+=1
                                        raise MystoolException("点赞遇到验证码, 重试")
                            if api_result.message == "帖子不存在":
                                logger.info(f"米游币任务 - 点赞: 帖子不存在")
                                continue
                            if api_result.message != "OK":
                                raise ValueError
                            count += 1
                except MystoolException:
                    return MissionStatus(need_verify=True)
                except tenacity.RetryError as e:
                    if is_incorrect_return(e, ValueError):
                        logger.error(f"米游币任务 - 点赞: 服务器没有正确返回")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(incorrect_return=True)
                    else:
                        logger.exception(f"米游币任务 - 点赞: 请求失败")
                        return MissionStatus(network_error=True)
                if count != like_times:
                    await asyncio.sleep(_conf.preference.sleep_time)
        if challenge:
            return MissionStatus(success=True, need_verify=True)
        else:
            return MissionStatus(success=True)

    async def share(self, retry: bool = True):
        """
        分享文章

        :param retry: 是否允许重试
        """
        get_post_status, post_list = await self.get_posts(retry)
        post_list = random.sample(post_list[-3:-1], 1)
        challenge = None
        if not get_post_status or not post_list:
            return MissionStatus(failed_getting_post=True)
        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    headers = HEADERS_BASE.copy()
                    headers["x-rpc-device_id"] = self.account.device_id_android
                    headers["DS"] = generate_ds(platform="android")
                    async with httpx.AsyncClient() as client:
                        res = await client.get(
                            URL_SHARE.format(post_list[0]["post_id"]),
                            headers=headers,
                            timeout=_conf.preference.timeout,
                            cookies=self.account.cookies.dict(v2_stoken=True, cookie_type=True)
                        )
                    api_result = ApiResultHandler(res.json())
                    name = api_result.data["title"]
                    logger.info(f"分享: {name} {api_result.content}")
                    if api_result.login_expired:
                        logger.info(
                            f"米游币任务 - 分享: 用户 {self.account.bbs_uid} 登录失效")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(login_expired=True)
                    if api_result.invalid_ds:
                        logger.info(
                            f"米游币任务 - 分享: 用户 {self.account.bbs_uid} DS 校验失败")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(invalid_ds=True)
                    if api_result.need_verify:
                        logger.info(
                            f"米游币任务 - 分享: 用户 {self.account.bbs_uid} 需要验证码")
                        logger.debug(f"网络请求返回: {res.text}")
                        if _conf.preference.geetest_url:
                            if attempt.retry_state.attempt_number == 1:
                                challenge = "yzm"
                                raise MystoolException("分享遇到验证码, 重试")
                    if api_result.message == "帖子不存在":
                        continue
                    if api_result.message != "OK":
                        raise ValueError
        except MystoolException:
            return MissionStatus(need_verify=True)
        except tenacity.RetryError as e:
            if is_incorrect_return(e, ValueError):
                logger.error(f"米游币任务 - 分享: 服务器没有正确返回")
                logger.debug(f"网络请求返回: {res.text}")
                return MissionStatus(incorrect_return=True)
            else:
                logger.exception(f"米游币任务 - 分享: 请求失败")
                return MissionStatus(network_error=True)
        if challenge:
            return MissionStatus(success=True, need_verify=True)
        else:
            return MissionStatus(success=True)


class GenshinImpactMission(BaseMission):
    """
    原神 米游币任务
    """
    NAME = "原神"
    GIDS = 2
    FID = 26


class HonkaiImpact3Mission(BaseMission):
    """
    崩坏3 米游币任务
    """
    NAME = "崩坏3"
    GIDS = 1
    FID = 1


class HoukaiGakuen2Mission(BaseMission):
    """
    崩坏学园2 米游币任务
    """
    NAME = "崩坏学园2"
    GIDS = 3
    FID = 30


class TearsOfThemisMission(BaseMission):
    """
    未定事件簿 米游币任务
    """
    NAME = "未定事件簿"
    GIDS = 4
    FID = 37


class StarRailMission(BaseMission):
    """
    崩坏：星穹铁道 米游币任务
    """
    NAME = "崩坏：星穹铁道"
    GIDS = 5
    FID = 52


class BBSMission(BaseMission):
    """
    大别野 米游币任务
    """
    NAME = "大别野"
    GIDS = 5
    # TODO: bbs fid暂时未知


BaseMission.AVAILABLE_GAMES.add(GenshinImpactMission)
BaseMission.AVAILABLE_GAMES.add(HonkaiImpact3Mission)
BaseMission.AVAILABLE_GAMES.add(HoukaiGakuen2Mission)
BaseMission.AVAILABLE_GAMES.add(TearsOfThemisMission)
BaseMission.AVAILABLE_GAMES.add(StarRailMission)
BaseMission.AVAILABLE_GAMES.add(BBSMission)


async def get_missions(account: UserAccount, retry: bool = True) -> Tuple[BaseApiStatus, Optional[List[MissionData]]]:
    """
    获取米游币任务信息

    :param account: 用户账号
    :param retry: 是否允许重试
    """
    try:
        async for attempt in get_async_retry(retry):
            with attempt:
                async with httpx.AsyncClient() as client:
                    res = await client.get(URL_MISSION, headers=HEADERS_MISSION,
                                           cookies=account.cookies.dict(v2_stoken=True, cookie_type=True),
                                           timeout=_conf.preference.timeout)
                api_result = ApiResultHandler(res.json())
                if api_result.login_expired:
                    logger.info(
                        f"获取米游币任务列表: 用户 {account.bbs_uid} 登录失效")
                    logger.debug(f"网络请求返回: {res.text}")
                    return BaseApiStatus(login_expired=True), None
                mission_list: List[MissionData] = []
                for mission in api_result.data["missions"]:
                    mission_list.append(MissionData.parse_obj(mission))
                return BaseApiStatus(success=True), mission_list
    except tenacity.RetryError as e:
        if is_incorrect_return(e):
            logger.error(f"获取米游币任务列表: 服务器没有正确返回")
            logger.debug(f"网络请求返回: {res.text}")
            return BaseApiStatus(incorrect_return=True), None
        else:
            logger.exception("获取米游币任务列表: 请求失败")
            return BaseApiStatus(network_error=True), None


async def get_missions_state(account: UserAccount, retry: bool = True) -> Tuple[BaseApiStatus, Optional[MissionState]]:
    """
    获取米游币任务完成情况

    :param account: 用户账号
    :param retry: 是否允许重试
    """
    get_missions_status, missions = await get_missions(account)
    if not get_missions_status:
        return get_missions_status, None
    try:
        async for attempt in get_async_retry(retry):
            with attempt:
                async with httpx.AsyncClient() as client:
                    res = await client.get(URL_MISSION_STATE, headers=HEADERS_MISSION,
                                           cookies=account.cookies.dict(v2_stoken=True, cookie_type=True),
                                           timeout=_conf.preference.timeout)
                api_result = ApiResultHandler(res.json())
                if api_result.login_expired:
                    logger.info(
                        f"获取米游币任务完成情况: 用户 {account.bbs_uid} 登录失效")
                    logger.debug(f"网络请求返回: {res.text}")
                    return BaseApiStatus(login_expired=True), None
                state_dict = {}
                for mission in missions:
                    try:
                        current = list(filter(lambda state: state["mission_key"] == mission.mission_key,
                                              api_result.data["states"]))[0]["happened_times"]
                        state_dict.setdefault(mission.mission_key, (mission, current))
                    except IndexError:
                        state_dict.setdefault(mission.mission_key, (mission, 0))
                return BaseApiStatus(success=True), MissionState(state_dict=state_dict,
                                                                 current_myb=api_result.data["total_points"])
    except tenacity.RetryError as e:
        if is_incorrect_return(e):
            logger.error("获取米游币任务完成情况: 服务器没有正确返回")
            logger.debug(f"网络请求返回: {res.text}")
            return BaseApiStatus(incorrect_return=True), None
        else:
            logger.exception("获取米游币任务完成情况: 请求失败")
            return BaseApiStatus(network_error=True), None
