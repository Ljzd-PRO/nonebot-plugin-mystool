import httpx
from .config import mysTool_config as conf
from .utils import *
from typing import Union
from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import T_State, ArgPlainText
from .data import UserAccount, UserData

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


get_address = on_command('address', aliases={'地址填写', '地址', '地址获取'}, priority=4, block=True)

get_address.__help__ = {
    "usage":     "get_address",
    "introduce": "获取地址ID"
}

@get_address.handle()
async def handle_first_receive(event: PrivateMessageEvent, state: T_State):
    await get_address.send("请跟随指引配合地址ID，请确保米游社内已经填写了至少一个地址，过程中随时输入退出即可退出")
    qq_account = event.user_id
    user_account = UserData.read_account_all(qq_account)
    state['qq_account'] = qq_account
    if len(user_account) == 0:
        await get_address.finish("你没有配置cookie，请先配置cookie！")
    elif len(user_account) == 1:
        account = user_account[0]
    else:
        phone = get_address.got('您有多个账号，您要配置一下哪个账号的地址ID？')
        phones = [user_account[i].phone for i in len(user_account)]
        await get_address.send(','.join(phones))
        if phone in phones:
            account = UserData.read_account(qq_account, phone)
        else:
            get_address.reject('您输入的账号不在以上账号内，清授信输入')
    state['account'] = account
    get_address__(account, state)


@get_address.got('address_id',prompt='请输入你要选择的地址ID(Address_ID)')
async def _(event: PrivateMessageEvent, state: T_State, address_id: str = ArgPlainText('address_id')):
    if address_id == "退出":
        get_address.finish("已成功退出")
    if address_id in state['address_id']:
        state["address_id"] = address_id
        account = state["account"]
        account.addressID = address_id
        UserData.set_account(account, state['qq_account'], account.phone)
        get_address.finish("地址写入完成")
    else:
        get_address.reject("您输入的地址id与上文的不匹配，请重新输入")

async def get_address__(account: UserAccount, state: T_State):
    state['address_id'] = []

    try:
        address_list: list[Address] = get(account)
    except:
        await get_address.finish("请求失败")
    if not address_list:
        await get_address.send("以下为查询结果：")
        for address in address_list:
            address_string = f"""\
            ----------
            省：{address.province}
            市：{address.city}
            区/县：{address.county}
            详细地址：{address.detail}
            联系电话：{address.phone}
            联系人：{address.name}
            地址ID(Address_ID)：{address.addressID}
            """
            state['address_id'].append(address.addressID)
            await get_address.send(address_string)
    else:
        await get_address.finish("您的该账号没有配置地址，请先前往米游社配置地址！")