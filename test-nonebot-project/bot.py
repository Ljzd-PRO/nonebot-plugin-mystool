import nonebot

nonebot.init()

driver = nonebot.get_driver()

nonebot.load_from_toml("pyproject.toml")
nonebot.load_plugins("src/plugins/nonebot_plugin_mystool")

if __name__ == "__main__":
    nonebot.run()
