"""
上新模块
提供最新上架作品探索服务
使用 ThePornDB API 作为数据源
"""
from typing import List, Dict, Any
from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger
from cachetools import cached, TTLCache
from datetime import datetime, timedelta

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
            "path": "/bytemuse_new_releases",
            "endpoint": new_releases,
            "methods": ["GET"],
            "summary": "ByteMuse 最新上架",
            "description": "获取最新上架的作品",
        },
    ]


# 热门厂牌的最新番号（模拟"最新上架"数据）
# ThePornDB API 没有直接的上新接口，我们通过搜索最近的热门番号来实现
_RECENT_PATTERNS = [
    # S1 最新
    "SSIS", "IPX", "OFKU",
    # IdeaPocket 最新
    "IPX-", "IPZZ-",
    # Moodyz 最新
    "MIDE", "MIAB", "MIMK",
    # Premium 最新
    "PRED", "PFES",
    # DAS 最新
    "DASS", "DAKJ",
    # Madonna 最新
    "JUL", "JUQ",
    # Honnaka 最新
    "HNDR", "HNDV",
    # Attackers 最新
    "ATID", "SSNI",
    # Wanz 最新
    "WANZ",
]


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


def new_releases(
    days: int = 7,
    studio: str = None,
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    获取最新上架作品

    :param days: 天数（1/3/7/30）- 用于生成搜索模式
    :param studio: 厂牌筛选（可选）
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    client = ThePornDBApiClient(api_token=_theporndb_api_token)

    # 厂牌到番号前缀的映射
    studio_prefixes = {
        "S1": ["SSIS", "IPX", "SOAV"],
        "IdeaPocket": ["IPX", "IPZZ"],
        "Moodyz": ["MIDE", "MIAB", "MIMK", "MIAA"],
        "Premium": ["PRED", "PFES", "ABW"],
        "DAS": ["DASS", "DAKJ"],
        "Madonna": ["JUL", "JUQ"],
        "Honnaka": ["HNDR", "HNDV", "HND"],
        "Attackers": ["ATID", "SSNI", "SHKD"],
        "Wanz": ["WANZ", "WAT"],
    }

    try:
        results = []

        # 确定要搜索的番号前缀
        if studio and studio in studio_prefixes:
            prefixes = studio_prefixes[studio]
        else:
            # 使用所有前缀
            prefixes = []
            for studio_prefixes_list in studio_prefixes.values():
                prefixes.extend(studio_prefixes_list)

        # 根据页码计算起始索引
        start_idx = (page - 1) * count
        end_idx = start_idx + count

        # 搜索每个前缀的最新番号
        searched = 0
        for i, prefix in enumerate(prefixes):
            if searched >= end_idx:
                break

            # 生成几个番号来搜索（模拟最新上架）
            # 使用较新的番号范围
            base_offset = (page - 1) * 5 + i * 2
            search_patterns = [
                f"{prefix}-{500 + base_offset:03d}",
                f"{prefix}-{600 + base_offset:03d}",
                f"{prefix}-{700 + base_offset:03d}",
            ]

            for pattern in search_patterns:
                if searched >= end_idx:
                    break

                jav_results = client.search_jav(pattern)
                if jav_results:
                    for jav in jav_results:
                        if searched >= end_idx:
                            break
                        if searched >= start_idx:
                            identifier = jav.slug if hasattr(jav, 'slug') and jav.slug else str(jav.id)
                            detail = client.get_jav_detail(identifier)
                            if detail:
                                results.append(_jav_to_media(detail))
                        searched += 1

                # 添加延迟避免请求过快
                import time
                time.sleep(0.1)

        return results

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
        name="ByteMuse上新",
        mediaid_prefix="theporndb_new",
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
