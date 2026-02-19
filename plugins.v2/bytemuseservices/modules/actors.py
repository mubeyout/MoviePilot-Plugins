"""
演员模块
提供订阅中/热门演员探索服务
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
            "path": "/bytemuse_actors_subscribed",
            "endpoint": actors_subscribed,
            "methods": ["GET"],
            "summary": "ByteMuse 订阅演员",
            "description": "获取订阅中的演员作品",
        },
        {
            "path": "/bytemuse_actors_hot",
            "endpoint": actors_hot,
            "methods": ["GET"],
            "summary": "ByteMuse 热门演员",
            "description": "获取热门演员列表",
        },
    ]


# 热门演员列表（可配置）
_HOT_ACTORS = [
    "三上悠亜", "Julia", "波多野結衣", "深田えいみ",
    "河北彩花", "架乃由良", "七沢みあ", "楓カレン",
    "伊藤舞雪", "美乃すずめ", "小島みなみ", "星宮一花",
    "天使もえ", "乙都さきの", "新有菜", "夏希まろん",
    "紗倉まな", "朝比奈なつせ", "枢木あおい", "山手よしき",
]


def _jav_to_media(jav_data: Any, actor_name: str = None) -> MediaInfo:
    """
    将 ThePornDB JAV 数据转换为 MediaInfo

    :param jav_data: ThePornDB JAV 场景或详情数据
    :param actor_name: 演员名称（可选）
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
        if actor_names and not actor_name:
            title = f"{title} ({', '.join(actor_names[:3])})"

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


def actors_subscribed(
    actor_name: str = None,
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取订阅演员作品

    :param actor_name: 演员名称（可选，指定演员时只返回该演员作品）
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    client = ThePornDBApiClient(api_token=_theporndb_api_token)

    def __actor_to_media(name: str) -> MediaInfo:
        """将演员名称转换为 MediaInfo"""
        return MediaInfo(
            type="电视剧",
            title=name,
            mediaid_prefix="theporndb_actor",
            media_id=str(hash(name)),
            poster_path="",
            vote_average=None,
        )

    try:
        if actor_name:
            # 使用 ThePornDB 搜索演员作品
            # 通过搜索番号模式来查找演员作品
            results = []
            # 尝试多种搜索方式
            search_queries = [
                actor_name,
                f"{actor_name} *",
            ]

            for query in search_queries:
                jav_results = client.search_jav(query, page=page)
                if jav_results:
                    # 获取详情
                    for jav in jav_results[:count]:
                        identifier = jav.slug if hasattr(jav, 'slug') and jav.slug else str(jav.id)
                        detail = client.get_jav_detail(identifier)
                        if detail:
                            results.append(_jav_to_media(detail, actor_name))
                if results:
                    break

            return results[:count]
        else:
            # 返回订阅演员列表（使用预设的热门演员列表）
            actors_list = _HOT_ACTORS

            # 分页
            start_idx = (page - 1) * count
            end_idx = start_idx + count
            paginated_actors = actors_list[start_idx:end_idx]

            return [__actor_to_media(actor) for actor in paginated_actors]

    except Exception as err:
        logger.error(f"获取订阅演员作品失败: {str(err)}")
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
    def __actor_to_media(name: str) -> MediaInfo:
        """将演员名称转换为 MediaInfo"""
        return MediaInfo(
            type="电视剧",
            title=name,
            mediaid_prefix="theporndb_actor",
            media_id=str(hash(name)),
            poster_path="",
            vote_average=None,
        )

    try:
        # 使用预设的热门演员列表
        actors_list = _HOT_ACTORS

        # 分页
        start_idx = (page - 1) * count
        end_idx = start_idx + count
        paginated_actors = actors_list[start_idx:end_idx]

        return [__actor_to_media(actor) for actor in paginated_actors]

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
        name="ByteMuse演员",
        mediaid_prefix="theporndb_actor",
        api_path=f"plugin/ByteMuseServices/bytemuse_actors_subscribed?apikey={settings.API_TOKEN}",
        filter_params={
            "actor_name": None,
            "actor_type": "subscribed",
            "page": 1,
            "count": 20,
        },
        filter_ui=actors_filter_ui(),
        depends={
            "actor_name": ["actor_type"],
        },
    )

    if not event_data.extra_sources:
        event_data.extra_sources = [actor_source]
    else:
        event_data.extra_sources.append(actor_source)
