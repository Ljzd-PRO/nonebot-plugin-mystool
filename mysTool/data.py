"""
### 用户数据相关
"""
import json
import traceback
import nonebot
from typing import Union
from nonebot.log import logger
from .utils import PATH, generateDeviceID
from .config import mysTool_config as conf

ENCODING = "utf-8"
USERDATA_PATH = PATH / "data" / "userdata.json"

driver = nonebot.get_driver()


class Address:
    """
    地址数据
    """

    def __init__(self, adress_dict: dict) -> None:
        self.address_dict = adress_dict
        try:
            for func in dir(Address):
                if func.startswith("__"):
                    continue
                getattr(self, func)
        except KeyError:
            logger.error(conf.LOG_HEAD + "地址数据 - 初始化对象: dict数据不正确")
            logger.debug(conf.LOG_HEAD + traceback.format_exc())

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
    def addressID(self) -> int:
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

    def get(self, uid: dict[str, str]):
        self.ys: str = uid["ys"]
        self.bh3: str = uid["bh3"]
        self.bh2: str = uid["bh2"]
        self.wd: str = uid["wd"]

    def to_dict(self) -> dict[str, str]:
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
        self.cookie: dict[str, str] = None
        '''Cookie'''
        self.gameUID: AccountUID = AccountUID()
        '''游戏UID'''
        self.deviceID: str = generateDeviceID()
        '''设备 x-rpc-device_id'''
        self.address: Address = None
        '''地址数据'''
        self.bbsUID: str = None
        '''米游社UID'''
        self.mybMission: bool = True
        '''是否开启米游币任务计划'''
        self.gameSign: bool = True
        '''是否开启米游社游戏签到计划'''
        self.exchange: list[str] = []
        '''计划兑换的商品'''

    def get(self, account: dict):
        # 适配旧版本的dict
        sample = UserAccount().to_dict
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
        self.gameUID = AccountUID()
        self.gameUID.get(account["gameUID"])
        self.deviceID: str = account["xrpcDeviceID"]
        self.address = Address(account["address"])
        self.bbsUID: str = account["bbsUID"]
        self.mybMission: bool = account["mybMission"]
        self.gameSign: bool = account["gameSign"]
        self.exchange: list[str] = account["exchange"]

    @property
    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "phone": self.phone,
            "cookie": self.cookie,
            "gameUID": self.gameUID.to_dict(),
            "xrpcDeviceID": self.deviceID,
            "address": None,
            "bbsUID": self.bbsUID,
            "mybMission": self.mybMission,
            "gameSign": self.gameSign,
            "exchange": self.exchange
        }
        if isinstance(self.address, Address):
            data["address"] = self.address.address_dict
        return data


class UserData:
    """
    用户数据相关
    """
    __OPTION_NOTICE = "notice"
    __USER_SAMPLE = {
        "accounts": [],
        __OPTION_NOTICE: True
    }
    '''QQ用户数据样例'''

    def read_all() -> dict[str, dict]:
        """
        以dict形式获取userdata.json
        """
        return json.load(open(USERDATA_PATH))

    def read_account(qq: int, by: Union[int, str]):
        """
        获取用户的某个米游社帐号数据

        参数:
            `qq`: 要查找的用户的QQ号
            `by`: 索引依据，可为备注名或手机号
        """
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        try:
            for account in UserData.read_all()[str(qq)]["accounts"]:
                if account[by_type] == by:
                    userAccount = UserAccount()
                    userAccount.get(account)
                    return userAccount
        except KeyError:
            pass
        return None

    def read_account_all(qq: int) -> Union[list[UserAccount], None]:
        """
        获取用户的所有米游社帐号数据

        参数:
            `qq`: 要查找的用户的QQ号
        """
        accounts = []
        try:
            accounts_raw = UserData.read_all()[str(qq)]["accounts"]
        except KeyError:
            return None
        for account_raw in accounts_raw:
            account = UserAccount()
            account.get(account_raw)
            accounts.append(account)
        return accounts

    def __set_all(userdata: dict[str, dict]):
        """
        写入用户数据文件(整体覆盖)

        参数:
            `userdata`: 完整用户数据(包含所有用户)
        """
        json.dump(userdata, open(USERDATA_PATH, "w",
                  encoding=ENCODING), indent=4, ensure_ascii=False)

    @classmethod
    def __create_user(cls, userdata: dict[str, dict], qq: int) -> dict:
        """
        创建用户数据，返回创建后整体的userdata
        """
        userdata.setdefault(str(qq), cls.__USER_SAMPLE)
        return userdata

    def __create_account(userdata: dict[str, dict], qq: int, name: str = None, phone: int = None) -> dict:
        """
        创建米哈游账户数据，返回创建后整体的userdata
        """
        account = UserAccount().to_dict
        account["name"] = name
        account["phone"] = phone
        userdata[str(qq)]["accounts"].append(account)
        return userdata

    def set_account(account: UserAccount, qq: int, by: Union[int, str]):
        """
        设置用户的某个米游社帐号信息

        参数:
            `account`: 米游社帐号信息
            `qq`: 要设置的用户的QQ号
            `by`: 索引依据，可为备注名或手机号
        """
        account_raw = account.to_dict
        userdata = UserData.read_all()
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        if qq not in userdata:
            userdata = UserData.__create_user(userdata, qq)

        for num in range(0, len(userdata[str(qq)]["accounts"])):
            if userdata[str(qq)]["accounts"][num][by_type] == by:
                userdata[str(qq)]["accounts"][num] = account_raw
                UserData.__set_all(userdata)
                return
        # 若找不到，进行新建
        userdata[str(qq)]["accounts"].append(account_raw)
        UserData.__set_all(userdata)

    def set_cookie(cookie: dict[str, str], qq: int, by: Union[int, str]):
        """
        设置用户的某个米游社帐号的Cookie

        参数:
            `cookie`: Cookie数据
            `qq`: 要设置的用户的QQ号
            `by`: 索引依据，可为备注名或手机号
        """
        userdata = UserData.read_all()
        name, phone = None, None
        if isinstance(by, str):
            by_type = "name"
            name = by
        else:
            by_type = "phone"
            phone = by
        if qq not in userdata:
            userdata = UserData.__create_user(userdata, qq)

        def action() -> bool:
            for account in userdata[str(qq)]["accounts"]:
                if account[by_type] == by:
                    account["cookie"] = cookie
                    for item in ("login_uid", "stuid", "ltuid", "account_id"):
                        if item in cookie:
                            account["bbsUID"] = cookie[item]
                            break
                    UserData.__set_all(userdata)
                    return True
            return False

        while not action():
            userdata = UserData.__create_account(userdata, qq, name, phone)

    @classmethod
    def isNotice(cls, qq: int) -> Union[bool, None]:
        """
        查看用户是否开启了通知，若不存在用户则返回None

        参数:
            `qq`: 用户QQ号
        """
        userdata = UserData.read_all()
        qq = str(qq)
        if qq not in userdata:
            return None
        elif cls.__OPTION_NOTICE not in userdata[qq]:
            userdata[qq].setdefault(cls.__OPTION_NOTICE, True)
            return True
        else:
            return userdata[qq][cls.__OPTION_NOTICE]


@driver.on_startup
def create_files():
    if not USERDATA_PATH.exists():
        USERDATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.warning(conf.LOG_HEAD + "用户数据文件不存在，将重新生成...")
    else:
        try:
            if not isinstance(json.load(open(USERDATA_PATH, encoding=ENCODING)), dict):
                raise ValueError
            else:
                return
        except json.JSONDecodeError and ValueError:
            logger.warning(conf.LOG_HEAD + "用户数据文件格式错误，将重新生成...")

    with USERDATA_PATH.open("w", encoding=ENCODING) as fp:
        json.dump({}, fp, indent=4, ensure_ascii=False)
