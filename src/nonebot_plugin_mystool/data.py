"""
### 用户数据相关
"""
import json
import traceback
from copy import deepcopy
from typing import Dict, List, Literal, Tuple, Union

import nonebot.log

from .config import PATH
from .config import mysTool_config as conf
from .utils import generateDeviceID, logger

ENCODING = "utf-8"
USERDATA_PATH = PATH / "userdata.json"

driver = nonebot.get_driver()


class Address:
    """
    地址数据
    """

    def __init__(self, src: Union[dict, int]) -> None:
        """
        初始化地址数据

        :param src: 可为地址数据dict或地址ID(int)
        """
        if isinstance(src, dict):
            self.address_dict = src
            try:
                for func in dir(Address):
                    if func.startswith("__"):
                        continue
                    getattr(self, func)
            except KeyError:
                logger.error(f"{conf.LOG_HEAD}地址数据 - 初始化对象: dict数据不正确")
                logger.debug(f"{conf.LOG_HEAD}{traceback.format_exc()}")
        elif isinstance(src, str):
            self.address_dict = {
                "id": src,
                "connect_name": None,
                "connect_areacode": None,
                "connect_mobile": None,
                "country": None,
                "province": None,
                "city": None,
                "county": None,
                "province_name": None,
                "city_name": None,
                "county_name": None,
                "addr_ext": None,
                "is_default": None,
                "status": None
            }
        else:
            logger.error(
                f"{conf.LOG_HEAD}地址数据 - 初始化对象: 传入数据不正确(传入了{str(type(src))})")

    @property
    def province(self) -> str:
        """
        省
        """
        return self.address_dict["province_name"]

    @property
    def city(self) -> str:
        """
        市
        """
        return self.address_dict["city_name"]

    @property
    def county(self) -> int:
        """
        区/县
        """
        return self.address_dict["county_name"]

    @property
    def detail(self) -> str:
        """
        详细地址
        """
        return self.address_dict["addr_ext"]

    @property
    def phone(self) -> str:
        """
        联系电话(包含区号)
        """
        return self.address_dict["connect_areacode"] + " " + self.address_dict["connect_mobile"]

    @property
    def name(self) -> int:
        """
        收货人姓名
        """
        return self.address_dict["connect_name"]

    @property
    def addressID(self) -> str:
        """
        地址ID
        """
        return self.address_dict["id"]


class AccountUID:
    """
    米哈游游戏UID数据
    """

    def __init__(self) -> None:
        self.ys: str = None
        self.bh3: str = None
        self.bh2: str = None
        self.wd: str = None

    def get(self, uid: Dict[str, str]):
        self.ys: str = uid["ys"]
        self.bh3: str = uid["bh3"]
        self.bh2: str = uid["bh2"]
        self.wd: str = uid["wd"]

    def to_dict(self) -> Dict[str, str]:
        return {
            "ys": self.ys,
            "bh3": self.bh3,
            "bh2": self.bh2,
            "wd": self.wd,
        }


class UserAccount:
    """
    用户的米哈游账户数据
    """

    def __init__(self) -> None:
        self.name: str = None
        '''备注名'''
        self.phone: int = None
        '''绑定手机号'''
        self.cookie: Dict[str, str] = None
        '''Cookie'''
        self.gameUID: AccountUID = AccountUID()
        '''游戏UID'''
        self.deviceID: str = generateDeviceID()
        '''设备 x-rpc-device_id'''
        self.deviceID_2: str = generateDeviceID()
        '''设备第二个 x-rpc-device_id(可用于安卓设备)'''
        self.address: Address = None
        '''地址数据'''
        self.bbsUID: str = None
        '''米游社UID'''
        self.mybMission: bool = True
        '''是否开启米游币任务计划'''
        self.gameSign: bool = True
        '''是否开启米游社游戏签到计划'''
        self.exchange: List[Tuple[str, str]] = []
        '''计划兑换的商品( 元组(商品ID, 游戏UID) )'''
        self.platform: Literal["ios", "android"] = "ios"
        '''设备平台'''
        self.missionGame: List[Literal["ys", "bh3",
                                       "bh2", "wd", "bbs", "xq", "jql"]] = ["ys"]
        '''在哪些板块执行米游币任务计划'''
        self.checkResin: bool = True
        '''是否开启原神树脂提醒'''

    def get(self, account: dict):
        # 适配旧版本的dict
        sample = UserAccount().to_dict()
        if account.keys() != sample.keys():
            add = sample.keys() - account.keys()
            remove = account.keys() - sample.keys()
            for key in add:
                account.setdefault(key, sample[key])
            for key in remove:
                account.pop(key)
        sample = AccountUID().to_dict()
        if account["gameUID"].keys() != sample.keys():
            add = sample.keys() - account["gameUID"].keys()
            remove = account["gameUID"].keys() - sample.keys()
            for key in add:
                account["gameUID"].setdefault(key, sample[key])
            for key in remove:
                account["gameUID"].pop(key)

        self.name: str = account["name"]
        self.phone: int = account["phone"]
        self.cookie: dict[str, str] = account["cookie"]
        self.deviceID: str = account["xrpcDeviceID"]
        self.deviceID_2: str = account["xrpcDeviceID_2"]
        self.address = Address(
            account["address"]) if account["address"] else None
        self.bbsUID: str = account["bbsUID"]
        self.mybMission: bool = account["mybMission"]
        self.gameSign: bool = account["gameSign"]
        self.platform: Literal["ios", "android"] = account["platform"]
        self.missionGame: List[Literal["ys", "bh3", "bh2",
                                       "wd", "bbs", "xq", "jql"]] = account["missionGame"]
        self.checkResin: bool = account["checkResin"]

        exchange = []
        for plan in account["exchange"]:
            exchange.append(tuple(plan))
        self.exchange: List[Tuple[str, str]] = exchange

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "phone": self.phone,
            "cookie": self.cookie,
            "gameUID": self.gameUID.to_dict(),
            "xrpcDeviceID": self.deviceID,
            "xrpcDeviceID_2": self.deviceID_2,
            "address": None,
            "bbsUID": self.bbsUID,
            "mybMission": self.mybMission,
            "gameSign": self.gameSign,
            "exchange": self.exchange,
            "platform": self.platform,
            "missionGame": self.missionGame,
            "checkResin": self.checkResin
        }
        if isinstance(self.address, Address):
            data["address"] = self.address.addressID
        elif isinstance(self.address, int):
            data["address"] = self.address
        return data


class UserData:
    """
    用户数据相关
    """
    OPTION_NOTICE = "notice"
    USER_SAMPLE = {
        "accounts": [],
        OPTION_NOTICE: True
    }
    '''QQ用户数据样例'''

    @staticmethod
    def read_all() -> Dict[int, dict]:
        """
        以dict形式获取userdata.json
        """
        origin = json.load(open(USERDATA_PATH, encoding=conf.ENCODING))
        userdata = {}
        for key in origin:
            userdata.setdefault(int(key), origin[key])
        return userdata

    @classmethod
    def read_account(cls, qq: int, by: Union[int, str]):
        """
        获取用户的某个米游社帐号数据

        :param qq: 要查找的用户的QQ号
        :param by: 索引依据，可为备注名或手机号
        :return: 返回用户的某个米游社帐号数据
        """
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        try:
            for account in cls.read_all()[qq]["accounts"]:
                if account[by_type] == by:
                    userAccount = UserAccount()
                    userAccount.get(account)
                    return userAccount
        except KeyError:
            pass
        return None

    @classmethod
    def read_account_all(cls, qq: int) -> List[UserAccount]:
        """
        获取用户的所有米游社帐号数据

        :param qq: 要查找的用户的QQ号
        :return: 返回用户的所有米游社帐号数据
        """
        accounts = []
        try:
            accounts_raw = cls.read_all()[qq]["accounts"]
            for account_raw in accounts_raw:
                account = UserAccount()
                account.get(account_raw)
                accounts.append(account)
        except KeyError:
            pass
        return accounts

    @staticmethod
    def __set_all(userdata: Dict[int, dict]):
        """
        写入用户数据文件(整体覆盖)

        :param userdata: 完整用户数据(包含所有用户)
        """
        userdata_json = {}
        for key in userdata:
            userdata_json.setdefault(str(key), userdata[key])
        json.dump(userdata_json, open(USERDATA_PATH, "w",
                                      encoding=ENCODING), indent=4, ensure_ascii=False)

    @classmethod
    def __create_user(cls, userdata: Dict[int, dict], qq: int) -> dict:
        """
        创建用户数据，返回创建后整体的userdata
        """
        userdata.setdefault(qq, deepcopy(cls.USER_SAMPLE))
        return userdata

    @staticmethod
    def __create_account(userdata: Dict[str, dict], qq: int, name: str = None, phone: int = None) -> dict:
        """
        创建米哈游账户数据，返回创建后整体的userdata
        """
        account = UserAccount().to_dict()
        account["name"] = name
        account["phone"] = phone
        userdata[str(qq)]["accounts"].append(account)
        return userdata

    @classmethod
    def del_user(cls, qq: int):
        """
        删除某个QQ用户数据

        :param qq: 用户的QQ号

        若未找到返回`False`，否则返回`True`
        """
        userdata = cls.read_all()
        try:
            userdata.pop(qq)
        except KeyError:
            return False
        cls.__set_all(userdata)
        return True

    @classmethod
    def set_account(cls, account: UserAccount, qq: int, by: Union[int, str] = None):
        """
        设置用户的某个米游社帐号信息，若`by`为`None`，则自动根据传入的`UserAccount.phone`查找

        :param account: 米游社帐号信息
        :param qq: 要设置的用户的QQ号
        :param by: (可选)索引依据，可为备注名或手机号
        """
        account_raw = account.to_dict()
        userdata = cls.read_all()
        if isinstance(by, str):
            by_type = "name"
        elif isinstance(by, int):
            by_type = "phone"
        else:
            by_type = "phone"
            by = account.phone

        for num in range(0, len(userdata[qq]["accounts"])):
            if userdata[qq]["accounts"][num][by_type] == by:
                userdata[qq]["accounts"][num] = account_raw
                cls.__set_all(userdata)
                return

    @classmethod
    def del_account(cls, qq: int, by: Union[int, str]):
        """
        删除QQ用户的某个米哈游账号

        :param qq: 用户的QQ号
        :param by: 索引依据，可为备注名或手机号

        若未找到返回`False`，否则返回`True`
        """
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
            by = str(by)
        userdata = cls.read_all()
        try:
            account_list: List[dict] = userdata[qq]["accounts"]
            account_list.remove(
                list(filter(lambda account: account[by_type] == by, account_list))[0])
        except (KeyError, IndexError):
            return False
        cls.__set_all(userdata)
        return True

    @classmethod
    def set_cookie(cls, cookie: Dict[str, str], qq: int, by: Union[int, str]):
        """
        设置用户的某个米游社帐号的Cookie

        :param cookie: Cookie数据
        :param qq: 要设置的用户的QQ号
        :param by: 索引依据，可为备注名或手机号
        """
        userdata = cls.read_all()
        name, phone = None, None
        if isinstance(by, str):
            by_type = "name"
            name = by
        else:
            by_type = "phone"
            phone = by
        if qq not in userdata:
            userdata = cls.__create_user(userdata, qq)

        def action() -> bool:
            for account in userdata[qq]["accounts"]:
                if account[by_type] == by:
                    account["cookie"] = cookie
                    for item in ("login_uid", "stuid", "ltuid", "account_id"):
                        if item in cookie:
                            account["bbsUID"] = cookie[item]
                            break
                    account["cookie"].setdefault("stuid", account["bbsUID"])
                    cls.__set_all(userdata)
                    return True
            return False

        while not action():
            userdata = cls.__create_account(userdata, qq, name, phone)

    @classmethod
    def isNotice(cls, qq: int) -> Union[bool, None]:
        """
        查看用户是否开启了通知，若不存在用户则返回None

        :param qq: 用户QQ号
        :return: 是否开启通知
        """
        userdata = cls.read_all()
        if qq not in userdata:
            return None
        elif cls.OPTION_NOTICE not in userdata[qq]:
            userdata[qq].setdefault(cls.OPTION_NOTICE, True)
            return True
        else:
            return userdata[qq][cls.OPTION_NOTICE]

    @classmethod
    def set_notice(cls, isNotice: bool, qq: int):
        """
        设置用户的通知开关

        :param isNotice: 是否开启通知
        :param qq: 用户QQ号

        返回:
            `True`: 成功写入

            `False`: 写入失败，可能是不存在用户
        """
        userdata = cls.read_all()
        try:
            if cls.OPTION_NOTICE not in userdata[qq]:
                userdata[qq].setdefault(cls.OPTION_NOTICE, isNotice)
            else:
                userdata[qq][cls.OPTION_NOTICE] = isNotice
            cls.__set_all(userdata)
            return True
        except KeyError:
            return False


@driver.on_startup
def create_files():
    if not USERDATA_PATH.exists():
        USERDATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.warning(f"{conf.LOG_HEAD}用户数据文件不存在，将重新生成...")
    else:
        try:
            if not isinstance(json.load(open(USERDATA_PATH, encoding=ENCODING)), dict):
                raise ValueError
            else:
                return
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"{conf.LOG_HEAD}用户数据文件格式错误，将重新生成...")

    with USERDATA_PATH.open("w", encoding=ENCODING) as fp:
        json.dump({}, fp, indent=4, ensure_ascii=False)
