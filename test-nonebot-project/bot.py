import nonebot

nonebot.init()

driver = nonebot.get_driver()

nonebot.load_from_toml("pyproject.toml")

nonebot.run()
