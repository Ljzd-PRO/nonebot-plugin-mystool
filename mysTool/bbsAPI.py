import httpx
from .config import mysTool_config as conf
from .data import UserAccount
from .utils import *

URL_ACTION_TICKET = "https://api-takumi.mihoyo.com/auth/api/getActionTicketBySToken?action_type=game_role&stoken={stoken}&uid={bbs_uid}"
URL_GAME_RECORD = "https://api-takumi-record.mihoyo.com/game_record/card/wapi/getGameRecordCard?uid={}"
HEADERS_ACTION_TICKET = {
    "Host": "api-takumi.mihoyo.com",
    "x-rpc-device_model": conf.device.X_RPC_DEVICE_MODEL_MOBILE,
    "User-Agent": conf.device.USER_AGENT_OTHER,
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
HEADERS_GAME_RECORD = {
    "Host": "api-takumi-record.mihoyo.com",
    "Origin": "https://webstatic.mihoyo.com",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": conf.device.USER_AGENT_MOBILE,
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Referer": "https://webstatic.mihoyo.com/",
    "Accept-Encoding": "gzip, deflate, br"
}


class GameRecord:
    def __init__(self, gameRecord_dict: dict) -> None:
        self.gameRecord_dict = gameRecord_dict

    @property
    def regionName(self) -> str:
        return self.gameRecord_dict["region_name"]

    @property
    def gameID(self) -> str:
        return self.gameRecord_dict["game_id"]

    @property
    def level(self) -> str:
        return self.gameRecord_dict["level"]

    @property
    def region(self) -> str:
        return self.gameRecord_dict["region"]

    @property
    def uid(self) -> str:
        return self.gameRecord_dict["game_role_id"]

    @property
    def nickname(self) -> str:
        return self.gameRecord_dict["nickname"]


async def get_action_ticket(account: UserAccount) -> str:
    headers = HEADERS_ACTION_TICKET.copy()
    headers["DS"] = generateDS()
    async with httpx.AsyncClient() as client:
        res = await client.get(URL_ACTION_TICKET, headers=headers, cookies=account.cookie)
    return res["data"]["ticket"]


async def get_game_record(account: UserAccount) -> list[GameRecord]:
    record_list = []
    async with httpx.AsyncClient() as client:
        res = await client.get(URL_GAME_RECORD.format(account.bbsUID), headers=HEADERS_GAME_RECORD, cookies=account.cookie)
    for record in res.json()["data"]["list"]:
        record_list.append(GameRecord(record))
