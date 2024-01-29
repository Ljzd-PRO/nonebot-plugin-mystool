from typing import Union, Optional, Dict, TYPE_CHECKING

from nonebot.log import logger
from pydantic import BaseSettings

from ..._version import __version__
from ...model.common import data_path
from ...model.upgrade.configV2 import Preference, SaltConfig, DeviceConfig, GoodListImageConfig, PluginConfig, \
    plugin_config_path, \
    PluginEnv
from ...model.upgrade.dataV2 import UserData, UserAccount, PluginData, plugin_data_path

if TYPE_CHECKING:
    IntStr = Union[int, str]

__all__ = ["plugin_data_path_v1", "PluginDataV1", "upgrade_plugin_data"]
plugin_data_path_v1 = data_path / "plugin_data.json"


class PluginDataV1(BaseSettings):
    version: str = __version__
    """创建插件数据文件时的版本号"""
    preference: Preference = Preference()
    """偏好设置"""
    salt_config: SaltConfig = SaltConfig()
    """生成Headers - DS所用salt值"""
    device_config: DeviceConfig = DeviceConfig()
    """设备信息"""
    good_list_image_config: GoodListImageConfig = GoodListImageConfig()
    """商品列表输出图片设置"""
    user_bind: Optional[Dict[str, str]] = {}
    '''不同NoneBot适配器平台的用户数据绑定关系（如QQ聊天和QQ频道）(空用户数据:被绑定用户数据)'''
    users: Dict[str, UserData] = {}
    '''所有用户数据'''

    class Config:
        json_encoders = UserAccount.Config.json_encoders


def upgrade_plugin_data():
    if plugin_data_path_v1.exists() and plugin_data_path_v1.is_file():
        logger.warning("发现V1旧版插件数据文件（包含配置和插件数据），正在升级")
        plugin_data_v1 = PluginDataV1.parse_file(plugin_data_path_v1, encoding="utf-8")

        plugin_config_v2 = PluginConfig()
        plugin_config_v2.preference = plugin_data_v1.preference
        plugin_config_v2.good_list_image_config = plugin_data_v1.good_list_image_config
        logger.success("成功提取V1旧版插件数据文件中的 PluginConfig")

        plugin_env = PluginEnv()
        plugin_env.salt_config = plugin_data_v1.salt_config
        plugin_env.device_config = plugin_data_v1.device_config
        logger.success("成功提取V1旧版插件数据文件中的 PluginEnv")

        plugin_data_v2 = PluginData()
        plugin_data_v2.user_bind = plugin_data_v1.user_bind
        plugin_data_v2.users = plugin_data_v1.users
        logger.success("成功提取V1旧版插件数据文件中的 PluginData")

        plugin_env_text = ""
        plugin_env_text += "\n".join(
            map(
                lambda x: f"{plugin_env.Config.env_prefix.upper()}"
                          "SALT_CONFIG"
                          f"__{x}"
                          f"={plugin_env.salt_config.__getattribute__(x)}",
                plugin_env.salt_config.__fields__.keys()
            )
        )
        plugin_env_text += "\n"
        plugin_env_text += "\n".join(
            map(
                lambda x: f"{plugin_env.Config.env_prefix.upper()}"
                          "DEVICE_CONFIG"
                          f"__{x}"
                          f"={plugin_env.device_config.__getattribute__(x)}",
                plugin_env.device_config.__fields__.keys()
            )
        )
        logger.warning(
            f"PluginEnv 会从 nonebot 项目目录下读取 {plugin_env.Config.env_file} 文件，"
            "为了防止影响到其他配置，转换后的环境变量将直接输出，"
            f"如果需要请手动复制并粘贴至 {plugin_env.Config.env_file} 文件\n{plugin_env_text}"
        )

        # 备份V2配置文件
        for path in plugin_config_path, plugin_data_path:
            if path.exists() and path.is_file():
                backup_path = path.parent / f"{path.name}.bak"
                path.rename(backup_path)
                logger.warning(f"已存在的V2版本文件已备份至 {backup_path}")

        write_success = True

        try:
            str_data = plugin_config_v2.json(indent=4)
            with open(plugin_config_path, "w", encoding="utf-8") as f:
                f.write(str_data)
        except (AttributeError, TypeError, ValueError, PermissionError):
            logger.exception(f"创建转换后的插件配置文件失败，请检查是否有权限读取和写入 {plugin_config_path}")
            write_success = False

        try:
            str_data = plugin_data_v2.json(indent=4)
            with open(plugin_data_path, "w", encoding="utf-8") as f:
                f.write(str_data)
        except (AttributeError, TypeError, ValueError, PermissionError):
            logger.exception(f"创建转换后的插件数据文件失败，请检查是否有权限读取和写入 {plugin_config_path}")
            write_success = False

        if write_success:
            backup_path = plugin_data_path_v1.parent / f"{plugin_data_path_v1.name}.bak"
            plugin_data_path_v1.rename(backup_path)
            logger.warning(f"原先的V1版本插件数据文件已备份至 {backup_path}")
