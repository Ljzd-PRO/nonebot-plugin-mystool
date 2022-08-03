from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import T_State, ArgPlainText
import httpx
from .config import mysTool_config as conf
from .utils import *
from .data import UserData

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
    if len(user_account) == 0:
        await get_address.finish("你没有配置cookie，请先配置cookie！")
    elif len(user_account) == 1:
        cookie = user_account[0].cookie
    else:
        get_address.send('您有多个账号，您要配置一下哪个账号的地址ID？')
        ... # 发送账号
        cookie = user_account.cookie
    if cookie:
        await get_address.send('cookie已配置')
        get_address__(cookie)
    else:
        await get_address.finish('你没有配置cookie，请先配置cookie!')

@get_address.got('address_id',prompt='请输入你要选择的地址ID(Address_ID)')
async def _(event: PrivateMessageEvent, state: T_State, address_id: str = ArgPlainText('address_id')):
    if address_id == "退出":
        get_address.finish("已成功退出")
    if address_id in state['address_id']:
        state["address_id"] = address_id
        ... #写入address_id
        get_address.finish("地址写入完成")
    else:
        get_address.reject("您输入的地址id与上文的不匹配，请重新输入")

async def get_address__(cookie, state):
    state['address_id'] = []
    headers = {
        "Host":
            "api-takumi.mihoyo.com",
        "Accept":
            "application/json, text/plain, */*",
        "Origin":
            "https://user.mihoyo.com",
        "Cookie":
            cookie,
        "Connection":
            "keep-alive",
        "x-rpc-device_id": generateDeviceID(),
        "x-rpc-client_type":
            "5",
        "User-Agent":
            conf.device.USER_AGENT_MOBILE,
        "Referer":
            "https://user.mihoyo.com/",
        "Accept-Language":
            "zh-CN,zh-Hans;q=0.9",
        "Accept-Encoding":
            "gzip, deflate, br"
    }
    url = "https://api-takumi.mihoyo.com/account/address/list?t={time_now}".format(
        time_now=round(time.time() * 1000))
    retry_times = 0

    while True:
        try:
            address_list_req = httpx.get(url, headers=headers)
            address_list = address_list_req.json()["data"]["list"]
            break
        except:
            retry_times += 1
            await get_address.send("请求失败，正在重试({times})...".format(times=retry_times))
            if retry_times >= 3:
                await get_address.send("失败次数过多，请稍后再试")
            try:
                await get_address.finish("服务器返回: " + address_list_req.json())
            except:
                pass
    if address:
        await get_address.send("以下为查询结果：")
        for address in address_list:
            address_string = f"""\
            ----------
            省：{address["province_name"]}
            市：{address["city_name"]}
            区/县：{address["county_name"]}
            详细地址：{address["addr_ext"]}
            联系电话：{address["connect_areacode"] + " " +
                                    address["connect_mobile"]}
            联系人：{address["connect_name"]}
            地址ID(Address_ID)：{address["id"]}
            """
            state['address_id'].append(address["id"])
            await get_address.send(address_string)
    else:
        await get_address.finish("您的该账号没有配置地址，请先前往米游社配置地址！")