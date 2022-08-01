import httpx
import traceback
from nonebot.log import logger

ACT_ID = {
    "ys": "e202009291139501"
}
URL_REWARD = {
    "ys": "https://api-takumi.mihoyo.com/event/bbs_sign_reward/home?act_id={}".format(ACT_ID["ys"])
}
HEADERS = {
    ...
}

async def reward(game:str) -> list[dict]:
    res = await httpx.get(URL_REWARD[game], headers=HEADERS)
    try:
        return res.json()["data"]["awards"]
    except KeyError:
        print("服务器没有正确返回")
        logger.debug("mys_tool: " + traceback.format_exc())
    except:
        print("网络连接失败")
        logger.debug("mys_tool: " + traceback.format_exc())

async def sign(game:str):
    ...
