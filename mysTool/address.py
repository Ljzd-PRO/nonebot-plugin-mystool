import httpx
from .config import mysTool_config as conf
from .utils import *
from .data import UserAccount
from typing import Union

HEADERS = {
    "Host": "api-takumi.mihoyo.com",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://user.mihoyo.com",
    "Connection": "keep-alive",
    "x-rpc-device_id": None,
    "x-rpc-client_type": "5",
    "User-Agent": conf.device.USER_AGENT_MOBILE,
    "Referer": "https://user.mihoyo.com/",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

URL = "https://api-takumi.mihoyo.com/account/address/list?t={}"

class Address:
    def __init__(self, adress_dict:dict) -> None:
        self.address_dict = adress_dict

    @property
    def province(self) -> str:
        return self.address_dict["province_name"]

    @property
    def city(self) -> str:
        return self.address_dict["city_name"]

    @property
    def county(self) -> int:
        return self.address_dict["county_name"]

    @property
    def detail(self) -> str:
        return self.address_dict["addr_ext"]

    @property
    def phone(self) -> str:
        return self.address_dict["connect_areacode"] + " " + self.address_dict["connect_mobile"]

    @property
    def name(self) -> int:
        return self.address_dict["connect_name"]

    @property
    def addressID(self) -> int:
        return self.address_dict["id"]


async def get(account: UserAccount) -> Union[list[Address], None]:
    address_list = []
    headers = HEADERS.copy()
    headers["x-rpc-device_id"] = account.deviceID
    res: httpx.Response = await httpx.get(URL.format(
        time_now=round(NtpTime.time() * 1000)), headers=headers, cookies=account.cookie)
    try:
        for address in res.json()["data"]["list"]:
            address_list.append(Address(address))
    except KeyError:
        return None
    return address_list
