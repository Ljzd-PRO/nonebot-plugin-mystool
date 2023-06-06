import asyncio
from typing import List, Optional, Tuple, NewType

import httpx
import tenacity

from .base_api import device_login, device_save, ApiResultHandler, is_incorrect_return
from .data_model import BaseApiStatus, MissionStatus, MissionData, \
    MissionState
from .plugin_data import plugin_data_obj as conf
from .user_data import UserAccount
from .utils import logger, generate_ds, \
    get_async_retry

URL_SIGN = "https://bbs-api.mihoyo.com/apihub/app/api/signIn"
URL_GET_POST = "https://bbs-api.miyoushe.com/post/api/feeds/posts?fresh_action=1&gids={}&is_first_initialize=false" \
               "&last_id="
URL_READ = "https://bbs-api.miyoushe.com/post/api/getPostFull?post_id={}"
URL_LIKE = "https://bbs-api.miyoushe.com/apihub/sapi/upvotePost"
URL_SHARE = "https://bbs-api.miyoushe.com/apihub/api/getShareConf?entity_id={}&entity_type=1"
URL_MISSION = "https://api-takumi.mihoyo.com/apihub/wapi/getMissions?point_sn=myb"
URL_MISSION_STATE = "https://api-takumi.mihoyo.com/apihub/wapi/getUserMissionsState?point_sn=myb"
HEADERS_BASE = {
    "Host": "bbs-api.miyoushe.com",
    "Referer": "https://app.mihoyo.com",
    'User-Agent': conf.device.USER_AGENT_ANDROID_OTHER,
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "x-rpc-channel": conf.device.X_RPC_CHANNEL_ANDROID,
    "x-rpc-client_type": "2",
    "x-rpc-device_id": None,
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_ANDROID,
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_ANDROID,
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION_ANDROID,
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "DS": None
}
HEADERS_MISSION = {
    "Host": "api-takumi.mihoyo.com",
    "Origin": "https://webstatic.mihoyo.com",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": conf.device.USER_AGENT_MOBILE,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Referer": "https://webstatic.mihoyo.com/",
    "Accept-Encoding": "gzip, deflate, br"
}
HEADERS_GET_POSTS = {
    "Host": "bbs-api.miyoushe.com",
    "Accept": "*/*",
    "x-rpc-client_type": "1",
    "x-rpc-device_id": None,
    "x-rpc-channel": conf.device.X_RPC_CHANNEL,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION,
    "Referer": "https://app.mihoyo.com",
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_MOBILE,
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "User-Agent": conf.device.USER_AGENT_OTHER,
    "Connection": "keep-alive"
}

# 旧的API
HEADERS_OLD = {
    "Host": "bbs-api.mihoyo.com",
    "Referer": "https://app.mihoyo.com",
    'User-Agent': conf.device.USER_AGENT_ANDROID_OTHER,
    "x-rpc-app_version": "2.36.1",
    "x-rpc-channel": conf.device.X_RPC_CHANNEL_ANDROID,
    "x-rpc-client_type": "2",
    "x-rpc-device_id": None,
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_ANDROID,
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_ANDROID,
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION_ANDROID,
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "DS": None
}


class GameID:
    """
    米游社任务所需的gid和fid
    """

    def __init__(self, gids: int, fid: int):
        self.gids: int = gids
        self.fid: int = fid


GAME_ID = {
    "bbs": GameID(5, 0),
    # TODO: bbs fid暂时未知
    "bh3": GameID(1, 1),
    "ys": GameID(2, 26),
    "bh2": GameID(3, 30),
    "wd": GameID(4, 37),
    "xq": GameID(5, 52),
}
'''所有的gid和fid'''

Progress_Now = NewType("Progress_Now", int)
Myb_Num = NewType("Myb_Num", int)


class BaseMission:
    GIDS = 0
    FID = 0

    def __init__(self, account: UserAccount) -> None:
        """
        米游币任务相关

        :param account: 账号对象
        """
        self.account = account
        self.headers = HEADERS_BASE.copy()
        self.headers["x-rpc-device_id"] = account.device_id_android

    async def async_init(self):
        """
        初始化米游币任务(异步，返回`self`对象)(执行deviceLogin和saveDevice)
        """
        await device_login(self.account)
        await device_save(self.account)

    async def sign(self, retry: bool = True) -> Tuple[MissionStatus, Optional[int]]:
        """
        签到

        :param retry: 是否允许重试
        :return: (BaseApiStatus, 签到获得的米游币数量)
        """
        content = {"gids": self.GIDS}
        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    headers = HEADERS_OLD.copy()
                    headers["x-rpc-device_id"] = self.account.device_id_android
                    headers["DS"] = generate_ds(data=content)
                    async with httpx.AsyncClient() as client:
                        res = await client.post(URL_SIGN, headers=headers, json=content, timeout=conf.TIME_OUT)
                    api_result = ApiResultHandler(res.json())
                    if api_result.login_expired:
                        logger.info(
                            f"米游币任务 - 讨论区签到: 用户 {self.account.bbs_uid} 登录失效")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(login_expired=True), None
                    if api_result.invalid_ds:
                        logger.info(
                            f"米游币任务 - 讨论区签到: 用户 {self.account.bbs_uid} DS 校验失败")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(invalid_ds=True), None
                    return api_result.data["points"]
        except tenacity.RetryError as e:
            if is_incorrect_return(e):
                logger.exception(f"米游币任务 - 讨论区签到: 服务器没有正确返回")
                logger.debug(f"网络请求返回: {res.text}")
                return MissionStatus(incorrect_return=True), None
            else:
                logger.exception(f"米游币任务 - 讨论区签到: 请求失败")
                return MissionStatus(network_error=True), None

    async def get_posts(self, retry: bool = True) -> Tuple[BaseApiStatus, Optional[List[str]]]:
        """
        获取文章ID列表，若失败返回 `None`

        :param retry: 是否允许重试
        :return: (BaseApiStatus, 文章ID列表)
        """
        post_id_list = []
        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    headers = HEADERS_GET_POSTS.copy()
                    headers["x-rpc-device_id"] = self.account.device_id_ios
                    async with httpx.AsyncClient() as client:
                        res = await client.get(URL_GET_POST.format(self.GIDS), headers=headers,
                                               timeout=conf.TIME_OUT)
                    api_result = ApiResultHandler(res.json())
                    for post in api_result.data["list"]:
                        if post["self_operation"]["attitude"] == 0:
                            post_id_list.append(post['post']['post_id'])
                    break
            return BaseApiStatus(success=True), post_id_list
        except tenacity.RetryError as e:
            if is_incorrect_return(e):
                logger.exception(f"米游币任务 - 获取文章列表: 服务器没有正确返回")
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
        get_post_status, posts = await self.get_posts(retry)
        if not get_post_status:
            return MissionStatus(failed_getting_post=True)
        while count < read_times:
            for post_id in posts:
                if count == read_times:
                    break
                try:
                    async for attempt in get_async_retry(retry):
                        with attempt:
                            self.headers["DS"] = generate_ds(platform="android")
                            async with httpx.AsyncClient() as client:
                                res = await client.get(URL_READ.format(post_id), headers=self.headers,
                                                       timeout=conf.TIME_OUT)
                            api_result = ApiResultHandler(res.json())
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
                        logger.exception(f"米游币任务 - 阅读: 服务器没有正确返回")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(incorrect_return=True)
                    else:
                        logger.exception(f"米游币任务 - 阅读: 请求失败")
                        return MissionStatus(network_error=True)
                if count != read_times:
                    await asyncio.sleep(conf.preference.sleep_time)
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
        get_post_status, posts = await self.get_posts(retry)
        if not get_post_status:
            return MissionStatus(failed_getting_post=True)
        while count < like_times:
            for post_id in posts:
                if count == like_times:
                    break
                try:
                    async for attempt in get_async_retry(retry):
                        with attempt:
                            headers = HEADERS_OLD.copy()
                            headers["x-rpc-device_id"] = self.account.device_id_android
                            headers["DS"] = generate_ds(platform="android")
                            async with httpx.AsyncClient() as client:
                                res = await client.post(URL_LIKE, headers=headers,
                                                        json={'is_cancel': False, 'post_id': post_id},
                                                        timeout=conf.TIME_OUT)
                            api_result = ApiResultHandler(res.json())
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
                            if api_result.message == "帖子不存在":
                                continue
                            if api_result.message != "OK":
                                raise ValueError
                            count += 1
                except tenacity.RetryError as e:
                    if is_incorrect_return(e, ValueError):
                        logger.exception(f"米游币任务 - 点赞: 服务器没有正确返回")
                        logger.debug(f"网络请求返回: {res.text}")
                        return MissionStatus(incorrect_return=True)
                    else:
                        logger.exception(f"米游币任务 - 点赞: 请求失败")
                        return MissionStatus(network_error=True)
                if count != like_times:
                    await asyncio.sleep(conf.preference.sleep_time)
            get_post_status, posts = await self.get_posts(retry)
            if not get_post_status:
                return MissionStatus(failed_getting_post=True)

        return MissionStatus(success=True)

    async def share(self, retry: bool = True):
        """
        分享文章

        :param retry: 是否允许重试
        """
        get_post_status, posts = await self.get_posts(retry)
        if not get_post_status or not posts:
            return MissionStatus(failed_getting_post=True)
        try:
            async for attempt in get_async_retry(retry):
                with attempt:
                    headers = HEADERS_OLD.copy()
                    headers["x-rpc-device_id"] = self.account.device_id_android
                    headers["DS"] = generate_ds(platform="android")
                    async with httpx.AsyncClient() as client:
                        res = await client.get(URL_SHARE.format(posts[0]), headers=headers,
                                               timeout=conf.TIME_OUT)
                    api_result = ApiResultHandler(res.json())
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
                    if api_result.message == "帖子不存在":
                        continue
                    if api_result.message != "OK":
                        raise ValueError
        except tenacity.RetryError as e:
            if is_incorrect_return(e, ValueError):
                logger.exception(f"米游币任务 - 分享: 服务器没有正确返回")
                logger.debug(f"网络请求返回: {res.text}")
                return MissionStatus(incorrect_return=True)
            else:
                logger.exception(f"米游币任务 - 分享: 请求失败")
                return MissionStatus(network_error=True)
        return MissionStatus(success=True)


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
                    res = await client.get(URL_MISSION, headers=HEADERS_MISSION, cookies=account.cookies,
                                           timeout=conf.preference.timeout)
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
            logger.exception(f"获取米游币任务列表: 服务器没有正确返回")
            logger.debug(f"网络请求返回: {res.text}")
            return BaseApiStatus(incorrect_return=True), None
        else:
            logger.exception(f"获取米游币任务列表: 请求失败")
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
                    res = await client.get(URL_MISSION_STATE, headers=HEADERS_MISSION, cookies=account.cookies,
                                           timeout=conf.preference.timeout)
                api_result = ApiResultHandler(res.json())
                if api_result.login_expired:
                    logger.info(
                        f"获取米游币任务完成情况: 用户 {account.bbs_uid} 登录失效")
                    logger.debug(f"网络请求返回: {res.text}")
                    return BaseApiStatus(login_expired=True), None
                state_dict = {}
                for mission in missions:
                    try:
                        state_dict.setdefault(mission, list(filter(lambda state: state["mission_key"] ==
                                                                                 mission.key_name,
                                                                   api_result.data["states"]))[0][
                            "happened_times"])
                    except IndexError:
                        state_dict.setdefault(mission, 0)
                return BaseApiStatus(success=True), MissionState(state_dict=state_dict,
                                                                 current_myb=api_result.data["total_points"])
    except tenacity.RetryError as e:
        if is_incorrect_return(e):
            logger.exception(f"获取米游币任务完成情况: 服务器没有正确返回")
            logger.debug(f"网络请求返回: {res.text}")
            return BaseApiStatus(incorrect_return=True), None
        else:
            logger.exception(f"获取米游币任务完成情况: 请求失败")
            return BaseApiStatus(network_error=True), None