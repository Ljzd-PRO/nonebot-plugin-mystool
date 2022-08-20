"""
### 米游币兑换相关
"""
import asyncio
import datetime
import io
import time
import traceback
from typing import List, Literal, Tuple, Union

import httpx
from nonebot import get_bot, get_driver, on_command
from nonebot.adapters.onebot.v11 import (Bot, MessageEvent, MessageSegment,
                                         PrivateMessageEvent)
from nonebot.adapters.onebot.v11.message import Message
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, CommandArg, T_State
from nonebot_plugin_apscheduler import scheduler
from PIL import Image, ImageDraw, ImageFont

from .bbsAPI import get_game_record
from .config import img_config as img_conf
from .config import mysTool_config as conf
from .data import UserAccount, UserData
from .utils import generateDeviceID

URL_GOOD_LIST = "https://api-takumi.mihoyo.com/mall/v1/web/goods/list?app_id=1&point_sn=myb&page_size=20&page={page}&game={game}"
URL_CHECK_GOOD = "https://api-takumi.mihoyo.com/mall/v1/web/goods/detail?app_id=1&point_sn=myb&goods_id={}"
URL_EXCHANGE = "https://api-takumi.mihoyo.com/mall/v1/web/goods/exchange"
HEADERS_GOOD_LIST = {
    "Host":
        "api-takumi.mihoyo.com",
    "Accept":
        "application/json, text/plain, */*",
    "Origin":
        "https://user.mihoyo.com",
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
HEADERS_EXCHANGE = {
    "Accept":
    "application/json, text/plain, */*",
    "Accept-Encoding":
    "gzip, deflate, br",
    "Accept-Language":
    "zh-CN,zh-Hans;q=0.9",
    "Connection":
    "keep-alive",
    "Content-Type":
    "application/json;charset=utf-8",
    "Host":
    "api-takumi.mihoyo.com",
    "User-Agent":
    conf.device.USER_AGENT_MOBILE,
    "x-rpc-app_version":
    conf.device.X_RPC_APP_VERSION,
    "x-rpc-channel":
    "appstore",
    "x-rpc-client_type":
    "1",
    "x-rpc-device_id": None,
    "x-rpc-device_model":
    conf.device.X_RPC_DEVICE_MODEL_MOBILE,
    "x-rpc-device_name":
    conf.device.X_RPC_DEVICE_NAME_MOBILE,
    "x-rpc-sys_version":
    conf.device.X_RPC_SYS_VERSION
}


class Good:
    """
    商品数据
    """

    def __init__(self, good_dict: dict) -> None:
        self.good_dict = good_dict
        try:
            for func in dir(Good):
                if func.startswith("__") and func == "time":
                    continue
                getattr(self, func)
        except KeyError:
            logger.error(conf.LOG_HEAD + "米游币商品数据 - 初始化对象: dict数据不正确")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())

    @property
    def name(self) -> str:
        """
        商品名称
        """
        return self.good_dict["goods_name"]

    @property
    def goodID(self) -> str:
        """
        商品ID(Good_ID)
        """
        return self.good_dict["goods_id"]

    @property
    def price(self) -> int:
        """
        商品价格
        """
        return self.good_dict["price"]

    @property
    def time(self) -> str:
        """
        兑换时间
        """
        # "next_time" 为 0 表示任何时间均可兑换或兑换已结束
        # "type" 为 1 时商品只有在指定时间开放兑换；为 0 时商品任何时间均可兑换
        if self.good_dict["type"] != 1 and self.good_dict["next_time"] == 0:
            return None
        else:
            return time.strftime("%Y-%m-%d %H:%M:%S",
                                 time.localtime(self.good_dict["next_time"]))

    @property
    def num(self) -> int:
        """
        库存
        """
        if self.good_dict["type"] != 1 and self.good_dict["next_num"] == 0:
            return None
        else:
            return self.good_dict["next_num"]

    @property
    def limit(self) -> Tuple[str, str, Literal["forever", "month"]]:
        """
        限购，返回元组 (已经兑换次数, 最多可兑换次数, 限购类型)
        """
        return (self.good_dict["account_exchange_num"],
                self.good_dict["account_cycle_limit"], self.good_dict["account_cycle_type"])

    @property
    def icon(self) -> str:
        """
        商品图片链接
        """
        return self.good_dict["icon"]

    @property
    def isVisual(self) -> bool:
        """
        是否为虚拟商品
        """
        if self.good_dict["type"] == 2:
            return True
        else:
            return False


async def get_good_detail(goodID: str):
    try:
        async with httpx.AsyncClient() as client:
            res: httpx.Response = await client.get(URL_CHECK_GOOD.format(goodID))
        return Good(res.json()["data"])
    except KeyError and ValueError:
        logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取开始时间: 服务器没有正确返回")
        logger.debug("{0} 网络请求返回: {1}".format(conf.LOG_HEAD, res.text))
        logger.debug(conf.LOG_HEAD + traceback.format_exc())
    except:
        logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取开始时间: 网络请求失败")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())


async def get_start_time(goodID: str) -> Union[int, None]:
    try:
        async with httpx.AsyncClient() as client:
            res: httpx.Response = await client.get(URL_CHECK_GOOD.format(goodID))
        return int(res.json()["data"]["sale_start_time"])
    except KeyError and ValueError:
        logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取开始时间: 服务器没有正确返回")
        logger.debug("{0} 网络请求返回: {1}".format(conf.LOG_HEAD, res.text))
        logger.debug(conf.LOG_HEAD + traceback.format_exc())
    except:
        logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取开始时间: 网络请求失败")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())


async def get_good_list(game: Literal["bh3", "ys", "bh2", "wd", "bbs"]) -> Union[List[Good], None]:
    if game == "bh3":
        game = "bh3"
    elif game == "ys":
        game = "hk4e"
    elif game == "bh2":
        game = "bh2"
    elif game == "wd":
        game = "nxx"
    elif game == "bbs":
        game = "bbs"

    error_times = 0
    good_list = []
    page = 1
    res = None

    while error_times < conf.MAX_RETRY_TIMES:
        try:
            async with httpx.AsyncClient() as client:
                res: httpx.Response = await client.get(URL_GOOD_LIST.format(page=page,
                                                                            game=game), headers=HEADERS_GOOD_LIST, timeout=conf.TIME_OUT)
            goods = res.json()["data"]["list"]
            # 判断是否已经读完所有商品
            if goods == []:
                break
            else:
                good_list += goods
            page += 1
        except KeyError:
            logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取商品列表: 服务器没有正确返回")
            logger.debug("{0} 网络请求返回: {1}".format(conf.LOG_HEAD, res.text))
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            error_times += 1
        except:
            logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取商品列表: 网络请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            error_times += 1

    if not isinstance(res, list):
        return None

    result = []

    for good in good_list:
        # "next_time" 为 0 表示任何时间均可兑换或兑换已结束
        # "type" 为 1 时商品只有在指定时间开放兑换；为 0 时商品任何时间均可兑换
        if good["next_time"] == 0 and good["type"] == 1 or good["unlimit"] == False and good["next_num"] == 0:
            continue
        else:
            result.append(Good(good))

    return result


class Exchange:
    """
    米游币商品兑换相关(需先初始化对象)
    `result`属性为 `-1`: 商品为游戏内物品，由于未配置stoken，放弃兑换\n
    `result`属性为 `-2`: 商品为游戏内物品，由于stoken为\"v2\"类型，且未配置mid，放弃兑换\n
    `result`属性为 `-3`: 暂不支持商品所属的游戏\n
    `result`属性为 `-4`: 获取商品的信息时，服务器没有正确返回
    """
    async def __init__(self, account: UserAccount, goodID: str, gameUID: str) -> None:
        self.result = None
        self.goodID = goodID
        self.account = account
        self.content = {
            "app_id": 1,
            "point_sn": "myb",
            "goods_id": goodID,
            "exchange_num": 1,
            "address_id": account.address.addressID
        }
        logger.info(conf.LOG_HEAD +
                    "米游币商品兑换 - 初始化兑换任务: 开始获取商品 {} 的信息".format(goodID))
        try:
            async with httpx.AsyncClient() as client:
                res: httpx.Response = await client.get(
                    URL_CHECK_GOOD.format(goodID), timeout=conf.TIME_OUT)
            goodInfo = res.json()["data"]
            if goodInfo["type"] == 2:
                if "stoken" not in account.cookie:
                    logger.error(
                        conf.LOG_HEAD + "米游币商品兑换 - 初始化兑换任务: 商品 {} 为游戏内物品，由于未配置stoken，放弃兑换".format(goodID))
                    self.result = -1
                    return
                if account.cookie["stoken"].find("v2__") == 0 and "mid" not in account.cookie:
                    logger.error(
                        conf.LOG_HEAD + "米游币商品兑换 - 初始化兑换任务: 商品 {} 为游戏内物品，由于stoken为\"v2\"类型，且未配置mid，放弃兑换".format(goodID))
                    self.result = -2
                    return
            # 若商品非游戏内物品，则直接返回，不进行下面的操作
            else:
                return

            if goodInfo["game"] not in ("bh3", "hk4e", "bh2", "nxx"):
                logger.warning(
                    conf.LOG_HEAD + "米游币商品兑换 - 初始化兑换任务: 暂不支持商品 {} 所属的游戏".format(goodID))
                self.result = -3
                return

            record_list = await get_game_record(account)
            for record in record_list:
                if record.uid == gameUID:
                    self.content.setdefault("uid", record.uid)
                    # 例: cn_gf01
                    self.content.setdefault("region", record.region)
                    # 例: hk4e_cn
                    self.content.setdefault("game_biz", goodInfo["game_biz"])
                    break
        except KeyError:
            logger.error(
                conf.LOG_HEAD + "米游币商品兑换 - 初始化兑换任务: 获取商品 {} 的信息时，服务器没有正确返回".format(goodID))
            logger.debug("{0} 网络请求返回: {1}".format(conf.LOG_HEAD, res.text))
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            self.result = -4

    async def start(self) -> Union[Tuple[bool, dict], None]:
        """
        执行兑换操作
        返回元组 (是否成功, 服务器返回数据)\n
        若服务器没有正确返回，函数返回 `None`
        """
        if self.result is not None and self.result < 0:
            logger.error(conf.LOG_HEAD +
                         "商品：{} 未初始化完成，放弃兑换".format(self.goodID))
            return None
        else:
            headers = HEADERS_EXCHANGE
            headers["x-rpc-device_id"] = self.account.deviceID
            try:
                async with httpx.AsyncClient() as client:
                    res: httpx.Response = await client.post(
                        URL_EXCHANGE, headers=headers, cookies=self.account.cookie, timeout=conf.TIME_OUT)
                if res.json()["message"] == "OK":
                    logger.info(
                        conf.LOG_HEAD + "米游币商品兑换 - 执行兑换: 商品 {} 兑换成功！可以自行确认。".format(self.goodID))
                    return (True, res.json())
                else:
                    logger.info(
                        conf.LOG_HEAD + "米游币商品兑换 - 执行兑换: 商品 {} 兑换失败，可以自行确认。".format(self.goodID))
                    return (False, res.json())
            except KeyError:
                logger.error(
                    conf.LOG_HEAD + "米游币商品兑换 - 执行兑换: 商品 {} 服务器没有正确返回".format(self.goodID))
                logger.debug("{0} 网络请求返回: {1}".format(conf.LOG_HEAD, res.text))
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                return None


async def game_list_to_image(good_list: List[Good]):
    font = ImageFont.truetype(
        str(conf.goodListImage.FONT_PATH), conf.goodListImage.FONT_SIZE, encoding=conf.ENCODING)

    size_y = 0
    '''起始粘贴位置 高'''
    position: List[tuple] = []
    '''预览图粘贴的位置'''
    imgs: List[Image.Image] = []
    '''商品预览图'''

    for good in good_list:
        async with httpx.AsyncClient() as client:
            icon: httpx.Response = await client.get(good.icon, timeout=conf.TIME_OUT)
        img = Image.open(io.BytesIO(icon.content))
        # 调整预览图大小
        img = img.resize(conf.goodListImage.ICON_SIZE)
        # 记录预览图粘贴位置
        position.append((0, size_y))
        # 调整下一个粘贴的位置
        size_y += conf.goodListImage.ICON_SIZE[1] + \
            conf.goodListImage.PADDING_ICON
        imgs.append(img)

    preview = Image.new(
        'RGB', (conf.goodListImage.WIDTH, size_y), (255, 255, 255))

    i = 0
    for img in imgs:
        preview.paste(img, position[i])
        i += 1

    draw_y = conf.goodListImage.PADDING_TEXT_AND_ICON_Y
    '''写入文字的起始位置 高'''
    for good in good_list:
        draw = ImageDraw.Draw(preview)
        # 根据预览图高度来确定写入文字的位置，并调整空间
        if good.time is None:
            start_time = "不限"
        else:
            start_time = good.time
        draw.text((conf.goodListImage.ICON_SIZE[0] + conf.goodListImage.PADDING_TEXT_AND_ICON_X, draw_y),
                  "{0}\n商品ID: {1}\n兑换时间: {2}\n价格: {3} 米游币".format(good.name, good.goodID, start_time, good.price), (0, 0, 0), font)
        draw_y += (conf.goodListImage.ICON_SIZE[1] +
                   conf.goodListImage.PADDING_ICON)

    # 导出
    image_bytes = io.BytesIO()
    preview.save(image_bytes, format="JPEG")
    return image_bytes.getvalue()

driver = get_driver()

__cs = ''
if conf.USE_COMMAND_START:
    __cs = conf.COMMAND_START
command = list(get_driver().config.command_start)[0] + __cs

myb_exchange_plan = on_command(
    __cs+'myb_exchange_plan', aliases={__cs+'myb_exchange', __cs+'米游币兑换', __cs+'米游币兑换计划', __cs+'兑换计划', __cs+'兑换'}, priority=4, block=True)
myb_exchange_plan.__help_name__ = "兑换"
myb_exchange_plan.__help_info__ = "跟随指引，配置米游币兑换计划，即可自动兑换米游社商品。在兑换商品前，请先调用商品列表命令查看您想兑换的商品的ID。换取实体商品前，必须要先配置地址id；兑换虚拟商品时，请跟随引导输入要兑换的账户的uid"
myb_exchange_plan.__help_msg__ = f"""\
    具体用法：\
    \n{command} + [商品id] -> 新增兑换计划\
    \n{command} - [商品id] -> 删除兑换计划\
    \n{command} 商品列表 -> 查看所有米游社商品
""".strip()


@myb_exchange_plan.handle()
async def handle_first_receive(event: PrivateMessageEvent, matcher: Matcher, state: T_State, args: Message = ArgPlainText()):
    if args:
        matcher.set_arg("content", args)
    qq_account = int(event.user_id)
    user_account = UserData.read_account_all(qq_account)
    state['qq_account'] = qq_account
    state['user_account'] = user_account
    if not user_account:
        await myb_exchange_plan.finish("你没有配置cookie，请先配置cookie！")
    if len(user_account) == 1:
        matcher.set_arg('phone', user_account[0].phone)
    else:
        phones = [str(user_account[i].phone) for i in range(len(user_account))]
        await matcher.send(f"您有多个账号，您要配置以下哪个账号的兑换计划？\n{'，'.join(phones)}")
    if args:
        matcher.set_arg("content", args)


@myb_exchange_plan.got('phone')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, phone: Message = ArgPlainText('phone')):
    if phone == '退出':
        await matcher.finish('已成功退出')
    user_account = state['user_account']
    qq = event.user_id
    phones = [str(user_account[i].phone) for i in range(len(user_account))]
    if phone in phones:
        account = UserData.read_account(qq, int(phone))
    else:
        myb_exchange_plan.reject('您输入的账号不在以上账号内，请重新输入')
    state['phone'] = int(phone)
    state['account'] = account
    if not matcher.get_arg('arg'):
        state['account'] = account
        goodid_list = account.exchange
        msg = ''
        if goodid_list:
            for goodid in goodid_list:
                good = get_good_detail(goodid[0])
                msg += f'{good.name} {good.goodID} {good.price} {good.time}\n'
            msg += '\n'
        else:
            msg = '您还没有兑换计划哦\n\n'
        await matcher.finish(msg+matcher.__help_msg__)


@myb_exchange_plan.got('arg')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, bot: Bot, content: Message = ArgPlainText('arg')):
    account = state['account']
    arg = content.strip()
    phone = state['phone']
    good_list = get_good_list('bh3') + get_good_list('ys') + \
        get_good_list('bh2') + get_good_list('wd') + get_good_list('bbs')
    Flag = True
    for good in good_list:
        if good.goodID == arg[1]:
            Flag = False
            break
    if Flag:
        await matcher.finish('您输入的商品id不在可兑换的商品列表内，程序已退出')
    if arg[0] == '+':
        if good.time:
            if good.isVisual:
                state['good'] = good
                await matcher.send("您兑换的是虚拟物品哦，请输入对应账户的uid")
            else:
                matcher.get_arg('uid', None)
        else:
            await matcher.finish(f'该商品暂时不可以兑换，请重新设置')
    elif arg[0] == '-':
        if account.exchange:
            for exchange_good in account.exchange:
                if exchange_good[0] == good.goodID:
                    account.exchange.remove(exchange_good)
                    UserData.set_account(account, event.user_id, phone)
                    scheduler.remove_job(job_id=account.phone+good.goodID)
                    await matcher.finish('兑换计划删除成功')
            await matcher.finish(f"您没有设置商品ID为{good.goodID}的兑换哦")
        else:
            await matcher.finish("您还没有配置兑换计划哦")
    else:
        matcher.finish('您的输入有误，请重新输入')


@myb_exchange_plan.got('uid')
async def _(event: PrivateMessageEvent, matcher: Matcher, state: T_State, bot: Bot, uid: Message = ArgPlainText('uid')):
    account = state['account']
    good = state['good']
    phone = state['phone']
    qq = event.user_id
    account.exchange.append((good.goodID, uid))
    UserData.set_account(account, event.user_id, phone)
    exchange_plan = Exchange(account, good.goodID)
    if exchange_plan.result == -1:
        await matcher.finish("商品 {} 为游戏内物品，由于未配置stoken，放弃兑换".format(good.goodID))
    elif exchange_plan.result == -2:
        await matcher.finish("商品 {} 为游戏内物品，由于stoken为\"v2\"类型，且未配置mid，放弃兑换".format(good.goodID))
    elif exchange_plan.result == -3:
        await matcher.finish("暂不支持商品 {} 所属的游戏".format(good.goodID))
    elif exchange_plan.result == -4:
        await matcher.finish("获取商品 {} 的信息时，服务器没有正确返回".format(good.goodID))
    else:
        scheduler.add_job(id=account.phone+good.goodID, replace_existing=True, trigger='date', func=exchange,
                          args=(exchange_plan, qq), next_run_time=datetime.datetime.strptime(good.time, "%Y-%m-%d %H:%M:%S"))
    await matcher.finish(f'设置兑换计划成功！将于{good.time}开始兑换，兑换结果会实时通知您')


async def exchange(exchange_plan: Exchange, qq: str):
    bot = get_bot()
    for i in range(3):
        results = []
        flag = False
        results.append(exchange_plan.start())
        await asyncio.sleep(0.2)
    for result in results:
        if result[0]:
            flag = True
            break
    if flag:
        await bot.send_private_msg(user_id=qq, message=f"商品{exchange_plan.goodID}兑换成功，可前往米游社查看")
    else:
        await bot.send_private_msg(user_id=qq, message=f"商品{exchange_plan.goodID}兑换失败\n{result[1]}")


get_good_image = on_command(
    __cs+'商品列表', aliases={__cs+'商品图片', __cs+'米游社商品列表', __cs+'米游币商品图片'}, priority=4, block=True)
get_good_image.__help_name__ = "商品列表"
get_good_image.__help_info__ = "获取当日米游社商品信息，目前共有五个分类可选，分别为（崩坏3，原神，崩坏2，未定事件簿，大别野）。请记住您要兑换的商品的ID，以方便下一步兑换"


@get_good_image.handle()
async def _(event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    if arg:
        matcher.set_arg("content", arg)


@get_good_image.got("content", prompt='请发送您要查看的商品类别:\n- 崩坏3\n- 原神\n- 崩坏2\n- 未定事件簿\n- 大别野\n—— 发送“退出”以结束')
async def _(event: MessageEvent, matcher: Matcher, arg: Message = ArgPlainText('content')):
    if arg in ['原神', 'ys']:
        arg = ('ys', '原神')
    elif arg in ['崩坏3', '崩坏三', '崩3', '崩三', '崩崩崩', '蹦蹦蹦', 'bh3']:
        arg = ('bh3', '崩坏3')
    elif arg in ['崩坏2', '崩坏二', '崩2', '崩二', '崩崩', '蹦蹦', 'bh2']:
        arg = ('bh2', '崩坏2')
    elif arg in ['未定', '未定事件簿', 'wd']:
        arg = ('wd', '未定事件簿')
    elif arg in ['大别野', '米游社']:
        arg = ('bbs', '米游社')
    else:
        await get_good_image.finish('您的输入有误，请重新输入')
    good_list = await get_good_list()
    if good_list:
        img_path = time.strftime(
            f'file:///{img_conf.SAVE_PATH}/%m-%d-{arg[0]}.jpg', time.localtime())
        await get_good_image.finish(MessageSegment.image(img_path))
    else:
        await get_good_image.finish(f"{arg[1]}部分目前没有可兑换商品哦~")


@driver.on_startup
def load_exchange_data():
    all_accounts = UserData.read_all()
    for qq in all_accounts.keys():
        accounts = UserData.read_account_all(qq)
        for account in accounts:
            exchange_list = account.exchange
            for exchange_good in exchange_list:
                good_detail = get_good_detail(exchange_good[0])
                exchange_plan = Exchange(account, exchange_good[0])
                scheduler.add_job(id=account.phone+exchange_good[0], replace_existing=True, trigger='date', func=exchange, args=(
                    exchange_plan, qq), next_run_time=datetime.datetime.strptime(good_detail.time, "%Y-%m-%d %H:%M:%S"))
