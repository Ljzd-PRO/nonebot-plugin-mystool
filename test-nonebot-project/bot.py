import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11

from nonebot.adapters.qqguild import Adapter as QQGuild

nonebot.init()

driver = nonebot.get_driver()

driver.register_adapter(OnebotV11)
driver.register_adapter(QQGuild)

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
