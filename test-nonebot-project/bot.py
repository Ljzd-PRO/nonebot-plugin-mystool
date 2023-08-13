import nonebot

nonebot.init()

driver = nonebot.get_driver()

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
