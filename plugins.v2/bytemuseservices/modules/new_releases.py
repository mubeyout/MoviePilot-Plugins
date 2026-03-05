"""
上新模块
提供最新上架作品探索服务
使用 ByteMuse API 作为数据源
"""
from typing import List, Dict, Any
from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from cachetools import cached, TTLCache
from datetime import datetime, timedelta

# ByteMuse API 客户端
from ..bytemuse_api import ByteMuseApiClient
from ..schema import ByteMuseMovie

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
            "path": "/bytemuse_new_releases",
            "endpoint": new_releases,
            "methods": ["GET"],
            "summary": "ByteMuse 最新上架",
            "description": "获取最新上架的作品",
        },
    ]


def _movie_to_media(movie: ByteMuseMovie) -> MediaInfo:
    """
    将 ByteMuseMovie 转换为 MediaInfo

    :param movie: ByteMuseMovie 对象
    :return: MediaInfo 对象
    """
    # 处理标题 - 只显示番号
    title = movie.code or movie.title or ""

    # 确保 media_id 永远不为空
    if movie.code:
        media_id = movie.code
    elif movie.id:
        media_id = f"bytemuse_{movie.id}"
    else:
        media_id = title or f"unknown_{id(movie)}"

    return MediaInfo(
        type="电影",
        title=title,
        mediaid_prefix="bytemuse_new",
        media_id=media_id,
        imdb_id=f"bytemuse_new:{movie.code}" if movie.code else f"bytemuse_new:{media_id}",  # 用于订阅识别
        poster_path=movie.poster_url or movie.cover_url or movie.thumb_url or "",
        vote_average=movie.score,
        year=movie.release_date[:4] if movie.release_date else None,
        overview=movie.summary or "",
        studio=movie.studio or movie.publisher or "",
    )


def new_releases(
    days: int = 7,
    studio: str = None,
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取最新上架作品

    :param days: 天数（暂未使用，API 默认返回今日上新）
    :param studio: 厂牌筛选（暂未使用）
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
        # 使用 ByteMuse API 获取今日上新
        logger.debug(f"获取今日上新: page={page}, count={count}")
        movies = client.get_release_today(page=page, page_size=count)

        logger.debug(f"API返回: movies={movies}, type={type(movies) if movies else 'None'}")

        if movies:
            logger.debug(f"开始转换 {len(movies)} 部电影数据")
            result = []
            for i, movie in enumerate(movies):
                try:
                    media = _movie_to_media(movie)
                    logger.debug(f"电影 {i+1}: code={movie.code}, title={movie.title[:20] if movie.title else 'N/A'}..., media_id={media.media_id}")
                    result.append(media)
                except Exception as e:
                    logger.error(f"转换电影 {i+1} 失败: {str(e)}, movie={movie}")
            return result

        logger.warning(f"未获取到今日上新: movies is {movies}")
        return []

    except Exception as err:
        logger.error(f"获取最新上架作品失败: {str(err)}")
        return []


def new_releases_filter_ui() -> List[dict]:
    """
    新上架过滤参数UI配置
    """
    days_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": text,
        }
        for value, text in [
            ("1", "1天内"),
            ("3", "3天内"),
            ("7", "7天内"),
            ("30", "30天内"),
        ]
    ]

    studio_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": studio},
            "text": studio,
        }
        for studio in ["S1", "IdeaPocket", "Moodyz", "Premium", "DAS", "Madonna", "Honnaka", "Attackers", "Wanz"]
    ]

    return [
        {
            "component": "div",
            "props": {"class": "flex justify-start items-center"},
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "时间范围"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "days"},
                    "content": days_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {"class": "flex justify-start items-center"},
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "厂牌"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "studio"},
                    "content": studio_ui,
                },
            ],
        },
    ]


def discover_source(master_plugin, event_data):
    """注册上新探索源"""
    new_releases_source = DiscoverMediaSource(
        name="上新",
        mediaid_prefix="bytemuse_new",
        api_path=f"plugin/ByteMuseServices/bytemuse_new_releases?apikey={settings.API_TOKEN}",
        filter_params={
            "days": 7,
            "studio": None,
            "page": 1,
            "count": 20,
        },
        filter_ui=new_releases_filter_ui(),
        depends={},
    )

    if not event_data.extra_sources:
        event_data.extra_sources = [new_releases_source]
    else:
        event_data.extra_sources.append(new_releases_source)
