import json
from json import JSONDecodeError
from typing import Union, Optional, Any, Dict, TYPE_CHECKING, AbstractSet, \
    Mapping

from loguru import logger
from pydantic import BaseModel, ValidationError

from . import user_data, data_path
from .._version import __version__
from ..model.user_data import UserData, UserAccount

__all__ = ["PluginData", "PluginDataManager"]

plugin_data_path = data_path / "dataV2.json"

if TYPE_CHECKING:
    IntStr = Union[int, str]
    DictStrAny = Dict[str, Any]
    AbstractSetIntStr = AbstractSet[IntStr]
    MappingIntStrAny = Mapping[IntStr, Any]


class PluginData(BaseModel):
    version: str = __version__
    """创建插件数据文件时的版本号"""
    user_bind: Optional[Dict[str, str]] = {}
    '''不同NoneBot适配器平台的用户数据绑定关系（如QQ聊天和QQ频道）(空用户数据:被绑定用户数据)'''
    users: Dict[str, UserData] = {}
    '''所有用户数据'''

    def do_user_bind(self, src: str = None, dst: str = None, write: bool = False):
        """
        执行用户数据绑定同步，将src指向dst的用户数据，即src处的数据将会被dst处的数据对象替换

        :param src: 源用户数据，为空则读取 self.user_bind 并执行全部绑定
        :param dst: 目标用户数据，为空则读取 self.user_bind 并执行全部绑定
        :param write: 是否写入插件数据文件
        """
        if None in [src, dst]:
            for x, y in self.user_bind.items():
                try:
                    self.users[x] = self.users[y]
                except KeyError:
                    logger.error(f"用户数据绑定失败，目标用户 {y} 不存在")
        else:
            try:
                self.user_bind[src] = dst
                self.users[src] = self.users[dst]
            except KeyError:
                logger.error(f"用户数据绑定失败，目标用户 {dst} 不存在")
            else:
                if write:
                    PluginDataManager.write_plugin_data()

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.do_user_bind(write=True)

    class Config:
        json_encoders = UserAccount.Config.json_encoders


class PluginDataManager:
    plugin_data: Optional[PluginData] = None
    """加载出的插件数据对象"""

    @classmethod
    def load_plugin_data(cls):
        """
        加载插件数据文件
        """
        if plugin_data_path.exists() and plugin_data_path.is_file():
            try:
                with open(plugin_data_path, "r") as f:
                    plugin_data_dict = json.load(f)
                # 读取完整的插件数据
                cls.plugin_data = PluginData.parse_obj(plugin_data_dict)
            except (ValidationError, JSONDecodeError):
                logger.exception(f"读取插件数据文件失败，请检查插件数据文件 {plugin_data_path} 格式是否正确")
                raise
            except:
                logger.exception(
                    f"读取插件数据文件失败，请检查插件数据文件 {plugin_data_path} 是否存在且有权限读取和写入")
                raise
        else:
            cls.plugin_data = PluginData()
            try:
                str_data = cls.plugin_data.json(indent=4)
                with open(plugin_data_path, "w", encoding="utf-8") as f:
                    f.write(str_data)
            except (AttributeError, TypeError, ValueError, PermissionError):
                logger.exception(f"创建插件数据文件失败，请检查是否有权限读取和写入 {plugin_data_path}")
                raise
            else:
                logger.info(f"插件数据文件 {plugin_data_path} 不存在，已创建默认插件数据文件。")

    @classmethod
    def write_plugin_data(cls):
        """
        写入插件数据文件

        :return: 是否成功
        """
        try:
            str_data = cls.plugin_data.json(indent=4)
        except (AttributeError, TypeError, ValueError):
            logger.exception("数据对象序列化失败，可能是数据类型错误")
            return False
        else:
            with open(plugin_data_path, "w", encoding="utf-8") as f:
                f.write(str_data)
            return True


PluginDataManager.load_plugin_data()

# 如果插件数据文件加载后，发现有用户没有UUID密钥，进行了生成，则需要保存写入
if user_data._new_uuid_in_init:
    PluginDataManager.write_plugin_data()
