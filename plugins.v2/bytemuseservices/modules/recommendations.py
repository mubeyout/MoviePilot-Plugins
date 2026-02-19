"""
推荐模块
提供推荐内容探索服务
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
            "path": "/bytemuse_recommendations",
            "endpoint": recommendations,
            "methods": ["GET"],
            "summary": "ByteMuse 推荐",
            "description": "获取推荐内容",
        },
    ]


# 精选推荐番号列表
_RECOMMENDED_CODES = {
    "all": [
        # S1 精选
        "SSIS-001", "SSIS-100", "SSIS-200", "SSIS-300", "SSIS-400",
        "IPX-001", "IPX-100", "IPX-200", "IPX-300",
        # Moodyz 精选
        "MIDE-001", "MIDE-100", "MIDE-200", "MIDE-300",
        "MIAB-001", "MIAB-100", "MIAB-200",
        # Premium 精选
        "PRED-001", "PRED-100", "PRED-200", "PRED-300",
        # IdeaPocket 精选
        "IPZZ-001", "IPZZ-100", "IPZZ-200",
    ],
    "high_rated": [
        # 高分作品
        "SSIS-391", "SSIS-453", "SSIS-542",
        "MIDV-001", "MIDV-100",
        "PRED-200", "PRED-300",
    ],
    "popular": [
        # 热门作品
        "SSIS-001", "IPX-292", "MIDE-479",
        "PRED-100", "SSIS-495",
    ],
    "trending": [
        # 趋势作品
        "SSIS-800", "IPX-900", "MIDE-800",
        "PRED-600", "IPZZ-300",
    ],
}


def _jav_to_media(jav_data: Any) -> MediaInfo:
    """
    将 ThePornDB JAV 数据转换为 MediaInfo

    :param jav_data: ThePornDB JAV 场景或详情数据
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
    if external_id and external_id not in title:
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
        if actor_names:
            title = f"{title} ({', '.join(actor_names[:3])})"

    # 提取厂牌信息
    site = data.get("site", {})
    studio_name = ""
    if isinstance(site, dict):
        studio_name = site.get("name", "")

    return MediaInfo(
        type="电影",
        title=title,
        mediaid_prefix="theporndb",
        media_id=data.get("id") or data.get("uuid") or data.get("external_id", ""),
        poster_path=poster_url,
        vote_average=None,
        year=data.get("date", "")[:4] if data.get("date") else None,
        overview=data.get("description", ""),
        studio=studio_name,
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
    client = ThePornDBApiClient(api_token=_theporndb_api_token)

    # 获取该分类的推荐番号列表
    codes = _RECOMMENDED_CODES.get(category, _RECOMMENDED_CODES["all"])

    try:
        results = []

        # 计算分页
        start_idx = (page - 1) * count
        end_idx = start_idx + count

        # 获取对应页码的番号
        paginated_codes = codes[start_idx:end_idx]

        # 搜索每个番号
        for code in paginated_codes:
            jav_results = client.search_jav(code)
            if jav_results:
                for jav in jav_results:
                    identifier = jav.slug if hasattr(jav, 'slug') and jav.slug else str(jav.id)
                    detail = client.get_jav_detail(identifier)
                    if detail:
                        results.append(_jav_to_media(detail))
                        break  # 只取第一个结果

        return results

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
        name="ByteMuse推荐",
        mediaid_prefix="theporndb_rec",
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
