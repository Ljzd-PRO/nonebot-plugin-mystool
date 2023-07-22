"""
### 商品图片生成等
"""
import io
import os
import zipfile
from multiprocessing import Lock
from typing import List

import httpx
from PIL import Image, ImageDraw, ImageFont

from .data_model import Good
from .plugin_data import PluginDataManager, DATA_PATH
from .simple_api import get_good_detail
from .utils import (get_file, logger, get_async_retry)

_conf = PluginDataManager.plugin_data

FONT_URL = os.path.join(
    _conf.preference.github_proxy,
    "https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansHWSC.zip")
TEMP_FONT_PATH = DATA_PATH / "temp" / "font.zip"
FONT_SAVE_PATH = DATA_PATH / "SourceHanSansHWSC-Regular.otf"


async def game_list_to_image(good_list: List[Good], lock: Lock = None, retry: bool = True):
    """
    将商品信息列表转换为图片数据，若返回`None`说明生成失败

    :param good_list: 商品列表数据
    :param lock: 进程同步锁，防止多进程同时在下载字体
    :param retry: 是否允许重试
    """
    # TODO: 暂时会阻塞，目前还找不到更好的解决方案
    #   回调函数是否适用于 NoneBot Matcher 暂不清楚，
    #   若适用则可以传入回调函数而不阻塞主进程
    try:
        if lock is not None:
            lock.acquire()

        font_path = _conf.good_list_image_config.FONT_PATH
        if font_path is None or not os.path.isfile(font_path):
            if os.path.isfile(FONT_SAVE_PATH):
                font_path = FONT_SAVE_PATH
            else:
                logger.warning(
                    f"{_conf.preference.log_head}商品列表图片生成 - 缺少字体，正在从 https://github.com/adobe-fonts/source-han-sans/tree/release "
                    f"下载字体...")
                try:
                    os.makedirs(os.path.dirname(TEMP_FONT_PATH))
                except FileExistsError:
                    pass
                with open(TEMP_FONT_PATH, "wb") as f:
                    content = await get_file(FONT_URL)
                    if content is None:
                        logger.error(
                            f"{_conf.preference.log_head}商品列表图片生成 - 字体下载失败，无法继续生成图片")
                        return None
                    f.write(content)
                with open(TEMP_FONT_PATH, "rb") as f:
                    with zipfile.ZipFile(f) as z:
                        with z.open("OTF/SimplifiedChineseHW/SourceHanSansHWSC-Regular.otf") as zip_font:
                            with open(FONT_SAVE_PATH, "wb") as fp_font:
                                fp_font.write(zip_font.read())
                logger.info(
                    f"{_conf.preference.log_head}商品列表图片生成 - 已完成字体下载 -> {FONT_SAVE_PATH}")
                try:
                    os.remove(TEMP_FONT_PATH)
                except:
                    logger.exception(
                        f"{_conf.preference.log_head}商品列表图片生成 - 无法清理下载的字体压缩包临时文件")
                font_path = FONT_SAVE_PATH

        if lock is not None:
            lock.release()

        font = ImageFont.truetype(
            str(font_path), _conf.good_list_image_config.FONT_SIZE, encoding=_conf.preference.encoding)

        size_y = 0
        '''起始粘贴位置 高'''
        position: List[tuple] = []
        '''预览图粘贴的位置'''
        imgs: List[Image.Image] = []
        '''商品预览图'''

        for good in good_list:
            await get_good_detail(good)
            async for attempt in get_async_retry(retry):
                with attempt:
                    async with httpx.AsyncClient() as client:
                        icon = await client.get(good.icon, timeout=_conf.preference.timeout)
            img = Image.open(io.BytesIO(icon.content))
            # 调整预览图大小
            img = img.resize(_conf.good_list_image_config.ICON_SIZE)
            # 记录预览图粘贴位置
            position.append((0, size_y))
            # 调整下一个粘贴的位置
            size_y += _conf.good_list_image_config.ICON_SIZE[1] + \
                      _conf.good_list_image_config.PADDING_ICON
            imgs.append(img)

        preview = Image.new(
            'RGB', (_conf.good_list_image_config.WIDTH, size_y), (255, 255, 255))

        i = 0
        for img in imgs:
            preview.paste(img, position[i])
            i += 1

        draw_y = _conf.good_list_image_config.PADDING_TEXT_AND_ICON_Y
        '''写入文字的起始位置 高'''
        for good in good_list:
            draw = ImageDraw.Draw(preview)
            # 根据预览图高度来确定写入文字的位置，并调整空间
            draw.text((_conf.good_list_image_config.ICON_SIZE[0] + _conf.good_list_image_config.PADDING_TEXT_AND_ICON_X,
                       draw_y),
                      f"{good.general_name}\n商品ID: {good.goods_id}\n兑换时间: {good.time_text}\n价格: {good.price} 米游币",
                      (0, 0, 0), font)
            draw_y += (_conf.good_list_image_config.ICON_SIZE[1] +
                       _conf.good_list_image_config.PADDING_ICON)

        # 导出
        image_bytes = io.BytesIO()
        preview.save(image_bytes, format="JPEG")
        return image_bytes.getvalue()
    except:
        logger.exception(f"{_conf.preference.log_head}商品列表图片生成 - 无法完成图片生成")
