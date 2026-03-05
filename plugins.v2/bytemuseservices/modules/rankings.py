"""
榜单模块
提供 JavDB 热门榜和 JavLibrary 想要榜探索服务
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
            "path": "/bytemuse_rankings",
            "endpoint": rankings,
            "methods": ["GET"],
            "summary": "ByteMuse 榜单",
            "description": "榜单探索服务（JavDB日榜/周榜/月榜，JavLibrary想要榜）",
        },
    ]


def rankings(
    ranking_source: str = "javdb",
    period: str = "daily",
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    统一的榜单API端点

    :param ranking_source: 榜单来源 (javdb, javlibrary)
    :param period: JavDB周期 (daily, weekly, monthly) - 仅当ranking_source为javdb时有效
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    # 根据ranking_source确定实际榜单类型
    if ranking_source == "javlibrary":
        return rankings_javlibrary(page=page, count=count)
    elif ranking_source == "javdb":
        # 根据period选择JavDB榜单类型
        if period == "weekly":
            return rankings_javdb_weekly(page=page, count=count)
        elif period == "monthly":
            return rankings_javdb_monthly(page=page, count=count)
        else:  # daily
            return rankings_javdb_daily(page=page, count=count)
    else:
        # 兼容旧的直接调用方式
        if ranking_source == "javdb_weekly":
            return rankings_javdb_weekly(page=page, count=count)
        elif ranking_source == "javdb_monthly":
            return rankings_javdb_monthly(page=page, count=count)
        elif ranking_source == "javlibrary":
            return rankings_javlibrary(page=page, count=count)
        else:  # javdb_daily or default
            return rankings_javdb_daily(page=page, count=count)


def _item_to_media(item: Dict[str, Any], rank: int = None) -> MediaInfo:
    """
    将榜单项数据转换为 MediaInfo

    :param item: 榜单项数据
    :param rank: 排名（可选）
    :return: MediaInfo 对象
    """
    # 提取番号
    code = item.get("code", "")
    external_id = item.get("external_id", "") or code

    # 标题只显示番号
    title = external_id if external_id else "未知番号"

    # 确保 media_id 永远不为空
    media_id = external_id or code or item.get("id", "") or title or f"unknown_{id(item)}"

    # 提取图片URL
    poster_url = (item.get("poster", "") or
                  item.get("cover", "") or
                  item.get("image", "") or
                  item.get("thumb", ""))

    # 厂牌信息
    studio = item.get("studio", "") or item.get("site", {}).get("name", "") if isinstance(item.get("site"), dict) else ""

    return MediaInfo(
        type="电影",
        title=title,
        mediaid_prefix="bytemuse_rank",
        media_id=media_id,
        imdb_id=f"bytemuse_rank:{external_id}" if external_id else f"bytemuse_rank:{media_id}",  # 用于订阅识别
        poster_path=poster_url,
        vote_average=item.get("score"),
        year=item.get("date", "")[:4] if item.get("date") else None,
        overview=item.get("description", "") or item.get("summary", ""),
        studio=studio,
    )


def _fetch_ranking_data(rank_type: str, page: int, count: int) -> List[MediaInfo]:
    """
    获取榜单数据

    :param rank_type: 榜单类型 (daily/weekly/monthly/javlibrary)
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
        # 使用 ByteMuse API 获取榜单
        ranking_data = client.get_ranks(rank_type=rank_type, limit=count)

        if ranking_data:
            # 计算分页
            start_idx = (page - 1) * count
            end_idx = start_idx + count
            paginated_data = ranking_data[start_idx:end_idx]

            return [_item_to_media(item, rank=start_idx + i + 1) for i, item in enumerate(paginated_data)]

        return []

    except Exception as err:
        logger.error(f"获取榜单失败: {str(err)}")
        return []


def rankings_javdb_daily(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取 JavDB 日榜

    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    try:
        return _fetch_ranking_data("daily", page, count)
    except Exception as err:
        logger.error(f"获取 JavDB 日榜失败: {str(err)}")
        return []


def rankings_javdb_weekly(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取 JavDB 周榜

    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    try:
        return _fetch_ranking_data("weekly", page, count)
    except Exception as err:
        logger.error(f"获取 JavDB 周榜失败: {str(err)}")
        return []


def rankings_javdb_monthly(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取 JavDB 月榜

    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    try:
        return _fetch_ranking_data("monthly", page, count)
    except Exception as err:
        logger.error(f"获取 JavDB 月榜失败: {str(err)}")
        return []


def rankings_javlibrary(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取 JavLibrary 想要榜

    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    try:
        return _fetch_ranking_data("javlibrary", page, count)
    except Exception as err:
        logger.error(f"获取 JavLibrary 想要榜失败: {str(err)}")
        return []


def rankings_filter_ui() -> List[dict]:
    """
    榜单过滤参数UI配置
    """
    source_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": text,
        }
        for value, text in [
            ("javdb", "JavDB"),
            ("javlibrary", "JavLibrary"),
        ]
    ]

    period_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": text,
        }
        for value, text in [
            ("daily", "日榜"),
            ("weekly", "周榜"),
            ("monthly", "月榜"),
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
                    "content": [{"component": "VLabel", "text": "榜单来源"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "ranking_source"},
                    "content": source_ui,
                },
            ],
        },
        {
            "component": "div",
            "props": {
                "class": "flex justify-start items-center",
                "show": "{{ranking_source == 'javdb'}}",
            },
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "周期"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "period"},
                    "content": period_ui,
                },
            ],
        },
    ]


def discover_source(master_plugin, event_data):
    """注册榜单探索源"""
    rankings_source = DiscoverMediaSource(
        name="榜单",
        mediaid_prefix="bytemuse_rank",
        api_path=f"plugin/ByteMuseServices/bytemuse_rankings?apikey={settings.API_TOKEN}",
        filter_params={
            "ranking_source": "javdb",
            "period": "daily",
            "page": 1,
            "count": 20,
        },
        filter_ui=rankings_filter_ui(),
    )

    if not event_data.extra_sources:
        event_data.extra_sources = [rankings_source]
    else:
        event_data.extra_sources.append(rankings_source)
