from typing import Dict, Type, Optional

from nonebot.internal.matcher import Matcher

from ..model import CommandUsage

__all__ = ["CommandRegistry"]


class CommandRegistry:
    _command_to_usage: Dict[Type[Matcher], CommandUsage] = {}

    @classmethod
    def get_commands_usage_mapping(cls) -> Dict[Type[Matcher], CommandUsage]:
        return cls._command_to_usage.copy()

    @classmethod
    def set_usage(cls, command: Type[Matcher], usage: CommandUsage) -> None:
        cls._command_to_usage[command] = usage

    @classmethod
    def get_usage(cls, command: Type[Matcher]) -> Optional[CommandUsage]:
        return cls._command_to_usage.get(command)
