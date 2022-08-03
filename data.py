import json
import nonebot
from nonebot.log import logger
from utils import *
from .config import mysTool_config as conf
from pathlib import Path

PATH = Path(__file__).parent.absolute()
ENCODING = "utf-8"
USERDATA_PATH = PATH / "data" / "userdata.json"

driver = nonebot.get_driver()


class AccountUID:
    """
    米哈游游戏UID数据
    """

    def __init__(self) -> None:
        self.ys: int = None
        self.bh3: int = None
        self.bh2: int = None
        self.wd: int = None

    def get(self, uid: dict[str, int]):
        self.ys: int = uid["ys"]
        self.bh3: int = uid["bh3"]
        self.bh2: int = uid["bh2"]
        self.wd: int = uid["wd"]

    @property
    def to_dict(self) -> dict:
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
        self.phone: int = None
        self.cookie: dict[str, str] = None
        self.uid: AccountUID = AccountUID()
        self.deviceID: str = None

    def get(self, account: dict):
        self.name: str = account["name"]
        self.phone: int = account["phone"]
        self.cookie: dict[str, str] = account["cookie"]
        self.uid = AccountUID(account["uid"])
        self.deviceID: str = account["xrpcDeviceID"]

    @property
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "phone": self.phone,
            "cookie": self.cookie,
            "uid": self.uid.to_dict,
            "xrpcDeviceID": self.deviceID,
        }


class UserData:
    """
    用户数据相关
    """
    __USER_SAMPLE = {
        "accounts": []
    }
    '''QQ用户数据样例'''

    def __read_all() -> dict:
        """
        获取所有用户数据
        """
        return json.load(open(USERDATA_PATH), encoding=ENCODING)

    def read_account(qq: int, by: int | str):
        """
        获取用户的某个米游社帐号数据

        参数:
            qq: 要查找的用户的QQ号
            by: 索引依据，可为备注名或手机号
        """
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        try:
            for account in UserData.__read_all()[str(qq)]["accounts"]:
                if account[by_type] == by:
                    userAccount = UserAccount()
                    userAccount.get(account)
                    return userAccount
        except KeyError:
            pass
        return None

    def read_account_all(qq: int) -> list[UserAccount]:
        """
        获取用户的所有米游社帐号数据

        参数:
            qq: 要查找的用户的QQ号
        """
        accounts = []
        try:
            accounts_raw = UserData.__read_all()[qq]["accounts"]
        except KeyError:
            pass
        for account_raw in accounts_raw:
            account = UserAccount()
            account.get(account_raw)
            accounts.append(account)
        return accounts

    def __set_all(userdata: dict):
        """
        写入用户数据文件(整体覆盖)

        参数:
            userdata: 完整用户数据(包含所有用户)
        """
        json.dump(userdata, open(USERDATA_PATH, "w", encoding=ENCODING), indent=4, ensure_ascii=False)

    @classmethod
    def __create_user(cls, userdata: dict, qq: int) -> dict:
        """
        创建用户数据，返回创建后整体的userdata
        """
        userdata.setdefault(qq, cls.__USER_SAMPLE)
        return userdata

    def __create_account(userdata: dict, qq: int, name: str = None, phone: int = None) -> dict:
        """
        创建米哈游账户数据，返回创建后整体的userdata
        """
        account = UserAccount().to_dict
        account["name"] = name
        account["phone"] = phone
        userdata[qq]["accounts"].append(account)
        return userdata

    def set_account(account: UserAccount, qq: int, by: int | str):
        """
        设置用户的某个米游社帐号信息

        参数:
            account: 米游社帐号信息
            qq: 要设置的用户的QQ号
            by: 索引依据，可为备注名或手机号
        """
        account_raw = account.to_dict
        userdata = UserData.__read_all()
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

    def set_cookie(cookie: dict[str, str], qq: int, by: int | str):
        """
        设置用户的某个米游社帐号的Cookie

        参数:
            cookie: Cookie数据
            qq: 要设置的用户的QQ号
            by: 索引依据，可为备注名或手机号
        """
        userdata = UserData.__read_all()
        name, phone = None
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        if qq not in userdata:
            userdata = UserData.__create_user(userdata, qq)

        def action() -> bool:
            for account in UserData.__read_all()[str(qq)]["accounts"]:
                if account[by_type] == by:
                    account["cookie"] = cookie
                    UserData.__set_all(userdata)
                    return True
            return False

        if not action():
            userdata = UserData.__create_account(userdata, qq, name, phone)
        action()


@driver.on_startup
def create_files():
    if not USERDATA_PATH.exists():
        USERDATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.warning(conf.LOG_HEAD + "用户数据文件不存在，将重新生成...")
    else:
        try:
            if not isinstance(json.load(open(USERDATA_PATH, encoding=ENCODING)), dict):
                raise ValueError
        except json.JSONDecodeError and ValueError:
            logger.warning(conf.LOG_HEAD + "用户数据文件格式错误，将重新生成...")

    with USERDATA_PATH.open("w", encoding=ENCODING) as fp:
        json.dump({}, fp, indent=4, ensure_ascii=False)
