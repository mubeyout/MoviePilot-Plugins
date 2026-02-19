"""
厂牌模块
提供厂牌作品探索服务
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
            "path": "/bytemuse_studio_s1",
            "endpoint": studio_s1,
            "methods": ["GET"],
            "summary": "ByteMuse S1 厂牌",
            "description": "获取 S1 厂牌作品",
        },
        {
            "path": "/bytemuse_studio_ideapocket",
            "endpoint": studio_ideapocket,
            "methods": ["GET"],
            "summary": "ByteMuse IdeaPocket 厂牌",
            "description": "获取 IdeaPocket 厂牌作品",
        },
        {
            "path": "/bytemuse_studio_moodyz",
            "endpoint": studio_moodyz,
            "methods": ["GET"],
            "summary": "ByteMuse Moodyz 厂牌",
            "description": "获取 Moodyz 厂牌作品",
        },
        {
            "path": "/bytemuse_studio_premium",
            "endpoint": studio_premium,
            "methods": ["GET"],
            "summary": "ByteMuse Premium 厂牌",
            "description": "获取 Premium 厂牌作品",
        },
        {
            "path": "/bytemuse_studio_das",
            "endpoint": studio_das,
            "methods": ["GET"],
            "summary": "ByteMuse DAS 厂牌",
            "description": "获取 DAS 厂牌作品",
        },
        {
            "path": "/bytemuse_studio_madonna",
            "endpoint": studio_madonna,
            "methods": ["GET"],
            "summary": "ByteMuse Madonna 厂牌",
            "description": "获取 Madonna 厂牌作品",
        },
        {
            "path": "/bytemuse_studio_honnaka",
            "endpoint": studio_honnaka,
            "methods": ["GET"],
            "summary": "ByteMuse Honnaka 厂牌",
            "description": "获取 Honnaka 厂牌作品",
        },
        {
            "path": "/bytemuse_studio_attackers",
            "endpoint": studio_attackers,
            "methods": ["GET"],
            "summary": "ByteMuse Attackers 厂牌",
            "description": "获取 Attackers 厂牌作品",
        },
        {
            "path": "/bytemuse_studio_wanz",
            "endpoint": studio_wanz,
            "methods": ["GET"],
            "summary": "ByteMuse Wanz 厂牌",
            "description": "获取 Wanz 厂牌作品",
        },
    ]


# 厂牌番号前缀映射
_STUDIO_PREFIXES = {
    "S1": ["SSIS", "IPX", "SOAV"],
    "IdeaPocket": ["IPX", "IPZZ"],
    "Moodyz": ["MIDE", "MIAB", "MIMK", "MIAA", "MIDV"],
    "Premium": ["PRED", "PFES", "ABW"],
    "DAS": ["DASS", "DAKJ"],
    "Madonna": ["JUL", "JUQ"],
    "Honnaka": ["HNDR", "HNDV", "HND"],
    "Attackers": ["ATID", "SSNI", "SHKD"],
    "Wanz": ["WANZ", "WAT"],
}


def _jav_to_media(jav_data: Any, studio: str = None) -> MediaInfo:
    """
    将 ThePornDB JAV 数据转换为 MediaInfo

    :param jav_data: ThePornDB JAV 场景或详情数据
    :param studio: 厂牌名称（可选）
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

    # 添加厂牌和番号到标题
    if studio:
        title = f"[{studio}] {external_id} {title}".strip()
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

    # 提取厂牌信息
    site = data.get("site", {})
    studio_name = studio or ""
    if isinstance(site, dict) and not studio_name:
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


def _fetch_studio_works(studio: str, page: int, count: int) -> List[MediaInfo]:
    """
    获取厂牌作品

    :param studio: 厂牌名称
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    client = ThePornDBApiClient(api_token=_theporndb_api_token)
    results = []

    # 获取该厂牌的番号前缀
    prefixes = _STUDIO_PREFIXES.get(studio, [])

    if not prefixes:
        logger.warning(f"未找到厂牌 {studio} 的番号前缀配置")
        return []

    try:
        # 计算分页
        start_idx = (page - 1) * count
        end_idx = start_idx + count

        # 生成番号进行搜索
        searched = 0
        for prefix in prefixes:
            if searched >= end_idx:
                break

            # 生成该前缀的番号范围
            base_offset = (page - 1) * 10
            for offset in range(base_offset, base_offset + 20):
                if searched >= end_idx:
                    break

                # 生成番号
                code = f"{prefix}-{offset:03d}"

                try:
                    jav_results = client.search_jav(code)
                    if jav_results:
                        for jav in jav_results:
                            if searched >= end_idx:
                                break
                            if searched >= start_idx:
                                identifier = jav.slug if hasattr(jav, 'slug') and jav.slug else str(jav.id)
                                detail = client.get_jav_detail(identifier)
                                if detail:
                                    results.append(_jav_to_media(detail, studio=studio))
                            searched += 1
                except Exception as e:
                    logger.debug(f"搜索番号 {code} 失败: {str(e)}")
                    continue

        return results

    except Exception as err:
        logger.error(f"获取厂牌 {studio} 作品失败: {str(err)}")
        return []


def studio_s1(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 S1 厂牌作品"""
    return _fetch_studio_works("S1", page, count)


def studio_ideapocket(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 IdeaPocket 厂牌作品"""
    return _fetch_studio_works("IdeaPocket", page, count)


def studio_moodyz(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Moodyz 厂牌作品"""
    return _fetch_studio_works("Moodyz", page, count)


def studio_premium(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Premium 厂牌作品"""
    return _fetch_studio_works("Premium", page, count)


def studio_das(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 DAS 厂牌作品"""
    return _fetch_studio_works("DAS", page, count)


def studio_madonna(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Madonna 厂牌作品"""
    return _fetch_studio_works("Madonna", page, count)


def studio_honnaka(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Honnaka 厂牌作品"""
    return _fetch_studio_works("Honnaka", page, count)


def studio_attackers(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Attackers 厂牌作品"""
    return _fetch_studio_works("Attackers", page, count)


def studio_wanz(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Wanz 厂牌作品"""
    return _fetch_studio_works("Wanz", page, count)


def studios_filter_ui() -> List[dict]:
    """
    厂牌过滤参数UI配置
    """
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
    """注册厂牌探索源"""
    # 为每个厂牌创建独立的探索源
    studios_list = [
        ("s1", "S1"),
        ("ideapocket", "IdeaPocket"),
        ("moodyz", "Moodyz"),
        ("premium", "Premium"),
        ("das", "DAS"),
        ("madonna", "Madonna"),
        ("honnaka", "Honnaka"),
        ("attackers", "Attackers"),
        ("wanz", "Wanz"),
    ]

    sources = []
    for studio_key, studio_name in studios_list:
        source = DiscoverMediaSource(
            name=f"ByteMuse-{studio_name}",
            mediaid_prefix=f"theporndb_{studio_key}",
            api_path=f"plugin/ByteMuseServices/bytemuse_studio_{studio_key}?apikey={settings.API_TOKEN}",
            filter_params={
                "page": 1,
                "count": 20,
            },
            filter_ui=studios_filter_ui(),
            depends={},
        )
        sources.append(source)

    if not event_data.extra_sources:
        event_data.extra_sources = sources
    else:
        event_data.extra_sources.extend(sources)
