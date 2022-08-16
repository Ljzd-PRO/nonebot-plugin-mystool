"""
### 插件配置相关
"""
import json
from nonebot.log import logger
from pydantic import BaseModel, Extra, ValidationError
from pathlib import Path
from typing import Tuple, Union
from nonebot import get_driver

PATH = Path(__file__).parent.absolute()
CONFIG_PATH = PATH / "data" / "config.json"


class DeviceConfig(BaseModel, extra=Extra.ignore):
    """
    设备信息
    DS算法与设备信息有关联，非必要请勿修改
    """
    USER_AGENT_MOBILE: str = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.25.1"
    '''移动端 User-Agent'''
    USER_AGENT_PC: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
    '''桌面端 User-Agent'''
    USER_AGENT_OTHER: str = "Hyperion/177 CFNetwork/1331.0.7 Darwin/21.4.0"
    '''获取用户 ActionTicket 时Headers所用的 User-Agent'''
    X_RPC_DEVICE_MODEL_MOBILE: str = "iPhone10,2"
    '''移动端 x-rpc-device_model'''
    X_RPC_DEVICE_MODEL_PC: str = "OS X 10.15.7"
    '''桌面端 x-rpc-device_model'''
    X_RPC_DEVICE_NAME_MOBILE: str = "iPhone"
    '''移动端 x-rpc-device_name'''
    X_RPC_DEVICE_NAME_PC: str = "Microsoft Edge 103.0.1264.62"
    '''桌面端 x-rpc-device_name'''
    X_RPC_APP_VERSION: str = "2.34.1"
    '''Headers所用的 x-rpc-app_version'''
    X_RPC_SYS_VERSION: str = "15.1"
    '''Headers所用的 x-rpc-sys_version'''
    X_RPC_CHANNEL: str = "appstore"
    '''Headers所用的 x-rpc-channel'''
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
    FONT_PATH: Union[Path, str] = PATH / "font" / "PingFang.ttc"
    '''字体文件路径(若使用计算机已经安装的字体，直接填入字体名称)'''
    FONT_SIZE: int = 50
    '''字体大小'''
    SAVE_PATH: Path = PATH / "data"
    '''商品列表图片缓存目录'''


class Config(BaseModel, extra=Extra.ignore):
    ENCODING: str = "utf-8"
    '''文件读写编码'''
    MAX_USER: int = 10
    '''支持最多用户数'''
    LOG_HEAD: str = "mysTool: "
    '''日志开头字符串'''
    NTP_SERVER: str = "ntp.aliyun.com"
    '''NTP服务器，用于获取网络时间'''
    MAX_RETRY_TIMES: int = 5
    '''网络请求失败后最多重试次数'''
    SLEEP_TIME: float = 3
    '''网络请求冷却时间'''
    TIME_OUT: Union[float, None] = None
    '''网络请求超时时间'''
    USE_COMMAND_START: bool = False
    '''采用插件内部命令头'''
    COMMAND_START: str = "mt "
    '''插件内部命令头'''

    device: DeviceConfig = DeviceConfig()
    goodListImage: GoodListImage = GoodListImage()


mysTool_config = Config.parse_obj(get_driver().config)
