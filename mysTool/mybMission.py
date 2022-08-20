"""
### 米游币任务相关
"""
import asyncio
import traceback
from typing import List, Literal, Union

import httpx
from nonebot.log import logger

from .config import mysTool_config as conf
from .data import UserAccount
from .utils import check_login, generateDS

URL_SIGN = "https://bbs-api.mihoyo.com/apihub/app/api/signIn"
URL_GET_POST = "https://bbs-api.mihoyo.com/post/api/getForumPostList?forum_id={}&is_good=false&is_hot=false&page_size=20&sort_type=1"
URL_READ = "https://bbs-api.mihoyo.com/post/api/getPostFull?post_id={}"
URL_LIKE = "https://bbs-api.mihoyo.com/apihub/sapi/upvotePost"
URL_SHARE = "https://bbs-api.mihoyo.com/apihub/api/getShareConf?entity_id={}&entity_type=1"
HEADERS = {
    "Host": "bbs-api.mihoyo.com",
    "Referer": "https://app.mihoyo.com",
    'User-Agent': conf.device.USER_AGENT_MISSION,
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "x-rpc-channel": conf.device.X_RPC_CHANNEL_MISSION,
    "x-rpc-client_type": "2",
    "x-rpc-device_id": None,
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_MISSION,
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_MISSION,
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION_MISSION,
    "DS": None
}
GAME_ID = {
    "bh3": {
        "gids": 1,
        "fid": 1
    },
    "ys": {
        "gids": 2,
        "fid": 26
    },
    "bh2": {
        "gids": 3,
        "fid": 30
    },
    "wd": {
        "gids": 4,
        "fid": 37
    },
    "xq": {
        "gids": 5,
        "fid": 52
    }
}


class Mission:
    """
    米游币任务相关(需先初始化对象)
    """

    def __init__(self, account: UserAccount) -> None:
        self.account = account
        self.headers = HEADERS.copy()
        self.headers["x-rpc-device_id"] = account.deviceID
        self.client = httpx.AsyncClient(cookies=account.cookie)

    async def sign(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]) -> Union[int, Literal[-1, -2, -3]]:
        """
        签到

        参数:
            `game`: 游戏代号

        - 若返回 `-1` 说明用户登录失效
        - 若返回 `-2` 说明服务器没有正确返回
        - 若返回 `-3` 说明请求失败
        """
        data = {"gids": GAME_ID[game]["gids"]}
        self.headers["DS"] = generateDS(data)
        res = await self.client.post(URL_SIGN, headers=self.headers, json=data, timeout=conf.TIME_OUT)
        if not check_login(res.text):
            logger.info(
                conf.LOG_HEAD + "米游币任务 - 讨论区签到: 用户 {} 登录失效".format(self.account.phone))
            logger.debug(conf.LOG_HEAD + "网络请求返回: {}".format(res.text))
            return -1
        try:
            return res.json()["data"]["points"]
        except KeyError:
            logger.error(conf.LOG_HEAD + "米游币任务 - 讨论区签到: 服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + "网络请求返回: {1}".format(res.text))
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            return -2
        except:
            logger.error(conf.LOG_HEAD + "米游币任务 - 讨论区签到: 请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            return -3

    async def get_posts(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]) -> Union[List[str], None]:
        """
        获取文章ID列表，若失败返回`None`

        参数:
            `game`: 游戏代号
        """
        postID_list = []
        error_times = 0
        while error_times <= conf.MAX_RETRY_TIMES:
            try:
                self.headers["DS"] = generateDS()
                res = await self.client.get(URL_GET_POST.format(GAME_ID[game]["fid"]), headers=self.headers, timeout=conf.TIME_OUT)
                data = res.json()["data"]["list"]
                for post in data:
                    if post["self_operation"]["attitude"] == 0:
                        postID_list.append(post['post']['post_id'])
                break
            except KeyError:
                logger.error(conf.LOG_HEAD + "米游币任务 - 获取文章列表: 服务器没有正确返回")
                logger.debug(conf.LOG_HEAD + "网络请求返回: {1}".format(res.text))
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
            except:
                logger.error(conf.LOG_HEAD + "米游币任务 - 获取文章列表: 网络请求失败")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
        if error_times <= conf.MAX_RETRY_TIMES:
            return postID_list

    async def read(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"], readTimes: int = 5):
        """
        阅读

        参数:
            `game`: 游戏代号
            `readTimes`: 阅读文章数

        - 若执行成功，返回 `True`
        - 若返回 `-1` 说明用户登录失效
        - 若返回 `-2` 说明服务器没有正确返回或请求失败
        - 若返回 `-3` 说明请求失败
        - 若返回 `-4` 说明获取文章失败
        """
        count = 0
        error_times = 0
        postID_list = await self.get_posts(game)
        if postID_list is None:
            return -4
        while count < readTimes:
            await asyncio.sleep(conf.SLEEP_TIME)
            for postID in postID_list:
                if count == readTimes:
                    break
                self.headers["DS"] = generateDS()
                res = await self.client.get(URL_READ.format(postID), headers=self.headers, timeout=conf.TIME_OUT)
                if not check_login(res.text):
                    logger.info(
                        conf.LOG_HEAD + "米游币任务 - 阅读: 用户 {} 登录失效".format(self.account.phone))
                    logger.debug(conf.LOG_HEAD + "网络请求返回: {}".format(res.text))
                    return -1
                try:
                    if "self_operation" not in res.json()["data"]["post"]:
                        raise ValueError
                    count += 1
                except KeyError and ValueError:
                    logger.error(conf.LOG_HEAD + "米游币任务 - 阅读: 服务器没有正确返回")
                    logger.debug(conf.LOG_HEAD +
                                 "网络请求返回: {}".format(res.text))
                    logger.debug(conf.LOG_HEAD + traceback.format_exc())
                    error_times += 1
                    if error_times != conf.MAX_RETRY_TIMES:
                        continue
                    else:
                        return -2
                except:
                    logger.error(conf.LOG_HEAD + "米游币任务 - 阅读: 网络请求失败")
                    logger.debug(conf.LOG_HEAD + traceback.format_exc())
                    error_times += 1
                    if error_times != conf.MAX_RETRY_TIMES:
                        continue
                    else:
                        return -3
            postID_list = await self.get_posts(game)
            if postID_list is None:
                return -4

        return True

    async def like(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"], likeTimes: int = 10):
        """
        点赞文章

        参数:
            `game`: 游戏代号
            `likeTimes`: 点赞次数

        - 若执行成功，返回 `True`
        - 若返回 `-1` 说明用户登录失效
        - 若返回 `-2` 说明服务器没有正确返回或请求失败
        - 若返回 `-3` 说明请求失败
        - 若返回 `-4` 说明获取文章失败
        """
        count = 0
        error_times = 0
        postID_list = await self.get_posts(game)
        if postID_list is None:
            return -4
        while count < likeTimes:
            await asyncio.sleep(conf.SLEEP_TIME)
            for postID in postID_list:
                if count == likeTimes:
                    break
                self.headers["DS"] = generateDS()
                res = await self.client.post(URL_LIKE, headers=self.headers, json={'is_cancel': False,  'post_id': postID}, timeout=conf.TIME_OUT)
                if not check_login(res.text):
                    logger.info(
                        conf.LOG_HEAD + "米游币任务 - 点赞: 用户 {} 登录失效".format(self.account.phone))
                    logger.debug(conf.LOG_HEAD + "网络请求返回: {}".format(res.text))
                    return -1
                try:
                    if res.json()["data"] != "OK":
                        raise ValueError
                    count += 1
                except KeyError and ValueError:
                    logger.error(conf.LOG_HEAD + "米游币任务 - 点赞: 服务器没有正确返回")
                    logger.debug(conf.LOG_HEAD +
                                 "网络请求返回: {1}".format(res.text))
                    logger.debug(conf.LOG_HEAD + traceback.format_exc())
                    error_times += 1
                    if error_times != conf.MAX_RETRY_TIMES:
                        continue
                    else:
                        return -2
                except:
                    logger.error(conf.LOG_HEAD + "米游币任务 - 点赞: 网络请求失败")
                    logger.debug(conf.LOG_HEAD + traceback.format_exc())
                    error_times += 1
                    if error_times != conf.MAX_RETRY_TIMES:
                        continue
                    else:
                        return -3
            postID_list = await self.get_posts(game)
            if postID_list is None:
                return -4

        return True

    async def share(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]):
        """
        分享文章

        参数:
            `game`: 游戏代号

        - 若执行成功，返回 `True`
        - 若返回 `-1` 说明用户登录失效
        - 若返回 `-2` 说明服务器没有正确返回或请求失败
        - 若返回 `-3` 说明网络请求发送成功，但是可能未签到成功
        - 若返回 `-4` 说明获取文章失败
        """
        self.headers["DS"] = generateDS()
        postID_list = await self.get_posts(game)
        if postID_list is None:
            return -4
        error_times = 0
        while error_times <= conf.MAX_RETRY_TIMES:
            res = await self.client.post(URL_SHARE.format(postID_list[0]), headers=self.headers, timeout=conf.TIME_OUT)
            if not check_login(res.text):
                logger.info(
                    conf.LOG_HEAD + "米游币任务 - 分享: 用户 {} 登录失效".format(self.account.phone))
                logger.debug(conf.LOG_HEAD + "网络请求返回: {}".format(res.text))
                return -1
            try:
                if res.json()["data"] != "OK":
                    return -3
            except KeyError and ValueError:
                logger.error(conf.LOG_HEAD + "米游币任务 - 分享: 服务器没有正确返回")
                logger.debug(conf.LOG_HEAD + "网络请求返回: {}".format(res.text))
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
            except:
                logger.error(conf.LOG_HEAD + "米游币任务 - 分享: 网络请求失败")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
        if error_times <= conf.MAX_RETRY_TIMES:
            return True
        else:
            return -2

    async def __del__(self):
        await self.client.aclose()
