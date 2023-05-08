import os
import traceback
from json import JSONDecodeError
from pathlib import Path
from typing import List, Union, Optional, Tuple, Any, Dict, Set, Callable, TYPE_CHECKING, AbstractSet, \
    Mapping

from httpx import Cookies
from loguru import logger
from pydantic import BaseModel, Extra, ValidationError, BaseSettings, validator

from .data_model import BaseModelWithSetter, Good, Address, GameRecord

ROOT_PATH = Path("./")
"""程序所在目录"""

CONFIG_PATH = ROOT_PATH / "user_data.json"
"""用户数据文件默认路径"""

VERSION = "2.0.0"
"""程序当前版本"""

if TYPE_CHECKING:
    IntStr = Union[int, str]
    DictStrAny = Dict[str, Any]
    AbstractSetIntStr = AbstractSet[IntStr]
    MappingIntStrAny = Mapping[IntStr, Any]


class BBSCookies(BaseModelWithSetter):
    """
    米游社Cookies数据

    # 测试 is_correct() 方法

    >>> assert BBSCookies().is_correct() is False
    >>> assert BBSCookies(stuid="123", stoken="123", cookie_token="123").is_correct() is True

    # 测试 bbs_uid getter

    >>> bbs_cookies = BBSCookies()
    >>> assert not bbs_cookies.bbs_uid
    >>> assert BBSCookies(stuid="123").bbs_uid == "123"

    # 测试 bbs_uid setter

    >>> bbs_cookies.bbs_uid = "123"
    >>> assert bbs_cookies.bbs_uid == "123"

    # 检查构造函数内所用的 stoken setter

    >>> bbs_cookies = BBSCookies(stoken="abcd1234")
    >>> assert bbs_cookies.stoken_v1 and not bbs_cookies.stoken_v2
    >>> bbs_cookies = BBSCookies(stoken="v2_abcd1234==")
    >>> assert bbs_cookies.stoken_v2 and not bbs_cookies.stoken_v1
    >>> assert bbs_cookies.stoken == "v2_abcd1234=="

    # 检查 stoken setter

    >>> bbs_cookies = BBSCookies(stoken="abcd1234")
    >>> bbs_cookies.stoken = "v2_abcd1234=="
    >>> assert bbs_cookies.stoken_v2 == "v2_abcd1234=="
    >>> assert bbs_cookies.stoken_v1 == "abcd1234"

    # 检查 .dict 方法能否生成包含 stoken_2 类型的 stoken 的字典
    >>> bbs_cookies = BBSCookies()
    >>> bbs_cookies.stoken_v1 = "abcd1234"
    >>> bbs_cookies.stoken_v2 = "v2_abcd1234=="
    >>> assert bbs_cookies.dict(v2_stoken=True)["stoken"] == "v2_abcd1234=="

    # 检查是否有多余的字段

    >>> bbs_cookies = BBSCookies(stuid="123")
    >>> assert all(bbs_cookies.dict())
    >>> assert all(map(lambda x: x not in bbs_cookies, ["stoken_v1", "stoken_v2"]))
    """
    stuid: Optional[str]
    """米游社UID"""
    ltuid: Optional[str]
    """米游社UID"""
    account_id: Optional[str]
    """米游社UID"""
    login_uid: Optional[str]
    """米游社UID"""

    stoken_v1: Optional[str]
    """保存stoken_v1，方便后续使用"""
    stoken_v2: Optional[str]
    """保存stoken_v2，方便后续使用"""

    cookie_token: Optional[str]
    login_ticket: Optional[str]
    ltoken: Optional[str]
    mid: Optional[str]

    def __init__(self, **data: Any):
        super().__init__(**data)
        stoken = data.get("stoken")
        if stoken:
            self.stoken = stoken

    def is_correct(self) -> bool:
        """判断是否为正确的Cookies"""
        if self.bbs_uid and self.stoken and self.cookie_token:
            return True
        else:
            return False

    @property
    def bbs_uid(self):
        """
        获取米游社UID
        """
        uid = None
        for value in [self.stuid, self.ltuid, self.account_id, self.login_uid]:
            if value:
                uid = value
                break
        return uid or None

    @bbs_uid.setter
    def bbs_uid(self, value: str):
        self.stuid = value
        self.ltuid = value
        self.account_id = value
        self.login_uid = value

    @property
    def stoken(self):
        """
        获取stoken
        """
        if self.stoken_v1:
            return self.stoken_v1
        elif self.stoken_v2:
            return self.stoken_v2
        else:
            return None

    @stoken.setter
    def stoken(self, value):
        if value.startswith("v2_"):
            self.stoken_v2 = value
        else:
            self.stoken_v1 = value

    def update(self, cookies: Union[Dict[str, str], Cookies, "BBSCookies"]):
        """
        更新Cookies
        """
        if isinstance(cookies, BBSCookies):
            [setattr(self, key, value) for key, value in cookies.dict().items() if value]
        else:
            self_dict: Dict[str, str] = self.dict()
            self_dict.update(cookies)
            self.parse_obj(self_dict)

    def dict(self, *,
             include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
             exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
             by_alias: bool = False,
             skip_defaults: Optional[bool] = None, exclude_unset: bool = False, exclude_defaults: bool = False,
             exclude_none: bool = False, v2_stoken: bool = False,
             cookie_type: bool = False) -> 'DictStrAny':
        """
        获取Cookies字典

        v2_stoken: stoken 字段是否使用 stoken_v2
        cookie_type: 是否返回符合Cookie类型的字典（没有自定义的stoken_v1、stoken_v2键）
        """
        # 保证 stuid, ltuid 等字段存在
        self.bbs_uid = self.bbs_uid
        cookies_dict = super().dict(include=include, exclude=exclude, by_alias=by_alias, skip_defaults=skip_defaults,
                                    exclude_unset=exclude_unset, exclude_defaults=exclude_defaults,
                                    exclude_none=exclude_none)
        if v2_stoken:
            cookies_dict["stoken"] = self.stoken_v2

        if cookie_type:
            # 去除自定义的 stoken_v1, stoken_v2 字段
            cookies_dict.pop("stoken_v1")
            cookies_dict.pop("stoken_v2")

            # 去除空的字段
            empty_key = set()
            for key, value in cookies_dict.items():
                if not value:
                    empty_key.add(key)
            [cookies_dict.pop(key) for key in empty_key]

        return cookies_dict


class UserAccount(BaseModelWithSetter, extra=Extra.ignore):
    """
    米游社账户数据

    >>> user_account = UserAccount(cookies=BBSCookies())
    >>> assert isinstance(user_account, UserAccount)
    >>> user_account.bbs_uid = "123"
    >>> assert user_account.bbs_uid == "123"
    """
    phone_number: Optional[str]
    """手机号"""
    cookies: BBSCookies
    """Cookies"""

    device_id_ios: str
    """iOS设备用 deviceID"""
    device_id_android: str
    """安卓设备用 deviceID"""

    def __init__(self, **data: Any):
        if not data.get("device_id_ios") or not data.get("device_id_android"):
            from .utils import generate_device_id
            if not data.get("device_id_ios"):
                data.setdefault("device_id_ios", generate_device_id())
            if not data.get("device_id_android"):
                data.setdefault("device_id_android", generate_device_id())
        super().__init__(**data)

    @property
    def bbs_uid(self):
        """
        获取米游社UID
        """
        return self.cookies.bbs_uid

    @bbs_uid.setter
    def bbs_uid(self, value: str):
        self.cookies.bbs_uid = value


class ExchangePlan(BaseModel):
    """
    兑换计划数据类
    """
    good: Good
    """商品"""
    address: Optional[Address]
    """地址ID"""
    account: UserAccount
    """米游社账号"""
    game_record: Optional[GameRecord]
    """商品对应的游戏的玩家账号"""

    def __hash__(self):
        return hash(
            (
                self.good.goods_id,
                self.good.time,
                self.address.id if self.address else None,
                self.account.bbs_uid,
                self.game_record.game_role_id if self.game_record else None
            )
        )


class ExchangeResult(BaseModel):
    """
    兑换结果数据类
    """
    result: bool
    """兑换结果"""
    return_data: dict
    """返回数据"""
    plan: ExchangePlan
    """兑换计划"""


class Preference(BaseSettings):
    """
    偏好设置
    """
    github_proxy: Optional[str] = "https://ghproxy.com/"
    """GitHub加速代理 最终会拼接在原GitHub链接前面"""
    enable_connection_test: bool = True
    """是否开启连接测试"""
    connection_test_interval: Optional[float] = 30
    """连接测试间隔（单位：秒）"""
    timeout: float = 10
    """网络请求超时时间（单位：秒）"""
    max_retry_times: Optional[int] = 3
    """最大网络请求重试次数"""
    retry_interval: float = 2
    """网络请求重试间隔（单位：秒）（除兑换请求外）"""
    enable_ntp_sync: Optional[bool] = True
    """是否开启NTP时间同步（将调整实际发出兑换请求的时间，而不是修改系统时间）"""
    ntp_server: Optional[str] = "ntp.aliyun.com"
    """NTP服务器地址"""
    timezone: Optional[str] = "Asia/Shanghai"
    """兑换时所用的时区"""
    geetest_statics_path: Optional[Path]
    """GEETEST行为验证 网站静态文件目录（默认读取本地包自带的静态文件）"""
    geetest_listen_address: Optional[Tuple[str, int]] = ("localhost", 0)
    """登录时使用的 GEETEST行为验证 WEB服务 本地监听地址"""
    exchange_thread_count: int = 2
    """兑换线程数"""
    exchange_latency: Tuple[float, float] = (0, 0.35)
    """兑换时间延迟随机范围（单位：秒）（防止因为发出请求的时间过于精准而被服务器认定为非人工操作）"""
    enable_log_output: bool = True
    """是否保存日志"""
    log_path: Optional[Path] = ROOT_PATH / "logs" / "mys_goods_tool.log"
    """日志保存路径"""

    @validator("log_path")
    def _(cls, v: Optional[Path]):
        absolute_path = v.absolute()
        if not os.path.exists(absolute_path) or not os.path.isfile(absolute_path):
            absolute_parent = absolute_path.parent
            try:
                os.makedirs(absolute_parent, exist_ok=True)
            except PermissionError:
                logger.warning(f"程序没有创建日志目录 {absolute_parent} 的权限")
        elif not os.access(absolute_path, os.W_OK):
            logger.warning(f"程序没有写入日志文件 {absolute_path} 的权限")
        return v

    class Config:
        env_prefix = "MYS_GOODS_TOOL_"  # 环境变量前缀


class SaltConfig(BaseSettings):
    """
    生成Headers - DS所用salt值
    """
    SALT_IOS: str = "ulInCDohgEs557j0VsPDYnQaaz6KJcv5"
    '''生成Headers iOS DS所需的salt'''
    SALT_ANDROID: str = "n0KjuIrKgLHh08LWSCYP0WXlVXaYvV64"
    '''生成Headers Android DS所需的salt'''
    SALT_DATA: str = "t0qEgfub6cvueAPgR5m9aQWWVciEer7v"
    '''Android 设备传入content生成 DS 所需的 salt'''
    SALT_PARAMS: str = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
    '''Android 设备传入url参数生成 DS 所需的 salt'''
    SALT_PROD: str = "JwYDpKvLj6MrMqqYU6jTKF17KNO2PXoS"

    class Config(Preference.Config):
        pass


class DeviceConfig(BaseSettings):
    """
    设备信息
    DS算法与设备信息有关联，非必要请勿修改
    """
    USER_AGENT_MOBILE: str = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.42.1"
    '''移动端 User-Agent(Mozilla UA)'''
    USER_AGENT_PC: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
    '''桌面端 User-Agent(Mozilla UA)'''
    USER_AGENT_OTHER: str = "Hyperion/275 CFNetwork/1402.0.8 Darwin/22.2.0"
    '''获取用户 ActionTicket 时Headers所用的 User-Agent'''
    USER_AGENT_ANDROID: str = "Mozilla/5.0 (Linux; Android 11; MI 8 SE Build/RQ3A.211001.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/104.0.5112.97 Mobile Safari/537.36 miHoYoBBS/2.36.1"
    '''安卓端 User-Agent(Mozilla UA)'''
    USER_AGENT_ANDROID_OTHER: str = "okhttp/4.9.3"
    '''安卓端 User-Agent(专用于米游币任务等)'''
    USER_AGENT_WIDGET: str = "WidgetExtension/231 CFNetwork/1390 Darwin/22.0.0"
    '''iOS 小组件 User-Agent(原神实时便笺)'''

    X_RPC_DEVICE_MODEL_MOBILE: str = "iPhone10,2"
    '''移动端 x-rpc-device_model'''
    X_RPC_DEVICE_MODEL_PC: str = "OS X 10.15.7"
    '''桌面端 x-rpc-device_model'''
    X_RPC_DEVICE_MODEL_ANDROID: str = "MI 8 SE"
    '''安卓端 x-rpc-device_model'''

    X_RPC_DEVICE_NAME_MOBILE: str = "iPhone"
    '''移动端 x-rpc-device_name'''
    X_RPC_DEVICE_NAME_PC: str = "Microsoft Edge 103.0.1264.62"
    '''桌面端 x-rpc-device_name'''
    X_RPC_DEVICE_NAME_ANDROID: str = "Xiaomi MI 8 SE"
    '''安卓端 x-rpc-device_name'''

    X_RPC_SYS_VERSION: str = "15.4"
    '''Headers所用的 x-rpc-sys_version'''
    X_RPC_SYS_VERSION_ANDROID: str = "11"
    '''安卓端 x-rpc-sys_version'''

    X_RPC_CHANNEL: str = "appstore"
    '''Headers所用的 x-rpc-channel'''
    X_RPC_CHANNEL_ANDROID: str = "miyousheluodi"
    '''安卓端 x-rpc-channel'''

    X_RPC_APP_VERSION: str = "2.28.1"
    '''Headers所用的 x-rpc-app_version'''
    X_RPC_PLATFORM: str = "ios"
    '''Headers所用的 x-rpc-platform'''
    UA: str = "\".Not/A)Brand\";v=\"99\", \"Microsoft Edge\";v=\"103\", \"Chromium\";v=\"103\""
    '''Headers所用的 sec-ch-ua'''
    UA_PLATFORM: str = "\"macOS\""
    '''Headers所用的 sec-ch-ua-platform'''

    class Config(Preference.Config):
        pass


class UserData(BaseModel):
    """
    用户数据类
    """
    version: str = VERSION
    """创建用户数据的程序版本号"""
    exchange_plans: Union[Set[ExchangePlan], List[ExchangePlan]] = set()
    """兑换计划列表"""
    preference: Preference = Preference()
    """偏好设置"""
    salt_config: SaltConfig = SaltConfig()
    """生成Headers - DS所用salt值"""
    device_config: DeviceConfig = DeviceConfig()
    """设备信息"""
    accounts: Dict[str, UserAccount] = {}
    """储存一些已绑定的账号数据"""

    def __init__(self, **data: Any):
        super().__init__(**data)
        exchange_plans = self.exchange_plans
        self.exchange_plans = set()
        for plan in exchange_plans:
            plan = ExchangePlan.parse_obj(plan)
            self.exchange_plans.add(plan)

    def save(self):
        """
        保存用户数据文件
        """
        return write_config_file(self)

    def json(
            self,
            *,
            include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']] = None,
            by_alias: bool = False,
            skip_defaults: Optional[bool] = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            encoder: Optional[Callable[[Any], Any]] = None,
            models_as_dict: bool = True,
            **dumps_kwargs: Any,
    ) -> str:
        """
        重写 BaseModel.json() 方法，使其支持对 Set 类型的数据进行序列化
        """
        set_plans = self.exchange_plans
        self.exchange_plans = list(set_plans)
        json_data = super().json(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            encoder=encoder,
            models_as_dict=models_as_dict,
            **dumps_kwargs,
        )
        self.exchange_plans = set_plans
        return json_data


def write_config_file(conf: UserData = UserData()):
    """
    写入用户数据文件

    :param conf: 配置对象
    """
    try:
        str_data = conf.json(indent=4)
    except (AttributeError, TypeError, ValueError):
        logger.exception("数据对象序列化失败，可能是数据类型错误")
        return False
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(str_data)
    return True


def load_config():
    """
    加载用户数据文件
    """
    if os.path.exists(CONFIG_PATH) and os.path.isfile(CONFIG_PATH):
        try:
            return UserData.parse_file(CONFIG_PATH)
        except (ValidationError, JSONDecodeError):
            logger.error(f"读取用户数据文件失败，请检查用户数据文件 {CONFIG_PATH} 格式是否正确")
            logger.debug(traceback.format_exc())
            exit(1)
        except:
            logger.error(f"读取用户数据文件失败，请检查用户数据文件 {CONFIG_PATH} 是否存在且程序有权限读取和写入")
            logger.debug(traceback.format_exc())
            exit(1)
    else:
        user_data = UserData()
        try:
            write_config_file(user_data)
        except PermissionError:
            logger.error(f"创建用户数据文件失败，请检查程序是否有权限读取和写入 {CONFIG_PATH}")
            logger.debug(traceback.format_exc())
            exit(1)
        # logger.info(f"用户数据文件 {CONFIG_PATH} 不存在，已创建默认用户数据文件。")
        # 由于会输出到标准输出流，影响TUI观感，因此暂时取消

        return user_data


config = load_config()
"""程序配置对象"""
