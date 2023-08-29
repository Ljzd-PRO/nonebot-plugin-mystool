# main code from lulu: https://github.com/lulu666lulu
import contextlib
import httpx
import json
import random
import base64
from hashlib import md5
from io import BytesIO
from string import ascii_letters, digits

import qrcode
from typing import Optional, Union, List, Dict, Any, Tuple, Type
from pydantic import ValidationError, BaseModel
from nonebot import on_command, get_bot, get_app
from nonebot.matcher import Matcher
#from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent, GroupMessageEvent
from nonebot.adapters.onebot.v11 import (Bot, MessageSegment,
                                         PrivateMessageEvent, GroupMessageEvent, Message, MessageEvent)
from nonebot.adapters.console import (MessageEvent as ConsoleMessageEvent,
                                      Message as ConsoleMessage)
from nonebot.adapters.qqguild import (MessageEvent as GuildMessageEvent,
                                      Message as GuildMessage, Bot as GuildBot,
                                      MessageSegment as GuildMessageSegment,
                                      MessageCreateEvent as GuildMessageCreateEvent)
from nonebot.internal.adapter.bot import Bot
from nonebot_plugin_saa import Image, Text, MessageFactory
from nonebot_plugin_apscheduler import scheduler

from .simple_api import ApiResultHandler, HEADERS_QRCODE_API, get_ltoken_by_stoken
from .plugin_data import PluginDataManager, write_plugin_data
from .data_model import QrcodeLoginData
from .utils import logger, generate_ds, \
    get_async_retry, get_validate, ALL_MessageEvent
from .user_data import UserAccount, UserData, BBSCookies

_conf = PluginDataManager.plugin_data_obj

running_login_data = {}

class CheckLoginHandler(BaseModel):
    """
    登录状态检测的数据处理器
    """
    content: Dict[str, Any]
    """API返回的JSON对象序列化以后的Dict对象"""
    data: Optional[Dict[str, Any]]
    """API返回的数据体"""
    message: Optional[str]
    """API返回的消息内容"""
    retcode: Optional[int]
    """API返回的状态码"""
    

    def __init__(self, content: Dict[str, Any]):
        super().__init__(content=content)

        self.data = self.content.get("data")

        if self.data is None:
            self.data = {
                "stat": "ExpiredCode"
            }

        for key in ["retcode", "status"]:
            if not self.retcode:
                self.retcode = self.content.get(key)
                if self.retcode is None:
                    self.retcode = self.data.get(key) if self.data else None
                else:
                    break

        self.message: Optional[str] = None
        for key in ["message", "msg"]:
            if not self.message:
                self.message = self.content.get(key)
                if self.message is None:
                    self.message = self.data.get(key) if self.data else None
                else:
                    break

    @property
    def success(self):
        """
        是否成功
        """
        return self.data.get("stat", "False") == "Confirmed"

    @property
    def game_token(self):
        """
        游戏TOKEN
        """
        if self.success:
            return json.loads(self.data['payload']['raw'])
        return None

    @property
    def scanned(self):
        """
        是否扫描
        """
        return self.data.get("stat", "False") in ["Scanned", "Confirmed"]

    @property
    def expiredCode(self):
        """
        是否过期
        """
        return self.data.get("stat", "False") == "ExpiredCode"

    def __bool__(self):
        if self.success:
            return True
        else:
            return False
    
async def get_stoken(data: dict = None, retry: bool = True):
    if data is None:
        data = {}
    headers = HEADERS_QRCODE_API.copy()
    async for attempt in get_async_retry(retry):
        with attempt:
            headers['DS'] = generate_ds(data=data, salt=_conf.salt_config.SALT_PROD)
            async with httpx.AsyncClient() as client:
                res = await client.post('https://passport-api.mihoyo.com/account/ma-cn-session/app/getTokenByGameToken',headers=headers,json=data)
            api_result = ApiResultHandler(res.json())
            if api_result.retcode == 0:
                return api_result.data
            else:
                raise Exception("获取stoken失败")


def generate_qrcode(url):
    qr = qrcode.QRCode(version=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_L,
                       box_size=10,
                       border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    bio = BytesIO()
    img.save(bio)
    return bio.getvalue()
    return f'base64://{base64.b64encode(bio.getvalue()).decode()}'


async def create_login_data(retry: bool = True):
    async for attempt in get_async_retry(retry):
        with attempt:
            device_id = ''.join(random.choices((ascii_letters + digits), k=64))
            app_id = '4'
            data = {'app_id': app_id,
                    'device': device_id}
            async with httpx.AsyncClient() as client:
                res = await client.post('https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/fetch?',
                                            json=data)
            api_result = ApiResultHandler(res.json())
            if api_result.retcode == 0:
                url = res.json()['data']['url']
                ticket = url.split('ticket=')[1]
                return QrcodeLoginData(app_id=app_id,ticket=ticket,device=device_id,url=url)
            else:
                raise Exception("二维码生成失败")


async def check_login(login_data: QrcodeLoginData, retry: bool = True):
    data = {'app_id': login_data.app_id,
            'ticket': login_data.ticket,
            'device': login_data.device}
    async for attempt in get_async_retry(retry):
        with attempt:
            async with httpx.AsyncClient() as client:
                res = await client.post('https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/query?',
                                            json=data)
            return CheckLoginHandler(res.json())


async def get_cookie_token(game_token: dict, retry: bool = True):
    async for attempt in get_async_retry(retry):
        with attempt:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"https://api-takumi.mihoyo.com/auth/api/getCookieAccountInfoByGameToken?game_token={game_token['token']}&account_id={game_token['uid']}")
            api_result = ApiResultHandler(res.json())
            if api_result.retcode == 0:
                return api_result.data.get("cookie_token")
            else:
                raise Exception("获取cookie_token失败")


qrcode_bind = on_command('扫码登录', aliases={'扫码绑定', '扫码登陆', 'qrcode_bind'}, priority=1, block=True)
qrcode_bind.name = "扫码登录"
qrcode_bind.command = 'qrcode_bind'
qrcode_bind.usage = "通过米游社扫码的方式登录"

@qrcode_bind.handle()
async def _(event: ALL_MessageEvent):
    if str(event.get_user_id()) in running_login_data:
        await qrcode_bind.finish('你已经在绑定中了，请扫描上一次的二维码')
    login_data = await create_login_data()
    img_b64 = generate_qrcode(login_data.url)
    #img = GuildMessageSegment.file_image(img_b64)
    msg_builder = MessageFactory([
        Image(img_b64), Text(f'\n请在3分钟内使用米游社扫码并确认进行绑定。\n注意：1.扫码即代表你同意将Cookie信息授权给二维码发送者\n2.扫码时会提示登录原神，实际不会把你顶掉原神\n3.其他人请不要乱扫，否则会将你的账号绑到TA身上！')
    ])
    msg_event = await msg_builder.send(at_sender=True)
    running_login_data[event.get_user_id()] = {
        "login_data": login_data,
        "event": event,
        "msg_event": msg_event
    }


@scheduler.scheduled_job('cron', second='*/10', misfire_grace_time=10)
async def check_qrcode():
    with contextlib.suppress(RuntimeError):
        for user_id, data_dict in running_login_data.items():
            data = data_dict["login_data"]
            event: MessageEvent = data_dict["event"]
            msg_event: dict = data_dict["msg_event"]
            bot:Bot = get_bot()
            status_data = await check_login(data)
            logger.info(status_data)
            if status_data.expiredCode:
                send_msg = '绑定二维码已过期，请重新发送扫码绑定指令'
                running_login_data.pop(user_id)
                if isinstance(event, GuildMessageCreateEvent):
                    await bot.delete_message(channel_id=msg_event.sent_msg.channel_id, message_id=msg_event.sent_msg.id, hidetip=True)
                else:
                    await bot.delete_msg(message_id=msg_event.get("message_id"))
            elif status_data:
                game_token = status_data.game_token
                cookie_token = await get_cookie_token(game_token)
                stoken_data = await get_stoken(data={'account_id': int(game_token['uid']),
                                                    'game_token': game_token['token']})
                mys_id = stoken_data['user_info']['aid']
                mid = stoken_data['user_info']['mid']
                stoken = stoken_data['token']['token']
                cookies = BBSCookies.parse_obj({
                        "stuid": mys_id,
                        "ltuid": mys_id,
                        "account_id": mys_id,
                        "login_uid": mys_id,
                        "stoken_v2": stoken,
                        "cookie_token": cookie_token,
                        "mid": mid
                    })
                _conf.users.setdefault(user_id, UserData())
                user = _conf.users[user_id]
                account = user.accounts.get(cookies.bbs_uid)
                """当前的账户数据对象"""
                if not account or not account.cookies:
                    user.accounts.update({
                        cookies.bbs_uid: UserAccount(phone_number=14514, cookies=cookies)
                    })
                    account = user.accounts[cookies.bbs_uid]
                else:
                    account.cookies.update(cookies)
                write_plugin_data()
                # 4. 通过 stoken_v2 获取 ltoken
                login_status, cookies = await get_ltoken_by_stoken(account.cookies, account.device_id_ios)
                if login_status:
                    logger.info(f"用户 {user} 成功获取 ltoken: {cookies.ltoken}")
                    account.cookies.update(cookies)
                    write_plugin_data()
                    logger.info(f"{_conf.preference.log_head}米游社账户 {cookies.bbs_uid} 绑定成功")
                    running_login_data.pop(user_id)
                    await bot.send(event=event, message=f"🎉米游社账户 {cookies.bbs_uid} 绑定成功")
                    logger.info(msg_event)
                    if isinstance(event, GuildMessageCreateEvent):
                        await bot.delete_message(channel_id=msg_event.sent_msg.channel_id, message_id=msg_event.sent_msg.id, hidetip=True)
                    else:
                        await bot.delete_msg(message_id=msg_event.get("message_id"))
