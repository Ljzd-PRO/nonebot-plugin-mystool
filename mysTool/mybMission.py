from email import header
import httpx
from .config import mysTool_config as conf
from .data import UserAccount
from .utils import generateDS
from typing import Literal, Union
from asyncio import sleep

URL_SIGN = "https://bbs-api.mihoyo.com/apihub/app/api/signIn"
URL_GET_POST = "https://bbs-api.mihoyo.com/apihub/app/api/getForumPostList?forum_id={}&is_good=false&is_hot=false&page_size=20&sort=create"
URL_READ = "https://bbs-api.mihoyo.com/apihub/app/api/getPostFull?post_id={}"
URL_LIKE = "https://api-takumi.mihoyo.com/apihub/sapi/upvotePost"
HEADERS = {
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-cn",
    "Connection": "keep-alive",
    "Host": "api-takumi.mihoyo.com",
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
    def __init__(self, account: UserAccount) -> None:
        self.account = account
        self.cookie = {"stuid": account.bbsUID,
                       "stoken": account.cookie["stoken"]}
        self.client = httpx.AsyncClient(cookies=self.cookie)
        self.mybNum: int = 0

    async def sign(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]):
        headers = HEADERS.copy()
        headers.setdefault("DS", generateDS())
        res = await self.client.post(URL_SIGN, headers=headers, json={"gids": GAME_ID[game]["gids"]})
        try:
            self.mybNum = res.json()["data"]["points"]
            return True
        except KeyError:
            return False

    async def get_posts(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]) -> Union[list[str], None]:
        headers = HEADERS.copy()
        headers.setdefault("DS", generateDS())
        res = await self.client.get(URL_GET_POST.format(GAME_ID[game]["fid"]), headers=headers)
        postID_list = []
        try:
            data = res.json()["data"]["list"]
            for post in data:
                if post["self_operation"]["attitude"] == 0:
                    postID_list.append(post['post']['post_id'])
        except KeyError:
            return None
        return postID_list

    async def read(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"], readTimes: int = 3):
        headers = HEADERS.copy()

        count = 0
        postID_list = await self.get_posts(game)
        while count < readTimes:
            await sleep(conf.SLEEP_TIME)
            headers["DS"] = generateDS()
            for postID in postID_list:
                if count == readTimes:
                    break
                res = await self.client.get(URL_READ.format(postID), headers=headers)
                try:
                    "self_operation" in res.json()["data"]["post"]
                    count += 1
                except KeyError:
                    ...
            postID_list = await self.get_posts(game)

        return True

    async def like(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"], likeTimes: int = 10):
        headers = HEADERS.copy()

        count = 0
        postID_list = await self.get_posts(game)
        while count < likeTimes:
            await sleep(conf.SLEEP_TIME)
            headers["DS"] = generateDS()
            for postID in postID_list:
                if count == likeTimes:
                    break
                res = await self.client.post(URL_LIKE, headers=headers, json={'is_cancel': False,  'post_id': postID})
                try:
                    res.json()["data"] == "OK"
                    count += 1
                except KeyError:
                    ...
            postID_list = await self.get_posts(game)

        return True

    async def share(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]):
        ...

    async def __del__(self):
        await self.client.aclose()
