"""
厂牌模块
提供厂牌作品探索服务
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


# 厂牌名称映射
_STUDIO_NAMES = {
    "s1": "S1",
    "ideapocket": "IdeaPocket",
    "ip": "IdeaPocket",
    "moodyz": "Moodyz",
    "premium": "Premium",
    "das": "DAS",
    "madonna": "Madonna",
    "honnaka": "Honnaka",
    "attackers": "Attackers",
    "wanz": "Wanz",
}


def get_api(master_plugin):
    """获取API列表"""
    global _bytemuse_base_url, _bytemuse_username, _bytemuse_password
    _bytemuse_base_url = master_plugin.bytemuse_base_url
    _bytemuse_username = master_plugin.bytemuse_username
    _bytemuse_password = master_plugin.bytemuse_password
    return [
        {
            "path": "/bytemuse_studios",
            "endpoint": studios,
            "methods": ["GET"],
            "summary": "ByteMuse 厂牌",
            "description": "厂牌作品探索服务（9个厂牌）",
        },
    ]


def studios(
    studio: str = "s1",
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """
    统一的厂牌API端点

    :param studio: 厂牌名称 (s1, ideapocket, moodyz, premium, das, madonna, honnaka, attackers, wanz)
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    # 厂牌名称映射到函数
    studio_funcs = {
        "s1": studio_s1,
        "ideapocket": studio_ideapocket,
        "moodyz": studio_moodyz,
        "premium": studio_premium,
        "das": studio_das,
        "madonna": studio_madonna,
        "honnaka": studio_honnaka,
        "attackers": studio_attackers,
        "wanz": studio_wanz,
    }

    func = studio_funcs.get(studio.lower(), studio_s1)
    return func(page=page, count=count)


def _item_to_media(item: Dict[str, Any], studio: str = None) -> MediaInfo:
    """
    将榜单项数据转换为 MediaInfo

    :param item: 榜单项数据
    :param studio: 厂牌名称
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

    # 厂牌名称
    studio_name = _STUDIO_NAMES.get(studio.lower(), studio) if studio else ""

    return MediaInfo(
        type="电影",
        title=title,
        mediaid_prefix="bytemuse_studio",
        media_id=media_id,
        imdb_id=f"bytemuse_studio:{external_id}" if external_id else f"bytemuse_studio:{media_id}",  # 用于订阅识别
        poster_path=poster_url,
        vote_average=item.get("score"),
        year=item.get("date", "")[:4] if item.get("date") else None,
        overview=item.get("description", "") or item.get("summary", ""),
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
    client = ByteMuseApiClient(
        base_url=_bytemuse_base_url,
        username=_bytemuse_username,
        password=_bytemuse_password,
    )

    try:
        # 使用 ByteMuse API 获取厂牌榜单
        studio_data = client.get_studio_ranks(studio=studio, limit=count)

        if studio_data:
            # 计算分页
            start_idx = (page - 1) * count
            end_idx = start_idx + count
            paginated_data = studio_data[start_idx:end_idx]

            studio_name = _STUDIO_NAMES.get(studio.lower(), studio)
            return [_item_to_media(item, studio=studio_name) for item in paginated_data]

        return []

    except Exception as err:
        logger.error(f"获取厂牌 {studio} 作品失败: {str(err)}")
        return []


def studio_s1(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 S1 厂牌作品"""
    return _fetch_studio_works("s1", page, count)


def studio_ideapocket(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 IdeaPocket 厂牌作品"""
    return _fetch_studio_works("ideapocket", page, count)


def studio_moodyz(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Moodyz 厂牌作品"""
    return _fetch_studio_works("moodyz", page, count)


def studio_premium(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Premium 厂牌作品"""
    return _fetch_studio_works("premium", page, count)


def studio_das(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 DAS 厂牌作品"""
    return _fetch_studio_works("das", page, count)


def studio_madonna(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Madonna 厂牌作品"""
    return _fetch_studio_works("madonna", page, count)


def studio_honnaka(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Honnaka 厂牌作品"""
    return _fetch_studio_works("honnaka", page, count)


def studio_attackers(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Attackers 厂牌作品"""
    return _fetch_studio_works("attackers", page, count)


def studio_wanz(
    page: int = 1,
    count: int = 20,
) -> List[MediaInfo]:
    """获取 Wanz 厂牌作品"""
    return _fetch_studio_works("wanz", page, count)


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
    studios_source = DiscoverMediaSource(
        name="厂牌",
        mediaid_prefix="bytemuse_studio",
        api_path=f"plugin/ByteMuseServices/bytemuse_studios?apikey={settings.API_TOKEN}",
        filter_params={
            "studio": "s1",
            "page": 1,
            "count": 20,
        },
        filter_ui=studios_filter_ui(),
    )

    if not event_data.extra_sources:
        event_data.extra_sources = [studios_source]
    else:
        event_data.extra_sources.append(studios_source)
