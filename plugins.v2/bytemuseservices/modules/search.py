"""
搜索模块
提供番号搜索服务
支持 ThePornDB、ByteMuse、Metatube 三个数据源
"""
from typing import List, Dict, Any, Optional
from app.schemas import MediaInfo, DiscoverMediaSource
from app.core.config import settings
from app.log import logger

# ByteMuse API 客户端
from ..bytemuse_api import ByteMuseApiClient
from ..schema import ByteMuseMovie
from ..theporndb_api import ThePornDBApiClient
from ..schema import ThePornDBJAVScene

# 全局配置
_bytemuse_base_url = "http://10.0.0.1:3750"
_bytemuse_username = "mubey"
_bytemuse_password = "355492"
_theporndb_api_token = ""
_metatube_base_url = "http://10.0.0.1:3244"


def get_api(master_plugin):
    """获取API列表"""
    global _bytemuse_base_url, _bytemuse_username, _bytemuse_password
    global _theporndb_api_token, _metatube_base_url
    _bytemuse_base_url = master_plugin.bytemuse_base_url
    _bytemuse_username = master_plugin.bytemuse_username
    _bytemuse_password = master_plugin.bytemuse_password
    _theporndb_api_token = master_plugin.theporndb_api_token
    _metatube_base_url = master_plugin.metatube_base_url
    return [
        {
            "path": "/bytemuse_search",
            "endpoint": search,
            "methods": ["GET"],
            "summary": "ByteMuse 搜索",
            "description": "番号搜索服务（支持 ThePornDB/ByteMuse/Metatube/全部）",
        },
        {
            "path": "/bytemuse_detail",
            "endpoint": detail,
            "methods": ["GET"],
            "summary": "ByteMuse 详情",
            "description": "根据番号获取详情信息",
        },
        {
            "path": "/bytemuse_torrents",
            "endpoint": torrents,
            "methods": ["GET"],
            "summary": "ByteMuse 种子",
            "description": "根据番号搜索种子",
        },
        {
            "path": "/bytemuse_actor_works",
            "endpoint": actor_works,
            "methods": ["GET"],
            "summary": "ByteMuse 演员作品",
            "description": "根据演员名搜索作品",
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

    # 使用 code 作为唯一标识符，如果 code 不存在则使用 id
    # 修复：确保 media_id 永远不为空
    if movie.code:
        media_id = movie.code
    elif movie.id:
        media_id = f"bytemuse_{movie.id}"
    else:
        # 最后的备选方案：使用标题
        media_id = title or f"unknown_{id(movie)}"

    return MediaInfo(
        type="电影",
        title=title,
        mediaid_prefix="bytemuse_search",
        media_id=media_id,
        imdb_id=f"bytemuse_search:{movie.code}" if movie.code else f"bytemuse_search:{media_id}",  # 用于订阅识别
        poster_path=movie.poster_url or movie.cover_url or movie.thumb_url or "",
        vote_average=movie.score,
        year=movie.release_date[:4] if movie.release_date else None,
        overview=movie.summary or "",
        studio=movie.studio or movie.publisher or "",
    )


def search_bytemuse(keyword: str) -> List[MediaInfo]:
    """使用 ByteMuse 搜索"""
    if not _bytemuse_username or not _bytemuse_password:
        logger.warning("ByteMuse 搜索失败: 未配置用户名或密码")
        return []

    try:
        client = ByteMuseApiClient(
            base_url=_bytemuse_base_url,
            username=_bytemuse_username,
            password=_bytemuse_password,
        )

        # 没有关键词时，返回推荐内容
        if not keyword:
            logger.debug(f"ByteMuse 空搜索，使用推荐接口")
            movies = client.get_recommend(category="all", page=1, page_size=20)
            if movies:
                logger.info(f"ByteMuse 推荐返回 {len(movies)} 条结果")
                return [_movie_to_media(movie) for movie in movies[:20]]
            logger.debug(f"ByteMuse 推荐未返回结果")
            return []

        # 有关键词时，使用搜索 API
        logger.debug(f"ByteMuse 搜索关键词: {keyword}")
        result = client.search_by_code(query=keyword)
        if not result:
            logger.debug(f"ByteMuse 搜索未返回结果")
            return []

        codes = result.get("codes", [])
        if not codes:
            logger.debug(f"ByteMuse 搜索 codes 为空")
            return []

        logger.info(f"ByteMuse 搜索返回 {len(codes)} 条结果")
        media_list = []
        for i, code_data in enumerate(codes[:20]):
            try:
                media_list.append(_movie_to_media(ByteMuseMovie(**code_data)))
            except Exception as e:
                logger.warning(f"ByteMuse 解码第 {i+1} 条结果失败: {str(e)}")
                continue

        return media_list

    except Exception as err:
        logger.error(f"ByteMuse 搜索失败: {str(err)}")
        import traceback
        logger.debug(f"ByteMuse 搜索异常详情: {traceback.format_exc()}")
        return []


def detail(code: str = "") -> Optional[MediaInfo]:
    """
    根据番号获取详情

    :param code: 番号
    :return: 媒体信息
    """
    if not code:
        return None

    if not _bytemuse_username or not _bytemuse_password:
        logger.warning("ByteMuse 详情获取失败: 未配置用户名或密码")
        return None

    try:
        client = ByteMuseApiClient(
            base_url=_bytemuse_base_url,
            username=_bytemuse_username,
            password=_bytemuse_password,
        )

        # 使用搜索接口获取详情
        result = client.search_by_code(query=code)

        if not result:
            logger.warning(f"ByteMuse 未找到番号: {code}")
            return None

        # 解析返回的数据
        codes = result.get("codes", [])
        if not codes:
            logger.warning(f"ByteMuse 未找到番号: {code}")
            return None

        # 取第一个匹配结果
        movie_data = codes[0]

        # 转换为 ByteMuseMovie
        movie = ByteMuseMovie(**movie_data)

        logger.info(f"ByteMuse 详情获取成功: {code} -> {movie.title}")

        # 转换为 MediaInfo
        return _movie_to_media(movie)

    except Exception as err:
        logger.error(f"ByteMuse 详情获取失败: {str(err)}")
        return None


def torrents(query: str = "") -> List[Dict[str, Any]]:
    """
    根据番号搜索种子

    :param query: 番号
    :return: 种子列表
    """
    if not query:
        return []

    if not _bytemuse_username or not _bytemuse_password:
        logger.warning("ByteMuse 种子搜索失败: 未配置用户名或密码")
        return []

    try:
        client = ByteMuseApiClient(
            base_url=_bytemuse_base_url,
            username=_bytemuse_username,
            password=_bytemuse_password,
        )

        result = client.search_torrents(query=query)
        if result:
            logger.info(f"ByteMuse 种子搜索成功: {query}, 返回 {len(result)} 个种子")
        return result or []

    except Exception as err:
        logger.error(f"ByteMuse 种子搜索失败: {str(err)}")
        return []


def _torrent_to_media(torrent: Dict[str, Any], keyword: str = "") -> MediaInfo:
    """
    将种子数据转换为 MediaInfo

    :param torrent: 种子数据
    :param keyword: 搜索关键词
    :return: MediaInfo 对象
    """
    # 提取种子信息
    title = torrent.get("title", "")
    magnet = torrent.get("magnet", "")
    size = torrent.get("size", "")
    date = torrent.get("date", "")
    provider = torrent.get("provider", "")

    # 直接使用磁力链接作为 media_id，点击时可以直接获取
    import base64
    magnet_b64 = base64.b64encode(magnet.encode()).decode() if magnet else ""

    # 构建种子描述
    overview_parts = []
    if size:
        overview_parts.append(f"大小: {size}")
    if date:
        overview_parts.append(f"日期: {date}")
    if provider:
        overview_parts.append(f"来源: {provider}")
    overview = " | ".join(overview_parts) if overview_parts else "种子资源"

    # 标题添加种子标识
    display_title = f"📥 {title}"

    return MediaInfo(
        type="电影",
        title=display_title,
        mediaid_prefix="bytemuse_torrent",
        media_id=magnet_b64,  # base64 编码的磁力链接
        imdb_id=magnet,  # 原始磁力链接也保存一份
        poster_path="",
        vote_average=None,
        year=None,
        overview=overview,
        studio=provider or "",
    )


def actor_works(actor_name: str = "", page: int = 1, count: int = 20) -> List[MediaInfo]:
    """
    根据演员名搜索作品

    :param actor_name: 演员名
    :param page: 页码
    :param count: 每页数量
    :return: 媒体信息列表
    """
    if not actor_name:
        return []

    if not _bytemuse_username or not _bytemuse_password:
        logger.warning("ByteMuse 演员作品搜索失败: 未配置用户名或密码")
        return []

    try:
        client = ByteMuseApiClient(
            base_url=_bytemuse_base_url,
            username=_bytemuse_username,
            password=_bytemuse_password,
        )

        # 使用搜索 API，传入演员名
        result = client.search_by_code(query=actor_name)
        if not result:
            return []

        codes = result.get("codes", [])
        if not codes:
            return []

        # 过滤出包含该演员的作品
        works = []
        actor_name_upper = actor_name.upper()
        for code_data in codes[:100]:  # 获取更多结果用于过滤
            movie = ByteMuseMovie(**code_data)

            # 检查演员列表
            has_actor = False
            if movie.actors:
                for actor in movie.actors:
                    if actor.name and actor_name_upper in actor.name.upper():
                        has_actor = True
                        break
            elif movie.casts:
                casts_upper = movie.casts.upper()
                if actor_name_upper in casts_upper:
                    has_actor = True

            if has_actor:
                works.append(_movie_to_media(movie))
                if len(works) >= count:
                    break

        logger.info(f"ByteMuse 演员作品搜索成功: {actor_name}, 返回 {len(works)} 部作品")
        return works

    except Exception as err:
        logger.error(f"ByteMuse 演员作品搜索失败: {str(err)}")
        return []


def _jav_scene_to_media(scene: ThePornDBJAVScene) -> MediaInfo:
    """
    将 ThePornDBJAVScene 转换为 MediaInfo

    :param scene: ThePornDBJAVScene 对象
    :return: MediaInfo 对象
    """
    # 提取番号 (external_id)
    code = scene.external_id or ""
    title = code if code else (scene.title or "未知番号")[:50]

    # 提取海报图片
    poster_url = ""
    if scene.background:
        if hasattr(scene.background, 'url') and scene.background.url:
            poster_url = scene.background.url
        elif hasattr(scene.background, 'large') and scene.background.large:
            poster_url = scene.background.large
        else:
            poster_url = str(scene.background)

    # 厂牌信息
    studio = ""
    if scene.site:
        if hasattr(scene.site, 'name') and scene.site.name:
            studio = scene.site.name
        else:
            studio = str(scene.site)

    # 年份
    year = None
    if scene.date:
        try:
            year = scene.date[:4]
        except (IndexError, TypeError):
            pass

    # 确保 media_id 永远不为空
    media_id = code or scene.id or scene.slug or title or f"unknown_{id(scene)}"

    return MediaInfo(
        type="电影",
        title=title,
        mediaid_prefix="theporndb_jav",
        media_id=media_id,
        imdb_id=f"theporndb:{code}" if code else f"theporndb:{media_id}",
        poster_path=poster_url,
        vote_average=None,  # ThePornDB JAV 搜索结果没有评分
        year=year,
        overview=scene.title or "",  # 使用完整标题作为简介
        studio=studio,
    )


def search_theporndb(keyword: str) -> List[MediaInfo]:
    """使用 ThePornDB 搜索"""
    logger.info(f"[ThePornDB] 搜索开始, keyword='{keyword}', token={'已配置' if _theporndb_api_token else '未配置'}")

    if not _theporndb_api_token:
        logger.warning("[ThePornDB] 搜索失败: 未配置 API Token")
        return []

    try:
        client = ThePornDBApiClient(api_token=_theporndb_api_token)

        # 没有关键词时，返回空列表（ThePornDB 不支持无搜索推荐）
        if not keyword:
            logger.debug("[ThePornDB] 空搜索，返回空列表")
            return []

        # 使用 JAV 搜索 API
        logger.info(f"[ThePornDB] 调用 search_jav: {keyword}")
        scenes = client.search_jav(keyword)
        logger.info(f"[ThePornDB] search_jav 返回: {scenes is not None}, 类型={type(scenes).__name__ if scenes else 'None'}, 数量={len(scenes) if scenes else 0}")

        if not scenes:
            logger.info(f"[ThePornDB] 未找到结果: {keyword}")
            return []

        logger.info(f"[ThePornDB] 搜索成功: {keyword}, 返回 {len(scenes)} 条结果")
        media_list = []
        for i, scene in enumerate(scenes[:20]):
            try:
                media_list.append(_jav_scene_to_media(scene))
            except Exception as e:
                logger.warning(f"[ThePornDB] 解码第 {i+1} 条结果失败: {str(e)}")
                continue

        logger.info(f"[ThePornDB] 最终返回 {len(media_list)} 条结果")
        return media_list

    except Exception as err:
        logger.error(f"[ThePornDB] 搜索失败: {str(err)}")
        import traceback
        logger.debug(f"[ThePornDB] 异常详情: {traceback.format_exc()}")
        return []


def search_metatube(keyword: str) -> List[MediaInfo]:
    """使用 Metatube 搜索"""
    try:
        # 动态导入 Metatube API 客户端
        try:
            from plugins.v2.metatubesource.metatube_api import MetatubeApiClient
            HAS_METATUBE = True
        except ImportError:
            try:
                # 尝试相对导入
                from ...metatubesource.metatube_api import MetatubeApiClient
                HAS_METATUBE = True
            except ImportError:
                HAS_METATUBE = False
                logger.warning("Metatube 模块未安装")
                return []

        if not HAS_METATUBE:
            return []

        client = MetatubeApiClient(base_url=_metatube_base_url)
        results = client.search(keyword)

        if results:
            media_list = []
            for i, item in enumerate(results):
                try:
                    # 提取番号作为标题
                    num = item.number or ""
                    title = item.title or ""
                    # 如果番号不在标题中，添加番号到标题
                    if num and num not in title:
                        title = f"{num} {title}".strip()

                    # 年份
                    year = None
                    if item.release_date:
                        try:
                            year = item.release_date[:4]
                        except (IndexError, TypeError):
                            pass

                    # 确保 media_id 永远不为空
                    media_id = num or title or f"unknown_{id(item)}"

                    media_list.append(MediaInfo(
                        type="电影",
                        title=title if title else (num or "未知番号"),
                        mediaid_prefix="metatube",
                        media_id=media_id,
                        poster_path=item.cover_url or item.thumb_url or "",
                        vote_average=item.score if item.score else None,
                        year=year,
                        overview="",  # Metatube 搜索结果没有概述
                        studio=item.provider or "",
                    ))
                except Exception as e:
                    logger.warning(f"Metatube 解码第 {i+1} 条结果失败: {str(e)}")
                    continue

            logger.info(f"Metatube 搜索成功: {keyword}, 返回 {len(media_list)} 条结果")
            return media_list

        logger.debug(f"Metatube 未找到结果: {keyword}")
        return []

    except Exception as err:
        logger.error(f"Metatube 搜索失败: {str(err)}")
        import traceback
        logger.debug(f"Metatube 搜索异常详情: {traceback.format_exc()}")
        return []


def _deduplicate_media_list(media_list: List[MediaInfo]) -> List[MediaInfo]:
    """
    去重媒体列表，基于番号 (media_id) 去重

    :param media_list: 媒体信息列表
    :return: 去重后的媒体信息列表
    """
    seen = {}
    for media in media_list:
        # 使用 media_id 作为唯一标识
        if media.media_id and media.media_id not in seen:
            seen[media.media_id] = media
    return list(seen.values())


def search(
    keyword: str = "",
    source: str = "all",
) -> List[MediaInfo]:
    """
    统一的搜索API端点（同时搜索媒体和种子）

    :param keyword: 搜索关键词
    :param source: 数据源 (all=全部/bytemuse/theporndb/metatube)
    :return: 媒体信息列表（包含种子）
    """
    logger.info(f"[搜索] keyword={keyword}, source={source}")

    # 如果没有关键词，返回推荐内容
    if not keyword:
        if source == "bytemuse" or source == "all":
            logger.info("[搜索] 空关键词，使用 ByteMuse 推荐")
            return search_bytemuse("")
        # 其他源暂时不支持空搜索
        logger.info(f"[搜索] 空关键词，source={source} 返回空列表")
        return []

    # 先搜索媒体
    media_results = []

    # 全部数据源：同时搜索三个数据源并合并去重
    if source == "all":
        # ByteMuse
        try:
            bytemuse_results = search_bytemuse(keyword)
            media_results.extend(bytemuse_results)
            logger.info(f"[搜索] ByteMuse: {len(bytemuse_results)} 条")
        except Exception as e:
            logger.warning(f"[搜索] ByteMuse 失败: {str(e)}")

        # ThePornDB
        try:
            theporndb_results = search_theporndb(keyword)
            media_results.extend(theporndb_results)
            logger.info(f"[搜索] ThePornDB: {len(theporndb_results)} 条")
        except Exception as e:
            logger.warning(f"[搜索] ThePornDB 失败: {str(e)}")

        # Metatube
        try:
            metatube_results = search_metatube(keyword)
            media_results.extend(metatube_results)
            logger.info(f"[搜索] Metatube: {len(metatube_results)} 条")
        except Exception as e:
            logger.warning(f"[搜索] Metatube 失败: {str(e)}")

        # 去重媒体结果
        media_results = _deduplicate_media_list(media_results)
        logger.info(f"[搜索] 媒体去重后: {len(media_results)} 条")

    elif source == "theporndb":
        media_results = search_theporndb(keyword)
    elif source == "metatube":
        media_results = search_metatube(keyword)
    else:  # bytemuse
        media_results = search_bytemuse(keyword)

    # 同时搜索种子
    if keyword:
        try:
            torrent_results = torrents(query=keyword)
            if torrent_results:
                # 将种子转换为 MediaInfo 并附加到结果中
                torrent_media_list = [
                    _torrent_to_media(torrent, keyword)
                    for torrent in torrent_results[:10]  # 最多10个种子
                ]
                media_results.extend(torrent_media_list)
                logger.info(f"[搜索] 添加 {len(torrent_media_list)} 个种子结果")
        except Exception as e:
            logger.warning(f"[搜索] 种子搜索失败: {str(e)}")

    return media_results


def search_filter_ui() -> List[dict]:
    """
    搜索过滤参数UI配置
    """
    source_ui = [
        {
            "component": "VChip",
            "props": {"filter": True, "tile": True, "value": value},
            "text": text,
        }
        for value, text in [
            ("all", "全部"),
            ("bytemuse", "ByteMuse"),
            ("theporndb", "ThePornDB"),
            ("metatube", "Metatube"),
        ]
    ]

    return [
        # 关键词输入框
        {
            "component": "VTextField",
            "props": {
                "model": "keyword",
                "label": "关键词",
                "placeholder": "请输入番号",
                "variant": "outlined",
                "density": "compact",
                "clearable": True,
                "hide-details": True,
            }
        },
        # 数据源选择
        {
            "component": "div",
            "props": {"class": "flex justify-start items-center mt-2"},
            "content": [
                {
                    "component": "div",
                    "props": {"class": "mr-5"},
                    "content": [{"component": "VLabel", "text": "数据源"}],
                },
                {
                    "component": "VChipGroup",
                    "props": {"model": "source"},
                    "content": source_ui,
                },
            ],
        },
    ]


def discover_source(master_plugin, event_data):
    """注册搜索探索源"""
    search_source = DiscoverMediaSource(
        name="搜索",
        mediaid_prefix="bytemuse_search",
        api_path=f"plugin/ByteMuseServices/bytemuse_search?apikey={settings.API_TOKEN}",
        filter_params={
            "keyword": "",
            "source": "all",
        },
        filter_ui=search_filter_ui(),
    )

    if not event_data.extra_sources:
        event_data.extra_sources = [search_source]
    else:
        event_data.extra_sources.append(search_source)
