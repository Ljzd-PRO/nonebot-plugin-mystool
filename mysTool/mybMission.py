import httpx
from .config import mysTool_config as conf
from .data import UserAccount
from .utils import generateDS
from typing import Literal
from asyncio import sleep

URL_SIGN = "https://api-takumi.mihoyo.com/apihub/sapi/signIn"
URL_GET_POST = "https://api-takumi.mihoyo.com/post/api/getForumPostList?forum_id={}&is_good=false&is_hot=false&page_size=20&sort=create"
URL_READ = "https://api-takumi.mihoyo.com/post/api/getPostFull?post_id={}"
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

    async def sign(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"]):
        headers = HEADERS.copy()
        headers.setdefault("DS", generateDS())
        res = await self.client.post(URL_SIGN, headers=headers, json={"gids": GAME_ID[game]["gids"]})
        ...

    async def read(self, game: Literal["bh3", "ys", "bh2", "wd", "xq"], times: int = 3):
        headers = HEADERS.copy()
        headers.setdefault("DS", generateDS())
        res_getPost = await self.client.get(URL_GET_POST.format(GAME_ID[game]["fid"]), headers=headers)
        count = 0
        while count < times:
            postID = res_getPost['data']['list'][count]['post']['post_id']
            await sleep(conf.SLEEP_TIME)
            headers["DS"] = generateDS()
            res = await ...

    async def __del__(self):
        await self.client.aclose()
