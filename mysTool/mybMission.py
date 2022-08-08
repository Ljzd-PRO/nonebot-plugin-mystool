"""
### 米游币任务相关
"""
import httpx
import traceback
import asyncio
from .config import mysTool_config as conf
from .data import UserAccount
from .utils import generateDS
from typing import Literal, Union
from nonebot.log import logger

URL_SIGN = "https://bbs-api.mihoyo.com/apihub/app/api/signIn"
URL_GET_POST = "https://bbs-api.mihoyo.com/post/api/getForumPostList?forum_id={}&is_good=false&is_hot=false&page_size=20&sort_type=1"
URL_READ = "https://bbs-api.mihoyo.com/post/api/getPostFull?post_id={}"
URL_LIKE = "https://bbs-api.mihoyo.com/apihub/sapi/upvotePost"
URL_SHARE = "https://bbs-api.mihoyo.com/apihub/api/getShareConf?entity_id={}&entity_type=1"
HEADERS = {
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-cn",
    "Connection": "keep-alive",
    "Host": "bbs-api.mihoyo.com",
    "Referer": "https://app.mihoyo.com",
    'User-Agent': conf.device.USER_AGENT_OTHER,
    "x-rpc-app_version": conf.device.X_RPC_APP_VERSION,
    "x-rpc-channel": conf.device.X_RPC_CHANNEL,
    "x-rpc-client_type": "1",
    "x-rpc-device_id": None,
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_MOBILE,
    "x-rpc-device_name": conf.device.X_RPC_DEVICE_NAME_MOBILE,
    "x-rpc-sys_version": conf.device.X_RPC_SYS_VERSION,
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
        self.cookie = {"stuid": account.bbsUID,
                       "stoken": account.cookie["stoken"]}
        self.client = httpx.AsyncClient(cookies=self.cookie)
        self.mybNum: int = 0

    async def sign(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]):
        """
        签到

        参数:
            `game`: 游戏代号

        若执行成功，返回 `True`\n
        若执行失败，返回 `False`
        """
        headers = HEADERS.copy()
        headers.setdefault("DS", generateDS())
        res = await self.client.post(URL_SIGN, headers=headers, json={"gids": GAME_ID[game]["gids"]})
        try:
            self.mybNum = res.json()["data"]["points"]
            return True
        except KeyError:
            logger.error(conf.LOG_HEAD + "米游币任务 - 讨论区签到: 服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            return False

    async def get_posts(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]) -> Union[list[str], None]:
        """
        获取文章ID列表，若返回None说明失败

        参数:
            `game`: 游戏代号
        """
        headers = HEADERS.copy()
        headers.setdefault("DS", generateDS())
        res = await self.client.get(URL_GET_POST.format(GAME_ID[game]["fid"]), headers=headers)
        postID_list = []
        error_times = 0
        while error_times <= conf.MAX_RETRY_TIMES:
            try:
                data = res.json()["data"]["list"]
                for post in data:
                    if post["self_operation"]["attitude"] == 0:
                        postID_list.append(post['post']['post_id'])
                break
            except KeyError:
                logger.error(conf.LOG_HEAD + "米游币任务 - 获取文章列表: 服务器没有正确返回")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
            except:
                logger.error(conf.LOG_HEAD + "米游币任务 - 获取文章列表: 网络请求失败")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
            return postID_list
        return None

    async def read(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"], readTimes: int = 3):
        """
        阅读

        参数:
            `game`: 游戏代号
            `readTimes`: 阅读文章数

        若执行成功，返回 `True`\n
        若执行失败，返回 `False`
        """
        headers = HEADERS.copy()
        headers.setdefault("DS", None)
        count = 0
        error_times = 0
        postID_list = await self.get_posts(game)
        if postID_list is None:
            return False
        while count < readTimes:
            await asyncio.sleep(conf.SLEEP_TIME)
            for postID in postID_list:
                if count == readTimes:
                    break
                headers["DS"] = generateDS()
                res = await self.client.get(URL_READ.format(postID), headers=headers)
                try:
                    if "self_operation" not in res.json()["data"]["post"]:
                        raise ValueError
                    count += 1
                except KeyError and ValueError:
                    logger.error(conf.LOG_HEAD + "米游币任务 - 阅读: 服务器没有正确返回")
                    logger.debug(conf.LOG_HEAD + traceback.format_exc())
                    error_times += 1
                    if error_times != conf.MAX_RETRY_TIMES:
                        continue
                    else:
                        return False
                except:
                    logger.error(conf.LOG_HEAD + "米游币任务 - 阅读: 网络请求失败")
                    logger.debug(conf.LOG_HEAD + traceback.format_exc())
                    error_times += 1
                    if error_times != conf.MAX_RETRY_TIMES:
                        continue
                    else:
                        return False
            postID_list = await self.get_posts(game)
            if postID_list is None:
                return False

        return True

    async def like(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"], likeTimes: int = 10):
        """
        点赞文章

        参数:
            `game`: 游戏代号
            `likeTimes`: 点赞次数

        若执行成功，返回 `True`\n
        若执行失败，返回 `False`
        """
        headers = HEADERS.copy()
        headers.setdefault("DS", None)
        count = 0
        error_times = 0
        postID_list = await self.get_posts(game)
        if postID_list is None:
            return False
        while count < likeTimes:
            await asyncio.sleep(conf.SLEEP_TIME)
            for postID in postID_list:
                if count == likeTimes:
                    break
                headers["DS"] = generateDS()
                res = await self.client.post(URL_LIKE, headers=headers, json={'is_cancel': False,  'post_id': postID})
                try:
                    if res.json()["data"] != "OK":
                        raise ValueError
                    count += 1
                except KeyError and ValueError:
                    logger.error(conf.LOG_HEAD + "米游币任务 - 点赞: 服务器没有正确返回")
                    logger.debug(conf.LOG_HEAD + traceback.format_exc())
                    error_times += 1
                    if error_times != conf.MAX_RETRY_TIMES:
                        continue
                    else:
                        return False
                except:
                    logger.error(conf.LOG_HEAD + "米游币任务 - 点赞: 网络请求失败")
                    logger.debug(conf.LOG_HEAD + traceback.format_exc())
                    error_times += 1
                    if error_times != conf.MAX_RETRY_TIMES:
                        continue
                    else:
                        return False
            postID_list = await self.get_posts(game)
            if postID_list is None:
                return False

        return True

    async def share(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]):
        """
        分享文章

        参数:
            `game`: 游戏代号

        若执行成功，返回 `True`\n
        若执行失败，返回 `False`
        """
        headers = HEADERS.copy()
        headers.setdefault("DS", generateDS())
        postID_list = await self.get_posts(game)
        if postID_list is None:
            return False
        error_times = 0
        while error_times <= conf.MAX_RETRY_TIMES:
            res = await self.client.post(URL_SHARE.format(postID_list[0]), headers=headers)
            try:
                if res.json()["data"] != "OK":
                    raise ValueError
                count += 1
            except KeyError and ValueError:
                logger.error(conf.LOG_HEAD + "米游币任务 - 分享: 服务器没有正确返回")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
                if error_times != conf.MAX_RETRY_TIMES:
                    continue
                else:
                    return False
            except:
                logger.error(conf.LOG_HEAD + "米游币任务 - 分享: 网络请求失败")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
                if error_times != conf.MAX_RETRY_TIMES:
                    continue
                else:
                    return False

        return True

    async def __del__(self):
        await self.client.aclose()


# 所有任务一体的函数
'''
async def get_posts(game: Literal["bh3", "ys", "bh2", "wd", "xq"], client: httpx.AsyncClient) -> Union[list[str], None]:
    headers = HEADERS.copy()
    headers.setdefault("DS", generateDS())
    res = await client.get(URL_GET_POST.format(GAME_ID[game]["fid"]), headers=headers)
    postID_list = []
    error_times = 0
    while error_times <= conf.MAX_RETRY_TIMES:
        try:
            data = res.json()["data"]["list"]
            for post in data:
                if post["self_operation"]["attitude"] == 0:
                    postID_list.append(post['post']['post_id'])
            break
        except KeyError:
            logger.error(conf.LOG_HEAD + "米游币任务 - 获取文章列表: 服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            error_times += 1
        except:
            logger.error(conf.LOG_HEAD + "米游币任务 - 获取文章列表: 网络请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            error_times += 1
        return postID_list
    return None


async def start(account: UserAccount, game: Literal["bh3", "ys", "bh2", "wd", "xq"], readTimes: int = 3, likeTimes: int = 10):
    headers = HEADERS.copy()
    client = httpx.AsyncClient(cookies=account.cookie)

    headers.setdefault("DS", generateDS())
    res = await client.post(URL_SIGN, headers=headers, json={"gids": GAME_ID[game]["gids"]})
    try:
        mybNum: int = res.json()["data"]["points"]
    except KeyError:
        logger.error(conf.LOG_HEAD + "米游币任务 - 讨论区签到: 服务器没有正确返回")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())

    count = 0
    error_times = 0
    postID_list = await get_posts(game)
    if postID_list is None:
        return False
    while count < readTimes:
        await asyncio.sleep(conf.SLEEP_TIME)
        for postID in postID_list:
            if count == readTimes:
                break
            headers["DS"] = generateDS()
            res = await client.get(URL_READ.format(postID), headers=headers)
            try:
                if "self_operation" not in res.json()["data"]["post"]:
                    raise ValueError
                count += 1
            except KeyError and ValueError:
                logger.error(conf.LOG_HEAD + "米游币任务 - 阅读: 服务器没有正确返回")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
                if error_times != conf.MAX_RETRY_TIMES:
                    continue
                else:
                    return False
            except:
                logger.error(conf.LOG_HEAD + "米游币任务 - 阅读: 网络请求失败")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
                if error_times != conf.MAX_RETRY_TIMES:
                    continue
                else:
                    return False
        postID_list = await get_posts(game)
        if postID_list is None:
            return False

    count = 0
    error_times = 0
    while count < likeTimes:
        await asyncio.sleep(conf.SLEEP_TIME)
        for postID in postID_list:
            if count == likeTimes:
                break
            headers["DS"] = generateDS()
            res = await client.post(URL_LIKE, headers=headers, json={'is_cancel': False,  'post_id': postID})
            try:
                if res.json()["data"] != "OK":
                    raise ValueError
                count += 1
            except KeyError and ValueError:
                logger.error(conf.LOG_HEAD + "米游币任务 - 点赞: 服务器没有正确返回")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
                if error_times != conf.MAX_RETRY_TIMES:
                    continue
                else:
                    return False
            except:
                logger.error(conf.LOG_HEAD + "米游币任务 - 点赞: 网络请求失败")
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                error_times += 1
                if error_times != conf.MAX_RETRY_TIMES:
                    continue
                else:
                    return False
        postID_list = await get_posts(game)
        if postID_list is None:
            return False

    error_times = 0
    while error_times <= conf.MAX_RETRY_TIMES:
        res = await client.post(URL_SHARE.format(postID_list[0]), headers=headers)
        try:
            if res.json()["data"] != "OK":
                raise ValueError
            count += 1
        except KeyError and ValueError:
            logger.error(conf.LOG_HEAD + "米游币任务 - 分享: 服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            error_times += 1
            if error_times != conf.MAX_RETRY_TIMES:
                continue
            else:
                return False
        except:
            logger.error(conf.LOG_HEAD + "米游币任务 - 分享: 网络请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            error_times += 1
            if error_times != conf.MAX_RETRY_TIMES:
                continue
            else:
                return False

    return mybNum
'''
