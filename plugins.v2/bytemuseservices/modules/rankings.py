"""
榜单模块
提供 JavDB 热门榜和 JavLibrary 想要榜探索服务
使用 ThePornDB API 作为数据源
"""
from typing import List, Dict, Any
from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from cachetools import cached, TTLCache

# ThePornDB API 客户端
from ..theporndb_api import ThePornDBApiClient

# 全局配置
_theporndb_api_token = "rlsxVnIRsrxAw4JH7UTIzLQQWQQKfcRpEpu4qehk0e4b96da"


def get_api(master_plugin):
    """获取API列表"""
    global _theporndb_api_token
    _theporndb_api_token = master_plugin.theporndb_api_token
    return [
        {
            "path": "/bytemuse_rankings_javdb_daily",
            "endpoint": rankings_javdb_daily,
            "methods": ["GET"],
            "summary": "ByteMuse JavDB 日榜",
            "description": "获取 JavDB 日榜",
        },
        {
            "path": "/bytemuse_rankings_javdb_weekly",
            "endpoint": rankings_javdb_weekly,
            "methods": ["GET"],
            "summary": "ByteMuse JavDB 周榜",
            "description": "获取 JavDB 周榜",
        },
        {
            "path": "/bytemuse_rankings_javdb_monthly",
            "endpoint": rankings_javdb_monthly,
            "methods": ["GET"],
            "summary": "ByteMuse JavDB 月榜",
            "description": "获取 JavDB 月榜",
        },
        {
            "path": "/bytemuse_rankings_javlibrary",
            "endpoint": rankings_javlibrary,
            "methods": ["GET"],
            "summary": "ByteMuse JavLibrary 想要榜",
            "description": "获取 JavLibrary 想要榜",
        },
    ]


# JavDB 榜单番号（模拟榜单数据）
_JAVDB_RANKINGS = {
    "daily": [
        "SSIS-800", "IPX-900", "MIDE-800", "PRED-600", "IPZZ-300",
        "SSIS-801", "IPX-901", "MIDE-801", "PRED-601", "IPZZ-301",
        "SSIS-802", "IPX-902", "MIDE-802", "PRED-602", "IPZZ-302",
        "SSIS-803", "IPX-903", "MIDE-803", "PRED-603", "IPZZ-303",
        "SSIS-804", "IPX-904", "MIDE-804", "PRED-604", "IPZZ-304",
    ],
    "weekly": [
        "SSIS-750", "IPX-850", "MIDE-750", "PRED-550", "IPZZ-250",
        "SSIS-751", "IPX-851", "MIDE-751", "PRED-551", "IPZZ-251",
        "SSIS-752", "IPX-852", "MIDE-752", "PRED-552", "IPZZ-252",
        "SSIS-753", "IPX-853", "MIDE-753", "PRED-553", "IPZZ-253",
        "SSIS-754", "IPX-854", "MIDE-754", "PRED-554", "IPZZ-254",
    ],
    "monthly": [
        "SSIS-700", "IPX-800", "MIDE-700", "PRED-500", "IPZZ-200",
        "SSIS-701", "IPX-801", "MIDE-701", "PRED-501", "IPZZ-201",
        "SSIS-702", "IPX-802", "MIDE-702", "PRED-502", "IPZZ-202",
        "SSIS-703", "IPX-803", "MIDE-703", "PRED-503", "IPZZ-203",
        "SSIS-704", "IPX-804", "MIDE-704", "PRED-504", "IPZZ-204",
    ],
}

# JavLibrary 想要榜番号（模拟榜单数据）
_JAVLIBRARY_RANKINGS = [
    "SSIS-391", "SSIS-453", "SSIS-542",
    "MIDV-001", "MIDV-100", "MIDV-200",
    "PRED-200", "PRED-300", "PRED-400",
    "IPX-292", "IPX-400", "IPX-500",
    "JUL-100", "JUL-200", "JUL-300",
    "STARS-100", "STARS-200", "STARS-300",
    "WANZ-800", "WANZ-900", "WANZ-1000",
    "ATID-400", "ATID-500", "ATID-600",
    "HNDR-500", "HNDR-600", "HNDR-700",
]


def _jav_to_media(jav_data: Any, rank: int = None) -> MediaInfo:
    """
    将 ThePornDB JAV 数据转换为 MediaInfo

    :param jav_data: ThePornDB JAV 场景或详情数据
    :param rank: 排名（可选）
    :return: MediaInfo 对象
    """
    # 处理不同类型的数据结构
    if hasattr(jav_data, 'model_dump'):
        data = jav_data.model_dump()
    elif isinstance(jav_data, dict):
        data = jav_data
    else:
        data = {}

    # 提取标题
    title = data.get("title", "")
    external_id = data.get("external_id", "")

    # 如果有排名，添加到标题
    if rank:
        title = f"#{rank} {external_id} {title}".strip()
    elif external_id and external_id not in title:
        title = f"{external_id} {title}".strip()

    # 提取图片URL（优先使用 poster，然后 background）
    poster_url = ""
    if data.get("poster"):
        poster_url = data.get("poster", "")
    elif data.get("posters"):
        posters = data.get("posters", {})
        if isinstance(posters, dict):
            poster_url = posters.get("full") or posters.get("large") or posters.get("medium") or ""
    elif data.get("background"):
        background = data.get("background", {})
        if isinstance(background, dict):
            poster_url = background.get("full") or background.get("large") or background.get("medium") or ""

    # 如果有演员信息，添加到标题
    performers = data.get("performers", [])
    actor_names = []
    if performers:
        for p in performers:
            if isinstance(p, dict):
                name = p.get("name") or p.get("parent", {}).get("name") if p.get("parent") else ""
                if name:
                    actor_names.append(name)

    return MediaInfo(
        type="电影",
        title=title,
        mediaid_prefix="theporndb",
        media_id=data.get("id") or data.get("uuid") or data.get("external_id", ""),
        poster_path=poster_url,
        vote_average=None,
        year=data.get("date", "")[:4] if data.get("date") else None,
        overview=data.get("description", ""),
    )


def _fetch_ranking_data(codes: List[str], page: int, count: int) -> List[MediaInfo]:
    """
    获取榜单数据

    :param codes: 番号列表
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    client = ThePornDBApiClient(api_token=_theporndb_api_token)
    results = []

    # 计算分页
    start_idx = (page - 1) * count
    end_idx = start_idx + count
    paginated_codes = codes[start_idx:end_idx]

    # 搜索每个番号
    for i, code in enumerate(paginated_codes):
        rank = start_idx + i + 1  # 计算排名
        try:
            jav_results = client.search_jav(code)
            if jav_results:
                for jav in jav_results:
                    identifier = jav.slug if hasattr(jav, 'slug') and jav.slug else str(jav.id)
                    detail = client.get_jav_detail(identifier)
                    if detail:
                        results.append(_jav_to_media(detail, rank=rank))
                        break
        except Exception as e:
            logger.debug(f"获取榜单项 {code} 失败: {str(e)}")
            continue

    return results


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
        return _fetch_ranking_data(_JAVDB_RANKINGS["daily"], page, count)
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
        return _fetch_ranking_data(_JAVDB_RANKINGS["weekly"], page, count)
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
        return _fetch_ranking_data(_JAVDB_RANKINGS["monthly"], page, count)
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
        return _fetch_ranking_data(_JAVLIBRARY_RANKINGS, page, count)
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
    javdb_daily_source = DiscoverMediaSource(
        name="JavDB日榜",
        mediaid_prefix="javdb_daily",
        api_path=f"plugin/ByteMuseServices/bytemuse_rankings_javdb_daily?apikey={settings.API_TOKEN}",
        filter_params={
            "page": 1,
            "count": 20,
        },
        filter_ui=rankings_filter_ui(),
        depends={},
    )

    javdb_weekly_source = DiscoverMediaSource(
        name="JavDB周榜",
        mediaid_prefix="javdb_weekly",
        api_path=f"plugin/ByteMuseServices/bytemuse_rankings_javdb_weekly?apikey={settings.API_TOKEN}",
        filter_params={
            "page": 1,
            "count": 20,
        },
        filter_ui=rankings_filter_ui(),
        depends={},
    )

    javdb_monthly_source = DiscoverMediaSource(
        name="JavDB月榜",
        mediaid_prefix="javdb_monthly",
        api_path=f"plugin/ByteMuseServices/bytemuse_rankings_javdb_monthly?apikey={settings.API_TOKEN}",
        filter_params={
            "page": 1,
            "count": 20,
        },
        filter_ui=rankings_filter_ui(),
        depends={},
    )

    javlibrary_source = DiscoverMediaSource(
        name="JavLibrary想要榜",
        mediaid_prefix="javlibrary",
        api_path=f"plugin/ByteMuseServices/bytemuse_rankings_javlibrary?apikey={settings.API_TOKEN}",
        filter_params={
            "page": 1,
            "count": 20,
        },
        filter_ui=rankings_filter_ui(),
        depends={},
    )

    if not event_data.extra_sources:
        event_data.extra_sources = [
            javdb_daily_source,
            javdb_weekly_source,
            javdb_monthly_source,
            javlibrary_source,
        ]
    else:
        event_data.extra_sources.extend([
            javdb_daily_source,
            javdb_weekly_source,
            javdb_monthly_source,
            javlibrary_source,
        ])
