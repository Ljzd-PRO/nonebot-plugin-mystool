"""
### 插件配置相关
"""
from datetime import time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Tuple, Union

from nonebot import get_driver
from pydantic import BaseModel, Extra

if TYPE_CHECKING:
    from loguru import RotationFunction

ROOT_PATH = Path(__name__).parent.absolute()
'''NoneBot2 机器人根目录'''
PATH = ROOT_PATH / "data" / "nonebot-plugin-mystool"
'''插件数据保存目录'''


class DeviceConfig(BaseModel, extra=Extra.ignore):
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

    X_RPC_APP_VERSION: str = "2.42.1"
    '''Headers所用的 x-rpc-app_version'''
    X_RPC_PLATFORM: str = "ios"
    '''Headers所用的 x-rpc-platform'''
    UA: str = "\".Not/A)Brand\";v=\"99\", \"Microsoft Edge\";v=\"103\", \"Chromium\";v=\"103\""
    '''Headers所用的 sec-ch-ua'''
    UA_PLATFORM: str = "\"macOS\""
    '''Headers所用的 sec-ch-ua-platform'''


class GoodListImage(BaseModel, extra=Extra.ignore):
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
    SAVE_PATH: Path = PATH
    '''商品列表图片缓存目录'''


class Config(BaseModel, extra=Extra.ignore):
    ENCODING: str = "utf-8"
    '''文件读写编码'''

    MAX_USER: int = 10
    '''支持最多用户数'''
    ADD_FRIEND_ACCEPT: bool = True
    '''是否自动同意好友申请'''

    COMMAND_START: str = ""
    '''插件内部命令头(若为""空字符串则不启用)'''
    PLUGIN_NAME: str = "nonebot_plugin_mystool"
    '''插件名(为模块名字，或于plugins目录手动加载时的目录名)'''

    LOG_HEAD: str = ""
    '''日志开头字符串(只有把插件放进plugins目录手动加载时才需要设置)'''
    LOG_SAVE: bool = True
    '''是否输出日志到文件(插件在plugins目录加载时，需要设置LOG_HEAD)'''
    LOG_PATH: Path = PATH / "mystool.log"
    '''日志保存路径'''
    LOG_ROTATION: Union[str, int, time, timedelta, "RotationFunction"] = "1 week"
    '''日志保留时长(需要按照格式设置)'''

    NTP_SERVER: str = "ntp.aliyun.com"
    '''NTP服务器，用于获取网络时间'''
    MAX_RETRY_TIMES: int = 5
    '''网络请求失败后最多重试次数'''
    SLEEP_TIME: float = 5
    '''任务操作冷却时间(如米游币任务)'''
    SLEEP_TIME_RETRY: float = 3
    '''网络请求出错的重试冷却时间'''
    TIME_OUT: Union[float, None] = None
    '''网络请求超时时间'''
    GITHUB_PROXY: str = "https://ghproxy.com/"
    '''GitHub代理加速服务器(若为""空字符串则不启用)'''

    SIGN_TIME: str = "00:30"
    '''每日自动签到和米游社任务的定时任务执行时间，格式为HH:MM'''
    RESIN_CHECK_INTERVAL: int = 60
    '''每次检查原神便笺间隔，单位为分钟'''
    EXCHANGE_THREAD: int = 3
    '''商品兑换线程数'''

    SALT_IOS: str = "YVEIkzDFNHLeKXLxzqCA9TzxCpWwbIbk"
    '''生成Headers iOS DS所需的salt'''
    SALT_ANDROID: str = "n0KjuIrKgLHh08LWSCYP0WXlVXaYvV64"
    '''生成Headers Android DS所需的salt'''
    SALT_DATA: str = "t0qEgfub6cvueAPgR5m9aQWWVciEer7v"
    '''Android 设备传入content生成 DS 所需的 salt'''
    SALT_PARAMS: str = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
    '''Android 设备传入url参数生成 DS 所需的 salt'''

    device: DeviceConfig = DeviceConfig()
    goodListImage: GoodListImage = GoodListImage()


mysTool_config = Config.parse_obj(get_driver().config)
