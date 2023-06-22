"""
### 插件数据相关
"""
import os
from datetime import time, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Union, Optional, Tuple, Any, Dict, TYPE_CHECKING, AbstractSet, \
    Mapping

from loguru import logger
from pydantic import BaseModel, ValidationError, BaseSettings, validator

from .user_data import UserData, UserAccount

VERSION = "v1.0.0"
"""程序当前版本"""

ROOT_PATH = Path(__name__).parent.absolute()
'''NoneBot2 机器人根目录'''

DATA_PATH = ROOT_PATH / "data" / "nonebot-plugin-mystool"
'''插件数据保存目录'''

PLUGIN_DATA_PATH = DATA_PATH / "plugin_data.json"
"""插件数据文件默认路径"""

if TYPE_CHECKING:
    IntStr = Union[int, str]
    DictStrAny = Dict[str, Any]
    AbstractSetIntStr = AbstractSet[IntStr]
    MappingIntStrAny = Mapping[IntStr, Any]


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
    exchange_thread_count: int = 2
    """兑换线程数"""
    exchange_latency: Tuple[float, float] = (0, 0.35)
    """兑换时间延迟随机范围（单位：秒）（防止因为发出请求的时间过于精准而被服务器认定为非人工操作）"""
    enable_log_output: bool = True
    """是否保存日志"""
    log_head: str = ""
    '''日志开头字符串(只有把插件放进plugins目录手动加载时才需要设置)'''
    log_path: Optional[Path] = DATA_PATH / "mystool.log"
    """日志保存路径"""
    log_rotation: Union[str, int, time, timedelta] = "1 week"
    '''日志保留时长(需要按照格式设置)'''
    plugin_name: str = "nonebot_plugin_mystool"
    '''插件名(为模块名字，或于plugins目录手动加载时的目录名)'''
    encoding: str = "utf-8"
    '''文件读写编码'''
    max_user: int = 10
    '''支持最多用户数'''
    add_friend_accept: bool = True
    '''是否自动同意好友申请'''
    add_friend_welcome: bool = True
    '''用户添加机器人为好友以后，是否发送使用指引信息'''
    command_start: str = ""
    '''插件内部命令头(若为""空字符串则不启用)'''
    sleep_time: float = 5
    '''任务操作冷却时间(如米游币任务)'''
    plan_time: str = "00:30"
    '''每日自动签到和米游社任务的定时任务执行时间，格式为HH:MM'''
    resin_interval: int = 60
    '''每次检查原神便笺间隔，单位为分钟'''
    geetest_url: Optional[str]
    '''极验Geetest人机验证打码接口URL'''

    @validator("log_path", allow_reuse=True)
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
        # TODO: env_prefix = "..."  # 环境变量前缀
        #   使用 nonebot2 的 环境变量规范
        ...


class GoodListImageConfig(BaseModel):
    """
    商品列表输出图片设置
    """
    ICON_SIZE: Tuple[int, int] = (600, 600)
    '''商品预览图在最终结果图中的大小'''
    WIDTH: int = 2000
    '''最终结果图宽度'''
    PADDING_ICON: int = 0
    '''展示图与展示图之间的间隙 高'''
    PADDING_TEXT_AND_ICON_Y: int = 125
    '''文字顶部与展示图顶部之间的距离 高'''
    PADDING_TEXT_AND_ICON_X: int = 10
    '''文字与展示图之间的横向距离 宽'''
    FONT_PATH: Union[Path, str, None] = None
    '''
    字体文件路径(若使用计算机已经安装的字体，直接填入字体名称，若为None则自动下载字体)

    开源字体 Source Han Sans 思源黑体
    https://github.com/adobe-fonts/source-han-sans
    '''
    FONT_SIZE: int = 50
    '''字体大小'''
    SAVE_PATH: Path = DATA_PATH
    '''商品列表图片缓存目录'''


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


class PluginData(BaseModel):
    version: str = VERSION
    """创建插件数据文件时的版本号"""
    preference: Preference = Preference()
    """偏好设置"""
    salt_config: SaltConfig = SaltConfig()
    """生成Headers - DS所用salt值"""
    device_config: DeviceConfig = DeviceConfig()
    """设备信息"""
    good_list_image_config: GoodListImageConfig = GoodListImageConfig()
    """商品列表输出图片设置"""
    users: Dict[int, UserData] = {}
    '''所有用户数据'''

    class Config:
        json_encoders = UserAccount.Config.json_encoders


class PluginDataManager:
    plugin_data_obj = PluginData()
    """加载出的插件数据对象"""

    @classmethod
    def load_plugin_data(cls):
        """
        加载插件数据文件
        """
        if os.path.exists(PLUGIN_DATA_PATH) and os.path.isfile(PLUGIN_DATA_PATH):
            try:
                new_model = PluginData.parse_file(PLUGIN_DATA_PATH)
                for attr in new_model.__fields__:
                    PluginDataManager.plugin_data_obj.__setattr__(attr, new_model.__getattribute__(attr))
            except (ValidationError, JSONDecodeError):
                logger.exception(f"读取插件数据文件失败，请检查插件数据文件 {PLUGIN_DATA_PATH} 格式是否正确")
                raise
            except:
                logger.exception(
                    f"读取插件数据文件失败，请检查插件数据文件 {PLUGIN_DATA_PATH} 是否存在且有权限读取和写入")
                raise
        else:
            plugin_data = PluginData()
            try:
                str_data = plugin_data.json(indent=4)
                with open(PLUGIN_DATA_PATH, "w", encoding="utf-8") as f:
                    f.write(str_data)
            except (AttributeError, TypeError, ValueError, PermissionError):
                logger.exception(f"创建插件数据文件失败，请检查是否有权限读取和写入 {PLUGIN_DATA_PATH}")
                raise
            logger.info(f"插件数据文件 {PLUGIN_DATA_PATH} 不存在，已创建默认插件数据文件。")


PluginDataManager.load_plugin_data()


def write_plugin_data(data: PluginData = None):
    """
    写入插件数据文件

    :param data: 配置对象
    """
    if data is None:
        data = PluginDataManager.plugin_data_obj
    try:
        str_data = data.json(indent=4)
    except (AttributeError, TypeError, ValueError):
        logger.exception("数据对象序列化失败，可能是数据类型错误")
        return False
    with open(PLUGIN_DATA_PATH, "w", encoding="utf-8") as f:
        f.write(str_data)
    return True
