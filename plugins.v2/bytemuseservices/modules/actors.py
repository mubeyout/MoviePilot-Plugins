"""
演员模块
提供订阅中/热门演员探索服务
使用 ByteMuse API 作为数据源
"""
from typing import List, Dict, Any
from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from cachetools import cached, TTLCache

# ByteMuse API 客户端
from ..bytemuse_api import ByteMuseApiClient

# 全局配置
_bytemuse_base_url = "http://10.0.0.1:3750"
_bytemuse_username = "mubey"
_bytemuse_password = "355492"


def get_api(master_plugin):
    """获取API列表"""
    global _bytemuse_base_url, _bytemuse_username, _bytemuse_password
    _bytemuse_base_url = master_plugin.bytemuse_base_url
    _bytemuse_username = master_plugin.bytemuse_username
    _bytemuse_password = master_plugin.bytemuse_password
    return [
        {
            "path": "/bytemuse_actors",
            "endpoint": actors,
            "methods": ["GET"],
            "summary": "ByteMuse 演员",
            "description": "演员探索服务（订阅中/热门）",
        },
    ]


def actors(
    actor_type: str = "subscribed",
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    统一的演员API端点

    :param actor_type: 演员类型 (subscribed=订阅中, hot=热门)
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    if actor_type == "hot":
        return actors_hot(page=page, count=count)
    else:
        return actors_subscribed(page=page, count=count)


def _actor_to_media(actor_data: Dict[str, Any]) -> MediaInfo:
    """将演员数据转换为 MediaInfo"""
    name = actor_data.get("name", "")
    if isinstance(name, list):
        name = name[0] if name else ""

    # API 返回的图片字段是 photo
    poster_path = (actor_data.get("photo", "") or
                   actor_data.get("avatar", "") or
                   actor_data.get("poster", "") or
                   actor_data.get("image", ""))

    return MediaInfo(
        type="电视剧",
        title=name,
        mediaid_prefix="bytemuse_actor",
        media_id=str(hash(name)),
        poster_path=poster_path,
        vote_average=actor_data.get("score"),
    )


def actors_subscribed(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取订阅演员（演员列表）

    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    client = ByteMuseApiClient(
        base_url=_bytemuse_base_url,
        username=_bytemuse_username,
        password=_bytemuse_password,
    )

    try:
        # 使用 ByteMuse API 获取演员列表
        actors_data = client.get_actors(page=page, page_size=count)

        if actors_data:
            return [_actor_to_media(actor) for actor in actors_data]

        return []

    except Exception as err:
        logger.error(f"获取订阅演员失败: {str(err)}")
        return []


def actors_hot(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取热门演员

    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表（演员）
    """
    client = ByteMuseApiClient(
        base_url=_bytemuse_base_url,
        username=_bytemuse_username,
        password=_bytemuse_password,
    )

    try:
        # 使用 ByteMuse API 获取热门演员
        actors_data = client.get_actors_rank(limit=count)

        if actors_data:
            return [_actor_to_media(actor) for actor in actors_data]

        return []

    except Exception as err:
        logger.error(f"获取热门演员失败: {str(err)}")
        return []


def actors_filter_ui() -> List[dict]:
    """
    演员过滤参数UI配置
    """
    return [
        {
            "component": "div",
            "props": {"class": "flex justify-start items-center"},
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "演员类型"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "actor_type"},
                    "content": [
                        {
                            "component": "VChip",
                            "props": {"filter": True, "tile": True, "value": "subscribed"},
                            "text": "订阅中",
                        },
                        {
                            "component": "VChip",
                            "props": {"filter": True, "tile": True, "value": "hot"},
                            "text": "热门",
                        },
                    ],
                },
            ],
        },
    ]


def discover_source(master_plugin, event_data):
    """注册演员探索源"""
    actor_source = DiscoverMediaSource(
        name="演员",
        mediaid_prefix="bytemuse_actor",
        api_path=f"plugin/ByteMuseServices/bytemuse_actors?apikey={settings.API_TOKEN}",
        filter_params={
            "actor_type": "subscribed",
            "page": 1,
            "count": 20,
        },
        filter_ui=actors_filter_ui(),
    )

    if not event_data.extra_sources:
        event_data.extra_sources = [actor_source]
    else:
        event_data.extra_sources.append(actor_source)
