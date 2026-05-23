from pathlib import Path
from typing import List, Any, Union, Annotated, Optional

from fastapi import APIRouter, Depends

from app import schemas
from app.chain.media import MediaChain
from app.chain.tmdb import TmdbChain
from app.core.config import settings
from app.core.context import Context
from app.core.event import eventmanager
from app.core.metainfo import MetaInfo, MetaInfoPath
from app.core.security import verify_token, verify_apitoken
from app.db.models import User
from app.db.user_oper import get_current_active_user, get_current_active_superuser
from app.schemas import MediaType, MediaRecognizeConvertEventData
from app.schemas.category import CategoryConfig
from app.schemas.types import ChainEventType
from app.log import logger
import json
import urllib.parse
import ssl

router = APIRouter()


@router.get("/recognize", summary="识别媒体信息（种子）", response_model=schemas.Context)
async def recognize(title: str,
                    subtitle: Optional[str] = None,
                    _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据标题、副标题识别媒体信息
    """
    # 识别媒体信息
    metainfo = MetaInfo(title, subtitle)
    mediainfo = await MediaChain().async_recognize_by_meta(metainfo)
    if mediainfo:
        return Context(meta_info=metainfo, media_info=mediainfo).to_dict()
    return schemas.Context()


@router.get("/recognize2", summary="识别种子媒体信息（API_TOKEN）", response_model=schemas.Context)
async def recognize2(_: Annotated[str, Depends(verify_apitoken)],
                     title: str,
                     subtitle: Optional[str] = None
                     ) -> Any:
    """
    根据标题、副标题识别媒体信息 API_TOKEN认证（?token=xxx）
    """
    # 识别媒体信息
    return await recognize(title, subtitle)


@router.get("/recognize_file", summary="识别媒体信息（文件）", response_model=schemas.Context)
async def recognize_file(path: str,
                         _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据文件路径识别媒体信息
    """
    # 识别媒体信息
    context = await MediaChain().async_recognize_by_path(path)
    if context:
        return context.to_dict()
    return schemas.Context()


@router.get("/recognize_file2", summary="识别文件媒体信息（API_TOKEN）", response_model=schemas.Context)
async def recognize_file2(path: str,
                          _: Annotated[str, Depends(verify_apitoken)]) -> Any:
    """
    根据文件路径识别媒体信息 API_TOKEN认证（?token=xxx）
    """
    # 识别媒体信息
    return await recognize_file(path)


@router.get("/search", summary="搜索媒体/人物信息", response_model=List[dict])
async def search(title: str,
                 type: Optional[str] = "media",
                 page: int = 1,
                 count: int = 8,
                 _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    模糊搜索媒体/人物信息列表 media：媒体信息，person：人物信息
    """

    def __get_source(obj: Union[schemas.MediaInfo, schemas.MediaPerson, dict]):
        """
        获取对象属性
        """
        if isinstance(obj, dict):
            return obj.get("source")
        return obj.source

    media_chain = MediaChain()
    if type == "media":
        _, medias = await media_chain.async_search(title=title)
        result = [media.to_dict() for media in medias] if medias else []
    elif type == "collection":
        collections = await media_chain.async_search_collections(name=title)
        result = [collection.to_dict() for collection in collections] if collections else []
    else:  # person
        persons = await media_chain.async_search_persons(name=title)
        result = [person.model_dump() for person in persons] if persons else []

    if not result:
        return []

    # 排序和分页
    setting_order = settings.SEARCH_SOURCE.split(',') if settings.SEARCH_SOURCE else []
    sort_order = {source: index for index, source in enumerate(setting_order)}

    sorted_result = sorted(result, key=lambda x: sort_order.get(__get_source(x), 4))
    return sorted_result[(page - 1) * count:page * count]


@router.post("/scrape/{storage}", summary="刮削媒体信息", response_model=schemas.Response)
def scrape(fileitem: schemas.FileItem,
           storage: Optional[str] = "local",
           _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    刮削媒体信息
    """
    if not fileitem or not fileitem.path:
        return schemas.Response(success=False, message="刮削路径无效")
    chain = MediaChain()
    # 识别媒体信息
    scrape_path = Path(fileitem.path)
    meta = MetaInfoPath(scrape_path)
    mediainfo = chain.recognize_by_meta(meta)
    if not mediainfo:
        return schemas.Response(success=False, message="刮削失败，无法识别媒体信息")
    if storage == "local":
        if not scrape_path.exists():
            return schemas.Response(success=False, message="刮削路径不存在")
    # 手动刮削 (暂时使用同步版本，可以后续优化为异步)
    chain.scrape_metadata(fileitem=fileitem, meta=meta, mediainfo=mediainfo, overwrite=True)
    return schemas.Response(success=True, message=f"{fileitem.path} 刮削完成")


@router.get("/category/config", summary="获取分类策略配置", response_model=schemas.Response)
def get_category_config(_: User = Depends(get_current_active_user)):
    """
    获取分类策略配置
    """
    config = MediaChain().category_config()
    return schemas.Response(success=True, data=config.model_dump())


@router.post("/category/config", summary="保存分类策略配置", response_model=schemas.Response)
def save_category_config(config: CategoryConfig, _: User = Depends(get_current_active_superuser)):
    """
    保存分类策略配置
    """
    if MediaChain().save_category_config(config):
        return schemas.Response(success=True, message="保存成功")
    else:
        return schemas.Response(success=False, message="保存失败")


@router.get("/category", summary="查询自动分类配置", response_model=dict)
async def category(_: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    查询自动分类配置
    """
    return MediaChain().media_category() or {}


@router.get("/group/seasons/{episode_group}", summary="查询剧集组季信息", response_model=List[schemas.MediaSeason])
async def group_seasons(episode_group: str, _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    查询剧集组季信息（themoviedb）
    """
    return await TmdbChain().async_tmdb_group_seasons(group_id=episode_group)


@router.get("/groups/{tmdbid}", summary="查询媒体剧集组", response_model=List[dict])
async def groups(tmdbid: int, _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    查询媒体剧集组列表（themoviedb）
    """
    mediainfo = await MediaChain().async_recognize_media(tmdbid=tmdbid, mtype=MediaType.TV)
    if not mediainfo:
        return []
    return mediainfo.episode_groups


@router.get("/seasons", summary="查询媒体季信息", response_model=List[schemas.MediaSeason])
async def seasons(mediaid: Optional[str] = None,
                  title: Optional[str] = None,
                  year: str = None,
                  season: int = None,
                  _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    查询媒体季信息
    """
    if mediaid:
        if mediaid.startswith("tmdb:"):
            tmdbid = int(mediaid[5:])
            seasons_info = await TmdbChain().async_tmdb_seasons(tmdbid=tmdbid)
            if seasons_info:
                if season is not None:
                    return [sea for sea in seasons_info if sea.season_number == season]
                return seasons_info
    if title:
        meta = MetaInfo(title)
        if year:
            meta.year = year
        mediainfo = await MediaChain().async_recognize_media(meta, mtype=MediaType.TV)
        if mediainfo:
            if settings.RECOGNIZE_SOURCE == "themoviedb":
                seasons_info = await TmdbChain().async_tmdb_seasons(tmdbid=mediainfo.tmdb_id)
                if seasons_info:
                    if season is not None:
                        return [sea for sea in seasons_info if sea.season_number == season]
                    return seasons_info
            else:
                sea = season if season is not None else 1
                return [schemas.MediaSeason(
                    season_number=sea,
                    poster_path=mediainfo.poster_path,
                    name=f"第 {sea} 季",
                    air_date=mediainfo.release_date,
                    overview=mediainfo.overview,
                    vote_average=mediainfo.vote_average,
                    episode_count=mediainfo.number_of_episodes
                )]
    return []


@router.get("/{mediaid}", summary="查询媒体详情")
async def detail(mediaid: str, type_name: str, title: Optional[str] = None, year: str = None,
                 _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据媒体ID查询themoviedb或豆瓣媒体信息，type_name: 电影/电视剧
    """
    logger.error(f"!!! DETAIL_ENDPOINT CALLED mediaid={mediaid}, type_name={type_name} !!!")
    mtype = MediaType(type_name)
    mediainfo = None
    mediachain = MediaChain()
    if mediaid.startswith("tmdb:"):
        mediainfo = await mediachain.async_recognize_media(tmdbid=int(mediaid[5:]), mtype=mtype)
    elif mediaid.startswith("douban:"):
        mediainfo = await mediachain.async_recognize_media(doubanid=mediaid[7:], mtype=mtype)
    elif mediaid.startswith("bangumi:"):
        mediainfo = await mediachain.async_recognize_media(bangumiid=int(mediaid[8:]), mtype=mtype)
    elif mediaid.startswith("metatube_search:") or mediaid.startswith("metatube:") or mediaid.startswith("bytemuse:"):
        code = mediaid.split(":", 1)[1]
        try:
            logger.info(f"[BYTEMUSE_DETAIL] code={code}")
            bm_url = 'http://10.0.0.1:3750/api/v1/codes/search'
            import http.client
            import urllib.parse as _up
            _params = _up.urlencode({'query': code})
            _conn = http.client.HTTPConnection('10.0.0.1', 3750, timeout=5)
            _conn.request('GET', f'/api/v1/codes/search?{_params}')
            _resp = _conn.getresponse()
            bm_data = json.loads(_resp.read())
            _conn.close()
            codes_data = bm_data.get('data', {}).get('codes') or []
            actors_data = bm_data.get('data', {}).get('actors') or []

            if not codes_data:
                logger.warning(f"[BYTEMUSE_DETAIL] No result for {code}")
                return None

            item = codes_data[0]
            cn_title = item.get('cn_title', '') or ''
            title = cn_title or item.get('title', '') or code
            poster = item.get('poster', '') or item.get('banner', '') or ''
            banner = item.get('banner', '') or ''
            create_time = item.get('create_time', '') or ''
            year = create_time[:4] if len(create_time) >= 4 else ''
            duration = item.get('duration', 0) or 0
            description = item.get('description', '') or ''

            # Build actors list with photos
            cast = []
            actor_photo_map = {}
            for actor in actors_data:
                name = actor.get('name', '') if isinstance(actor, dict) else str(actor)
                photo = actor.get('photo', '') if isinstance(actor, dict) else ''
                actor_photo_map[name] = photo
                cast.append({
                    'id': None, 'name': name, 'character': '', 'profile_path': photo,
                    'gender': None, 'known_for_department': 'Acting',
                    'original_name': name, 'popularity': None, 'credit_id': None, 'order': len(cast)
                })

            # Also parse actors from title/description if needed
            # JavBus-style actor names from the API

            # Build recommendations (today's new releases, excluding same-actor works)
            recommendations = []
            try:
                import http.client as _hc2
                # Get current actor
                _conn1 = _hc2.HTTPConnection('10.0.0.1', 3750, timeout=5)
                _conn1.request('GET', f'/api/v1/codes/search?query={code}')
                _resp1 = _conn1.getresponse()
                current_data = json.loads(_resp1.read())
                _conn1.close()
                current_actors = set()
                actors_data = current_data.get('data', {}).get('actors') or []
                if actors_data and isinstance(actors_data[0], dict):
                    main_actor = actors_data[0].get('name', '')
                    if main_actor:
                        current_actors.add(main_actor)
                # Get new releases
                _conn2 = _hc2.HTTPConnection('10.0.0.1', 3750, timeout=5)
                body = json.dumps({'page': 1, 'page_size': 20}).encode('utf-8')
                _conn2.request('POST', '/api/v1/codes/release_today', body=body, headers={'Content-Type': 'application/json'})
                _resp2 = _conn2.getresponse()
                new_data = json.loads(_resp2.read())
                _conn2.close()
                items = new_data if isinstance(new_data, list) else (new_data.get('data') or [])
                for c in items[:12]:
                    if not isinstance(c, dict):
                        continue
                    c_code = c.get('code', '') or ''
                    if not c_code or c_code.upper() == code.upper():
                        continue
                    # Exclude same-actor works
                    item_actors = c.get('actors') or []
                    actor_names = set()
                    for a in item_actors:
                        if isinstance(a, dict) and a.get('name'):
                            actor_names.add(a.get('name'))
                    if current_actors & actor_names:
                        continue
                    c_title = (c.get('cn_title', '') or c.get('title', '') or c_code)
                    c_poster = c.get('poster', '') or c.get('banner', '') or ''
                    recommendations.append({
                        'id': c_code, 'tmdb_id': c_code,
                        'title': c_title, 'poster_path': c_poster,
                        'backdrop_path': '', 'overview': '', 'vote_average': 0,
                        'source': 'bytemuse', 'type': '电影',
                        'media_id': c_code, 'mediaid_prefix': 'metatube'
                    })
            except Exception as e:
                logger.debug(f"[BYTEMUSE_DETAIL] Recommendations fetch failed: {e}")

            # Build similar (same-actor works)
            similar = []
            try:
                if actors_data and isinstance(actors_data[0], dict):
                    actor_name = actors_data[0].get('name', '')
                    if actor_name:
                        import http.client as _hc3
                        from urllib.parse import quote as _quote
                        _conn3 = _hc3.HTTPConnection('10.0.0.1', 3750, timeout=5)
                        _conn3.request('GET', '/api/v1/codes/search?query=' + _quote(actor_name, safe=''))
                        _resp3 = _conn3.getresponse()
                        bm_search = json.loads(_resp3.read())
                        _conn3.close()
                        all_codes = bm_search.get('data', {}).get('codes') or []
                        rec_ids = set(x.get('id','') or x.get('media_id','') for x in recommendations)
                        for c in all_codes[:12]:
                            c_code = c.get('code', '') if isinstance(c, dict) else ''
                            if c_code and c_code != code and c_code not in rec_ids:
                                c_title = (c.get('cn_title', '') or c.get('title', '') or c_code) if isinstance(c, dict) else c_code
                                c_poster = c.get('poster', '') or c.get('banner', '') or ''
                                similar.append({
                                    'id': c_code, 'tmdb_id': c_code,
                                    'title': c_title, 'poster_path': c_poster,
                                    'backdrop_path': '', 'overview': '', 'vote_average': 0,
                                    'source': 'bytemuse', 'type': '电影',
                                    'media_id': c_code, 'mediaid_prefix': 'metatube'
                                })
                                rec_ids.add(c_code)
            except Exception as e:
                logger.debug(f"[BYTEMUSE_DETAIL] Similar fetch failed: {e}")

            # Build stills from item (with image proxy for DMM etc.)
            stills = []
            still_photo = item.get('still_photo', '') or ''
            if still_photo:
                from urllib.parse import quote
                for s in still_photo.split(','):
                    s = s.strip()
                    if not s:
                        continue
                    if s.startswith('http'):
                        s = f'/api/v1/plugin/ByteMuseDiscover/image?url={quote(s, safe="")}'
                    stills.append(s)

            result = {
                'id': code,
                'tmdb_id': code,
                'imdb_id': None, 'tvdb_id': None, 'douban_id': None, 'bangumi_id': None,
                'collection_id': None, 'belongs_to_collection': None,
                'title': title,
                'en_title': item.get('title', '') or '',
                'original_title': item.get('title', '') or '',
                'overview': description,
                'poster_path': poster,
                'backdrop_path': banner,
                'vote_average': float(item.get('score', 0) or 0),
                'source': 'bytemuse',
                'type': '电影',
                'adult': True,
                'category': '成人/日系',
                'original_language': 'ja',
                'year': year or '2026',
                'release_date': f'{year or "2026"}-01-01',
                'mediaid_prefix': 'metatube',
                'media_id': code,
                'detail_link': f'https://www.javbus.com/{code}' if '-' in code else '',
                'status': 'Released',
                'runtime': int(duration) if duration else 120,
                'origin_country': ['JP'],
                'spoken_languages': [{'english_name': 'Japanese', 'iso_639_1': 'ja', 'name': 'Japanese'}],
                'production_countries': [{'iso_3166_1': 'JP', 'name': 'Japan'}],
                'genres': [{'id': 18, 'name': 'Drama'}],
                'genre_ids': [18],
                'popularity': float(item.get('score', 0) or 0) * 10,
                'vote_count': 0,
                'tagline': '',
                'release_dates': [{'date': f'{year or "2026"}-01-01T00:00:00.000Z', 'iso_code': 'JP', 'note': '', 'type': 3}],
                'first_air_date': None, 'last_air_date': None,
                'networks': [], 'number_of_episodes': None, 'number_of_seasons': None,
                'created_by': [], 'episode_run_time': [],
                'languages': ['ja'], 'season_info': [], 'seasons': {},
                'episode_groups': [], 'episode_group': None, 'next_episode_to_air': {},
                'title_year': f'{title} ({year})' if year else title,
                'actors': cast,
                'directors': [],
                'stills': stills,
                'recommendations': recommendations,
                'similar': similar,
                'code': code,
                'actor_name': (actors_data[0].get('name', '') if actors_data and isinstance(actors_data[0], dict) else ''),
            }
            logger.info(f"[BYTEMUSE_DETAIL] Success: {title}")
            return result
        except Exception as e:
            import traceback
            logger.error(f"[BYTEMUSE_DETAIL] Failed: {e} - {traceback.format_exc()}")
    else:
        event_data = MediaRecognizeConvertEventData(
            mediaid=mediaid,
            convert_type=settings.RECOGNIZE_SOURCE
        )
        event = await eventmanager.async_send_event(ChainEventType.MediaRecognizeConvert, event_data)
        if event and event.event_data and event.event_data.media_dict:
            event_data = event.event_data
            new_id = event_data.media_dict.get("id")
            if event_data.convert_type == "themoviedb":
                mediainfo = await mediachain.async_recognize_media(tmdbid=new_id, mtype=mtype)
            elif event_data.convert_type == "douban":
                mediainfo = await mediachain.async_recognize_media(doubanid=new_id, mtype=mtype)
        elif title:
            meta = MetaInfo(title)
            if year:
                meta.year = year
            if mtype:
                meta.type = mtype
            mediainfo = await mediachain.async_recognize_media(meta=meta)
    if mediainfo:
        await mediachain.async_obtain_images(mediainfo)
        return mediainfo.to_dict()
    return schemas.MediaInfo()


    """
    根据媒体ID查询themoviedb或豆瓣媒体信息，type_name: 电影/电视剧
    """
    mtype = MediaType(type_name)
    mediainfo = None
    mediachain = MediaChain()
    if mediaid.startswith("tmdb:"):
        mediainfo = await mediachain.async_recognize_media(tmdbid=int(mediaid[5:]), mtype=mtype)
    elif mediaid.startswith("douban:"):
        mediainfo = await mediachain.async_recognize_media(doubanid=mediaid[7:], mtype=mtype)
    elif mediaid.startswith("bangumi:"):
        mediainfo = await mediachain.async_recognize_media(bangumiid=int(mediaid[8:]), mtype=mtype)
    elif mediaid.startswith("metatube_search:") or mediaid.startswith("metatube:") or mediaid.startswith("bytemuse:"):
        # 成人番号详情：提取番号，直接调 MetatubeSource 插件获取详情
        code = mediaid.split(":", 1)[1]
        try:
            logger.info(f"Metatube detail request for code: {code}")
            from app.utils.singleton import Singleton
            for cls in Singleton._instances.values():
                if hasattr(cls, '_running_plugins'):
                    # Case-insensitive plugin lookup
                    plugin = None
                    for k, v in cls._running_plugins.items():
                        if 'metatube' in k.lower():
                            plugin = v
                            break
                    if plugin:
                        client = getattr(plugin, '_metatube_client', None)
                        if not client:
                            client = getattr(plugin, 'metatube_client', None)
                        if client:
                            results = client.search(code)
                            logger.info(f"Metatube search for {code}: {len(results) if results else 0} results")
                            if results:
                                movie = results[0]
                                detail = client.get_detail(movie.provider, movie.id)
                                if detail:
                                    mediainfo = plugin._convert_metatube_detail_to_mediainfo(detail)
                                    if mediainfo:
                                        if mediainfo.douban_id:
                                            await mediachain.async_obtain_images(mediainfo)
                                        logger.info(f"Metatube detail success: {mediainfo.title}")
                                        # 转换为 TMDB-like 格式返回
                                        result = mediainfo.to_dict()
                                        # 演员转换为 TMDB cast 格式
                                        if result.get('actors'):
                                            cast = []
                                            for i, actor in enumerate(result['actors']):
                                                if isinstance(actor, dict):
                                                    name = actor.get('name', '')
                                                else:
                                                    name = str(actor)
                                                cast.append({
                                                    'id': None,
                                                    'name': name,
                                                    'character': '',
                                                    'profile_path': None,
                                                    'gender': None,
                                                    'known_for_department': 'Acting',
                                                    'original_name': name,
                                                    'popularity': None,
                                                    'credit_id': None,
                                                    'order': i
                                                })
                                            result['actors'] = cast
                                        # 确保 id 字段存在
                                        if 'id' not in result or not result.get('id'):
                                            result['id'] = result.get('media_id') or result.get('tmdb_id')
                                        # 前端识别 source=themoviedb，否则显示"未识别到媒体信息"
                                        result['source'] = 'themoviedb'
                                        logger.info(f"DEBUG: set source=themoviedb, id={result.get('id')}")
                                        return result
                        logger.warning(f"Metatube plugin found but no client")
                        break
            logger.warning(f"MetatubeSource plugin not found in running plugins")
        except Exception as e:
            import traceback
            logger.error(f"Metatube detail failed: {e}\n{traceback.format_exc()}")
    else:
        # 广播事件解析媒体信息
        event_data = MediaRecognizeConvertEventData(
            mediaid=mediaid,
            convert_type=settings.RECOGNIZE_SOURCE
        )
        event = await eventmanager.async_send_event(ChainEventType.MediaRecognizeConvert, event_data)
        # 使用事件返回的上下文数据
        if event and event.event_data and event.event_data.media_dict:
            event_data: MediaRecognizeConvertEventData = event.event_data
            new_id = event_data.media_dict.get("id")
            if event_data.convert_type == "themoviedb":
                mediainfo = await mediachain.async_recognize_media(tmdbid=new_id, mtype=mtype)
            elif event_data.convert_type == "douban":
                mediainfo = await mediachain.async_recognize_media(doubanid=new_id, mtype=mtype)
        elif title:
            # 使用名称识别兜底
            meta = MetaInfo(title)
            if year:
                meta.year = year
            if mtype:
                meta.type = mtype
            mediainfo = await mediachain.async_recognize_media(meta=meta)
    # 识别
    if mediainfo:
        await mediachain.async_obtain_images(mediainfo)
        return mediainfo.to_dict()

    return schemas.MediaInfo()


@router.get("/debug/metatube", summary="调试")
async def debug_metatube(code: str = "CEMD-840") -> Any:
    """临时调试端点 - 无需认证"""
    import traceback as tb
    try:
        from app.utils.singleton import Singleton
        found_pm = False
        for cls_name, cls_inst in Singleton._instances.items():
            if hasattr(cls_inst, '_running_plugins'):
                found_pm = True
                has_meta = any('metatube' in k.lower() for k in cls_inst._running_plugins.keys())
                plugin = None
                if has_meta:
                    for k, v in cls_inst._running_plugins.items():
                        if 'metatube' in k.lower():
                            plugin = v
                            break
                if not plugin:
                    plugin = cls_inst._running_plugins.get("MetatubeSource") or cls_inst._running_plugins.get("metatubesource")
                if plugin:
                    client = getattr(plugin, '_metatube_client', None) or getattr(plugin, 'metatube_client', None)
                    if client:
                        results = client.search(code)
                        if results:
                            movie = results[0]
                            detail = client.get_detail(movie.provider, movie.id)
                            if detail:
                                info = plugin._convert_metatube_detail_to_mediainfo(detail)
                                if info:
                                    return {"ok": True, "title": info.title, "type": str(info.type), "year": info.year, "poster": info.poster_path or ""}
                                else:
                                    return {"ok": False, "search_results": len(results), "convert_failed": True, "detail_type": str(type(detail))}
                            else:
                                return {"ok": False, "search_results": len(results), "detail": None, "provider": movie.provider, "id": movie.id}
                        return {"ok": False, "search_results": 0, "client": str(type(client).__name__)}
                return {"ok": False, "plugins": list(cls_inst._running_plugins.keys()), "has_metatube": "MetatubeSource" in cls_inst._running_plugins}
        return {"ok": False, "found_pm": found_pm, "singletons": list(Singleton._instances.keys())}
    except Exception as ex:
        return {"ok": False, "error": str(ex), "traceback": tb.format_exc()}
