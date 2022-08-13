"""
### 米游社收货地址相关
"""
import httpx
from .config import mysTool_config as conf
from .utils import *
from typing import Union
from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import T_State, ArgPlainText
from .data import UserAccount, UserData, Address

__cs = ''
if conf.USE_COMMAND_START:
    __cs = conf.COMMAND_START

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


async def get(account: UserAccount) -> Union[list[Address], None]:
    """
    获取用户的地址数据
    """
    address_list = []
    headers = HEADERS.copy()
    headers["x-rpc-device_id"] = account.deviceID
    async with httpx.AsyncClient() as client:
        res = await client.get(URL.format(
            time_now=round(NtpTime.time() * 1000)), headers=headers, cookies=account.cookie)
    try:
        for address in res.json()["data"]["list"]:
            address_list.append(Address(address))
    except KeyError:
        return None
    return address_list


get_address = on_command(
    __cs+'address', aliases={__cs+'地址填写', __cs+'地址', __cs+'地址获取'}, priority=4, block=True)

get_address.__help_name__ = '地址填写'
get_address.__help_info__ = '跟随指引，获取地址id，米游币兑换实体奖品必须。在获取地址id前，必须先在米游社配置好至少一个地址。'


@get_address.handle()
async def handle_first_receive(event: PrivateMessageEvent, state: T_State):
    qq_account = int(event.user_id)
    user_account = UserData.read_account_all(qq_account)
    state['qq_account'] = qq_account
    if not user_account == 0:
        await get_address.finish("你没有配置cookie，请先配置cookie！")
    else:
        await get_address.send("请跟随指引配合地址ID，请确保米游社内已经填写了至少一个地址，过程中随时输入退出即可退出")
    if len(user_account) == 1:
        account = user_account[0]
    else:
        phone = get_address.got('您有多个账号，您要配置一下哪个账号的地址ID？')
        phones = [user_account[i].phone for i in len(user_account)]
        await get_address.send(','.join(phones))
        if phone in phones:
            account = UserData.read_account(qq_account, phone)
        else:
            get_address.reject('您输入的账号不在以上账号内，请重新输入')
    state['account'] = account

    try:
        state['address_list']: list[Address] = await get(account)
    except:
        await get_address.finish("请求失败")
    if state['address_list']:
        await get_address.send("以下为查询结果：")
        for address in state['address_list']:
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
            await get_address.send(address_string)
    else:
        await get_address.finish("您的该账号没有配置地址，请先前往米游社配置地址！")


@get_address.got('address_id', prompt='请输入你要选择的地址ID(Address_ID)')
async def _(event: PrivateMessageEvent, state: T_State, address_id: str = ArgPlainText('address_id')):
    if address_id == "退出":
        get_address.finish("已成功退出")
    result_address = list(
        filter(lambda address: address.addressID == address_id, state['address_list']))
    if result_address:
        account: UserAccount = state["account"]
        account.address = result_address[0]
        UserData.set_account(account, state['qq_account'], account.phone)
        get_address.finish("地址写入完成")
    else:
        get_address.reject("您输入的地址id与上文的不匹配，请重新输入")


async def get_address__(account: UserAccount, state: T_State):
    state['address_id'] = []

    try:
        address_list: list[Address] = await get(account)
    except:
        await get_address.finish("请求失败")
    if address_list:
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
