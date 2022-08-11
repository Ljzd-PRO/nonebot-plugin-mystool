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

URL_GOOD_LIST = "https://api-takumi.mihoyo.com/mall/v1/web/goods/list?app_id=1&point_sn=myb&page_size=20&page={page}&game={game}"
HEADERS = {
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


class Good:
    """
    商品数据
    """

    def __init__(self, good_dict: dict) -> None:
        self.good_dict = good_dict
        try:
            for func in dir(Good):
                if func.startswith("__"):
                    continue
                getattr(self, func)()
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
    def time(self):
        """
        兑换时间
        """
        # "next_time" 为 0 表示任何时间均可兑换或兑换已结束
        # "type" 为 1 时商品只有在指定时间开放兑换；为 0 时商品任何时间均可兑换
        if self.good_dict["type"] != 1 and self.good_dict["next_time"] == 0:
            return None
        else:
            return time.strftime("%Y-%m-%d %H:%M:%S",
                                 time.localtime(self.good_dict["sale_start_time"]))

    @property
    def num(self):
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
    def icon(self) -> int:
        """
        商品图片
        """
        return self.good_dict["icon"]


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
                get_list: httpx.Response = client.get(URL_GOOD_LIST.format(page=page,
                                                                           game=game), headers=HEADERS)
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
    def __init__(self, account: UserAccount, goodID: str) -> None:
        ...