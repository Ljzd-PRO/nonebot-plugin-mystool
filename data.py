import json
import os
from pathlib import Path

PATH = Path(__file__).parent.absolute()
ENCODING = "utf-8"


class UserData:
    """
    用户数据相关
    """
    def read_all() -> dict:
        """
        获取所有用户数据
        """
        return json.load(open(os.path.join(PATH, "data", "userdata.json"), encoding=ENCODING))

    def read_account(qq: int, by: int | str) -> dict | None:
        """
        获取用户所拥有的所有米游社帐号信息

        参数:
            qq: 要查找的用户的QQ号
            by: 索引依据，可为备注名或手机号
        """
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        try:
            for account in UserData.read_all()[str(qq)]["accounts"]:
                if account[by_type] == by:
                    return account
        except KeyError:
            pass
        return None

    def read_cookie(qq: int, by: int | str) -> dict | None:
        """
        获取用户的某个米游社帐号的Cookie

        参数:
            qq: 要查找的用户的QQ号
            by: 索引依据，可为备注名或手机号
        """
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        try:
            for account in UserData.read_all()[str(qq)]["accounts"]:
                if account[by_type] == by:
                    return account["cookie"]
        except KeyError:
            pass
        return None

    def read_phone(qq: int, account_name: str) -> int | None:
        """
        获取用户的某个米游社帐号的绑定手机号

        参数:
            qq: 要查找的用户的QQ号
            account_name: 帐号备注名
        """
        try:
            for account in UserData.read_all()[str(qq)]["accounts"]:
                if account["name"] == account_name:
                    return account["phone"]
        except KeyError:
            pass
        return None

    def set_all(userdata:dict):
        """
        写入用户数据文件(整体覆盖)

        参数:
            userdata: 完整用户数据(包含所有用户)
        """
        json.dump(userdata, open(os.path.join(PATH, "data", "userdata.json"), "w", encoding=ENCODING))

    def set_account(account:dict, qq: int, by: int | str) -> bool:
        """
        设置用户的某个米游社帐号信息

        参数:
            account: 米游社帐号信息
            qq: 要设置的用户的QQ号
            by: 索引依据，可为备注名或手机号
        """
        userdata = UserData.read_all()
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        try:
            for num in range(0, len(userdata[str(qq)]["accounts"])):
                if userdata[str(qq)]["accounts"][num][by_type] == by:
                    userdata[str(qq)]["accounts"][num] = account
                    UserData.set_all(userdata)
                    return True
        except KeyError:
            pass
        return None

    def set_cookie(cookie:dict, qq: int, by: int | str) -> dict | None:
        """
        设置用户的某个米游社帐号的Cookie

        参数:
            cookie: Cookie数据
            qq: 要设置的用户的QQ号
            by: 索引依据，可为备注名或手机号
        """
        userdata = UserData.read_all()
        if isinstance(by, str):
            by_type = "name"
        else:
            by_type = "phone"
        try:
            for account in UserData.read_all()[str(qq)]["accounts"]:
                if account[by_type] == by:
                    account["cookie"] = cookie
                    UserData.set_all(userdata)
                    return True
        except KeyError:
            pass
        return None

    def set_phone(phone:int, qq: int, account_name: str) -> int | None:
        """
        设置用户的某个米游社帐号的绑定手机号

        参数:
            phone: 手机号
            qq: 要设置的用户的QQ号
            account_name: 帐号备注名
        """
        userdata = UserData.read_all()
        try:
            for account in UserData.read_all()[str(qq)]["accounts"]:
                if account["name"] == account_name:
                    account["phone"] = phone
                    UserData.set_all(userdata)
                    return True
        except KeyError:
            pass
        return None