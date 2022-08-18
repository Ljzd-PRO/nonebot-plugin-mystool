"""
### 米游币兑换相关
"""
import httpx
import time
import traceback
from typing import Literal, Tuple, Union
from .config import mysTool_config as conf
from .utils import generateDeviceID
from nonebot.log import logger
from .data import UserAccount
from .bbsAPI import get_game_record
from PIL import Image, ImageFont, ImageDraw
import io

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


async def get_good_detail(goodID: str):
    try:
        async with httpx.AsyncClient() as client:
            res: httpx.Response = await client.get(URL_CHECK_GOOD.format(goodID))
        return Good(res.json()["data"])
    except KeyError and ValueError:
        logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取开始时间: 服务器没有正确返回")
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
        logger.debug(conf.LOG_HEAD + traceback.format_exc())
    except:
        logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取开始时间: 网络请求失败")
        logger.debug(conf.LOG_HEAD + traceback.format_exc())


async def get_good_list(game: Literal["bh3", "ys", "bh2", "wd", "bbs"]) -> Union[list[Good], None]:
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
    get_list = None

    while error_times < conf.MAX_RETRY_TIMES:
        try:
            async with httpx.AsyncClient() as client:
                get_list: httpx.Response = await client.get(URL_GOOD_LIST.format(page=page,
                                                                                 game=game), headers=HEADERS_GOOD_LIST, timeout=conf.TIME_OUT)
            get_list = get_list.json()["data"]["list"]
            # 判断是否已经读完所有商品
            if get_list == []:
                break
            else:
                good_list += get_list
            page += 1
        except KeyError:
            logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取商品列表: 服务器没有正确返回")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            error_times += 1
        except:
            logger.error(conf.LOG_HEAD + "米游币商品兑换 - 获取商品列表: 网络请求失败")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())
            error_times += 1

    if not isinstance(get_list, list):
        return None

    result = []

    for good in good_list:
        # "next_time" 为 0 表示任何时间均可兑换或兑换已结束
        # "type" 为 1 时商品只有在指定时间开放兑换；为 0 时商品任何时间均可兑换
        if good["next_time"] == 0 and good["type"] == 1:
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
    async def __init__(self, account: UserAccount, goodID: str) -> None:
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

            gameUID = None
            if goodInfo["game"] == "bh3":
                gameUID = account.gameUID.bh3
            elif goodInfo["game"] == "hk4e":
                gameUID = account.gameUID.ys
            elif goodInfo["game"] == "bh2":
                gameUID = account.gameUID.bh2
            elif goodInfo["game"] == "nxx":
                gameUID = account.gameUID.wd
            if gameUID is None:
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
                logger.debug(conf.LOG_HEAD + traceback.format_exc())
                return None


async def game_list_to_image(good_list: list[Good]):
    font = ImageFont.truetype(
        str(conf.goodListImage.FONT_PATH), conf.goodListImage.FONT_SIZE, encoding=conf.ENCODING)

    size_y = 0
    '''起始粘贴位置 高'''
    position: list[tuple] = []
    '''预览图粘贴的位置'''
    imgs: list[Image.Image] = []
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
