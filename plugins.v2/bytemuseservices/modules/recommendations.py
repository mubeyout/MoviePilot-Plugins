"""
推荐模块
提供推荐内容探索服务
使用 ByteMuse API 作为数据源
"""
from typing import List, Dict, Any
from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from cachetools import cached, TTLCache

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
            "path": "/bytemuse_recommendations",
            "endpoint": recommendations,
            "methods": ["GET"],
            "summary": "ByteMuse 推荐",
            "description": "获取推荐内容",
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
        mediaid_prefix="bytemuse_recommend",
        media_id=media_id,
        imdb_id=f"bytemuse_recommend:{movie.code}" if movie.code else f"bytemuse_recommend:{media_id}",  # 用于订阅识别
        poster_path=movie.poster_url or movie.cover_url or movie.thumb_url or "",
        vote_average=movie.score,
        year=movie.release_date[:4] if movie.release_date else None,
        overview=movie.summary or "",
        studio=movie.studio or movie.publisher or "",
    )


def recommendations(
    category: str = "all",
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取推荐内容

    :param category: 分类 (all/high_rated/popular/trending)
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    client = ByteMuseApiClient(
        base_url=_bytemuse_base_url,
        username=_bytemuse_username,
        password=_bytemuse_password,
    )

    # 分类映射
    category_map = {
        "all": "all",
        "high_rated": "high_rated",
        "popular": "popular",
        "trending": "trending",
    }
    api_category = category_map.get(category, "all")

    try:
        # 使用 ByteMuse API 获取推荐内容
        logger.debug(f"获取推荐内容: category={api_category}, page={page}, count={count}")
        movies = client.get_recommend(category=api_category, page=page, page_size=count)

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

        logger.warning(f"未获取到推荐内容: movies is {movies}")
        return []

    except Exception as err:
        logger.error(f"获取推荐内容失败: {str(err)}")
        return []


def recommendations_filter_ui() -> List[dict]:
    """
    推荐过滤参数UI配置
    """
    category_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": text,
        }
        for value, text in [
            ("all", "全部"),
            ("high_rated", "高分"),
            ("popular", "热门"),
            ("trending", "趋势"),
        ]
    ]

    return [
        {
            "component": "div",
            "props": {"class": "flex justify-start items-center"},
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "推荐分类"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "category"},
                    "content": category_ui,
                },
            ],
        },
    ]


def discover_source(master_plugin, event_data):
    """注册推荐探索源"""
    recommendations_source = DiscoverMediaSource(
        name="推荐",
        mediaid_prefix="bytemuse_recommend",
        api_path=f"plugin/ByteMuseServices/bytemuse_recommendations?apikey={settings.API_TOKEN}",
        filter_params={
            "category": "all",
            "page": 1,
            "count": 20,
        },
        filter_ui=recommendations_filter_ui(),
        depends={},
    )

    if not event_data.extra_sources:
        event_data.extra_sources = [recommendations_source]
    else:
        event_data.extra_sources.append(recommendations_source)
