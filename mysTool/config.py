import nonebot
import json
from nonebot.log import logger
from pydantic import BaseModel, Extra, ValidationError
from utils import *

config_path = PATH / "data" / "config.json"

# 模拟设备设置
class DeviceConfig(BaseModel, extra=Extra.ignore):
    USER_AGENT_MOBILE: str = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.25.1"
    """移动端 User-Agent"""
    USER_AGENT_PC: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
    """桌面端 User-Agent"""
    X_RPC_DEVICE_MODEL: str = "OS X 10.15.7"
    """Headers所用的 x-rpc-device_model"""
    X_RPC_DEVICE_NAME: str = "Microsoft Edge 103.0.1264.62"
    """Headers所用的 x-rpc-device_name"""
    UA: str = "\".Not/A)Brand\";v=\"99\", \"Microsoft Edge\";v=\"103\", \"Chromium\";v=\"103\""
    """Headers所用的 sec-ch-ua"""

class Config(BaseModel, extra=Extra.ignore):
    ENCODING: bool = "utf-8"
    MAX_USER: int = 10
    LOG_HEAD: str = "mysTool: "

    device: DeviceConfig = DeviceConfig()


driver = nonebot.get_driver()
global_config = driver.config
mysTool_config: Config = Config()


@driver.on_startup
def check_config():
    global mysTool_config

    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        mysTool_config = Config()
        logger.warning(mysTool_config.LOG_HEAD + "配置文件不存在，将重新生成配置文件...")
    else:
        with config_path.open("r", encoding=mysTool_config.ENCODING) as fp:
            data = json.load(fp)
        try:
            mysTool_config = Config.parse_obj({**global_config.dict(), **data})
        except ValidationError:
            mysTool_config = Config()
            logger.warning(mysTool_config.LOG_HEAD + "配置文件格式错误，将重新生成配置文件...")

    with config_path.open("w", encoding=mysTool_config.ENCODING) as fp:
        json.dump(mysTool_config.dict(), fp, indent=4, ensure_ascii=False)
