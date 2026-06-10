# ByteMuse interceptor for non-numeric tmdbid
import urllib.request
import urllib.parse
from urllib.parse import quote as _mquote
import json
import ssl

from typing import List, Any, Optional

from fastapi import APIRouter, Depends

from app import schemas
from app.chain.tmdb import TmdbChain
from app.core.security import verify_token
from app.schemas.types import MediaType

router = APIRouter()


@router.get("/seasons/{tmdbid}", summary="TMDB所有季", response_model=List[schemas.TmdbSeason])
async def tmdb_seasons(tmdbid: int, _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据TMDBID查询themoviedb所有季信息
    """
    seasons_info = await TmdbChain().async_tmdb_seasons(tmdbid=tmdbid)
    if seasons_info:
        return seasons_info
    return []


@router.get("/similar/{tmdbid}/{type_name}", summary="类似电影/电视剧")
async def tmdb_similar(tmdbid: str,
                       type_name: str,
                       _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据TMDBID查询类似电影/电视剧，type_name: 电影/电视剧
    """
    # Non-numeric tmdbid: return empty (bytemuse-section handles this)
    try:
        int(tmdbid)
    except (ValueError, TypeError):
        # mediaverse: javbus code like SSIS-960, search by first actor for similar
        if '-' in tmdbid:
            try:
                import urllib.request as _urllib
                from urllib.parse import quote as _mquote
                _url = f'http://10.0.0.1:8922/api/movies/{_mquote(tmdbid, safe="")}'
                _resp = _urllib.urlopen(_url, timeout=5)
                _data = json.loads(_resp.read())
                _stars = (_data or {}).get('stars', []) or []
                if _stars and isinstance(_stars[0], dict) and _stars[0].get('name'):
                    _url2 = f'http://10.0.0.1:8922/api/movies/search?keyword={_mquote(_stars[0]["name"], safe="")}&page=1&count=12'
                    _resp2 = _urllib.urlopen(_url2, timeout=5)
                    _sim = json.loads(_resp2.read())
                    _out = []
                    for _m in (_sim.get('movies', []) or []):
                        _mid = _m.get('id', '')
                        if _mid and _mid != tmdbid:
                            _out.append({'id': _mid, 'tmdb_id': _mid, 'source': 'mediaverse', 'type': '电影',
                                        'title': _m.get('title', '') or _mid, 'poster_path': (f'/api/v1/plugin/MediaVerse/mediaverse/image?url={_mquote(_m.get("img",""), safe="")}' if _m.get('img') else ''),
                                        'backdrop_path': '', 'overview': '', 'vote_average': 0,
                                        'media_id': _mid, 'mediaid_prefix': 'mediaverse_search', 'adult': True})
                            if len(_out) >= 12: break
                    return _out
            except Exception:
                pass
        return []

    mediatype = MediaType(type_name)
    if mediatype == MediaType.MOVIE:
        medias = await TmdbChain().async_movie_similar(tmdbid=tmdbid)
    elif mediatype == MediaType.TV:
        medias = await TmdbChain().async_tv_similar(tmdbid=tmdbid)
    else:
        return []
    if medias:
        return [media.to_dict() for media in medias]
    return []


@router.get("/recommend/{tmdbid}/{type_name}", summary="推荐电影/电视剧")
async def tmdb_recommend(tmdbid: str,
                         type_name: str,
                         _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据TMDBID查询推荐电影/电视剧，type_name: 电影/电视剧
    """
    # Non-numeric tmdbid: return empty (bytemuse-section handles this)
    try:
        int(tmdbid)
    except (ValueError, TypeError):
        # mediaverse: return new releases
        if '-' in tmdbid:
            try:
                import urllib.request as _urllib
                _resp = _urllib.urlopen('http://10.0.0.1:8922/api/movies?page=1&count=12', timeout=5)
                _rec = json.loads(_resp.read())
                _out = []
                for _m in (_rec.get('movies', []) or []):
                    _mid = _m.get('id', '')
                    if _mid and _mid != tmdbid:
                        _out.append({'id': _mid, 'tmdb_id': _mid, 'source': 'mediaverse', 'type': '电影',
                                    'title': _m.get('title', '') or _mid, 'poster_path': (f'/api/v1/plugin/MediaVerse/mediaverse/image?url={_mquote(_m.get("img",""), safe="")}' if _m.get('img') else ''),
                                    'backdrop_path': '', 'overview': '', 'vote_average': 0,
                                    'media_id': _mid, 'mediaid_prefix': 'mediaverse_search', 'adult': True})
                        if len(_out) >= 12: break
                return _out
            except Exception:
                pass
        return []

    mediatype = MediaType(type_name)
    if mediatype == MediaType.MOVIE:
        medias = await TmdbChain().async_movie_recommend(tmdbid=tmdbid)
    elif mediatype == MediaType.TV:
        medias = await TmdbChain().async_tv_recommend(tmdbid=tmdbid)
    else:
        return []
    if medias:
        return [media.to_dict() for media in medias]
    return []


@router.get("/collection/{collection_id}", summary="系列合集详情", response_model=List[schemas.MediaInfo])
async def tmdb_collection(collection_id: int,
                          page: Optional[int] = 1,
                          count: Optional[int] = 20,
                          _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据合集ID查询合集详情
    """
    medias = await TmdbChain().async_tmdb_collection(collection_id=collection_id)
    if medias:
        return [media.to_dict() for media in medias][(page - 1) * count:page * count]
    return []


@router.get("/credits/{tmdbid}/{type_name}", summary="演员阵容", response_model=List[schemas.MediaPerson])
async def tmdb_credits(tmdbid: str,
                       type_name: str,
                       page: Optional[int] = 1,
                       _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据TMDBID查询演员阵容，type_name: 电影/电视剧
    """
    # Non-numeric tmdbid: intercept and return ByteMuse actor data
    try:
        int(tmdbid)
    except (ValueError, TypeError):
        return _bytemuse_credits(tmdbid)
    mediatype = MediaType(type_name)
    if mediatype == MediaType.MOVIE:
        persons = await TmdbChain().async_movie_credits(tmdbid=tmdbid, page=page)
    elif mediatype == MediaType.TV:
        persons = await TmdbChain().async_tv_credits(tmdbid=tmdbid, page=page)
    else:
        return []
    return persons or []


@router.get("/person/{person_id}", summary="人物详情", response_model=schemas.MediaPerson)
async def tmdb_person(person_id: int,
                      _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据人物ID查询人物详情
    """
    return await TmdbChain().async_person_detail(person_id=person_id)


@router.get("/person/credits/{person_id}", summary="人物参演作品", response_model=List[schemas.MediaInfo])
async def tmdb_person_credits(person_id: int,
                              page: Optional[int] = 1,
                              _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据人物ID查询人物参演作品
    """
    medias = await TmdbChain().async_person_credits(person_id=person_id, page=page)
    if medias:
        return [media.to_dict() for media in medias]
    return []


@router.get("/{tmdbid}/{season}", summary="TMDB季所有集", response_model=List[schemas.TmdbEpisode])
async def tmdb_season_episodes(tmdbid: int, season: int, episode_group: Optional[str] = None,
                               _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    根据TMDBID查询某季的所有信信息
    """
    return await TmdbChain().async_tmdb_episodes(tmdbid=tmdbid, season=season, episode_group=episode_group)





import time

# In-memory cache: {code: (timestamp, actors, works)}
_bytemuse_cache = {}
_CACHE_TTL = 1800  # 30 minutes

_bm_internal_url = 'http://10.0.0.1:3750/api/v1/codes/search'


def _bm_request(query):
    """Single ByteMuse search request."""
    req = urllib.request.Request(
        f'{_bm_internal_url}?query={urllib.parse.quote(query)}',
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
        return json.loads(r.read())


def _bm_get_actors_and_works(code):
    """Get actors and their works for a code, with caching."""
    now = time.time()
    cached = _bytemuse_cache.get(code)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1], cached[2]

    try:
        data = _bm_request(code)
        actors_data = data.get('data', {}).get('actors') or []
        all_works = data.get('data', {}).get('codes') or []

        # Get main actor name
        actor_name = ''
        if actors_data and isinstance(actors_data[0], dict):
            actor_name = actors_data[0].get('name', '')

        # Search works by actor name
        works = all_works
        if actor_name:
            try:
                actor_data = _bm_request(actor_name)
                works = actor_data.get('data', {}).get('codes') or []
            except Exception:
                pass

        _bytemuse_cache[code] = (now, actors_data, works)
        return actors_data, works
    except Exception:
        return [], []


def _bytemuse_credits(code):
    actors_data, _ = _bm_get_actors_and_works(code)
    result = []
    for actor in actors_data:
        name = actor.get('name', '') if isinstance(actor, dict) else str(actor)
        photo = actor.get('photo', '') if isinstance(actor, dict) else ''
        result.append({
            'source': 'douban',
            'id': None,
            'type': 1,
            'name': name,
            'character': '',
            'images': {},
            'profile_path': '',
            'gender': None,
            'original_name': name,
            'credit_id': None,
            'also_known_as': [],
            'birthday': None,
            'deathday': None,
            'imdb_id': None,
            'known_for_department': 'Acting',
            'place_of_birth': None,
            'popularity': None,
            'biography': None,
            'roles': [],
            'title': '',
            'url': '',
            'avatar': photo or '',
            'latin_name': '',
            'career': [],
            'relation': '',
        })
    return result


def _bytemuse_similar(code):
    """Get same-actor works (for TMDB '类似' endpoint)."""
    _, works = _bm_get_actors_and_works(code)
    result = []
    for c in works[:12]:
        c_code = c.get('code', '') if isinstance(c, dict) else ''
        if c_code and c_code != code:
            poster = c.get('poster', '') if isinstance(c, dict) else ''
            banner = c.get('banner', '') if isinstance(c, dict) else ''
            title = (c.get('cn_title', '') or c.get('title', '') or c_code) if isinstance(c, dict) else c_code
            result.append({
                'id': c_code,
                'tmdb_id': c_code,
                'title': title,
                'poster_path': poster or banner,
                'backdrop_path': banner,
                'overview': '',
                'vote_average': 0,
                'source': 'bytemuse',
                'type': '电影',
                'year': (c.get('create_time', '') or '')[:4] if isinstance(c, dict) else '',
                'media_id': c_code,
                'mediaid_prefix': 'metatube',
            })
    return result


def _bytemuse_recommend(code):
    """Get today's new releases excluding same-actor works (for TMDB '推荐' endpoint)."""
    try:
        # Get current actor
        req = urllib.request.Request(
            _bm_internal_url + f'?query={urllib.parse.quote(code)}',
            headers={'Content-Type': 'application/json'},
            method='GET'
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            current_data = json.loads(r.read())

        current_actors = set()
        actors_data = current_data.get('data', {}).get('actors') or []
        if actors_data and isinstance(actors_data[0], dict):
            main_actor = actors_data[0].get('name', '')
            if main_actor:
                current_actors.add(main_actor)
        # Get new releases
        req2 = urllib.request.Request(
            'http://10.0.0.1:3750/api/v1/codes/release_today',
            data=json.dumps({'page': 1, 'page_size': 20}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        ctx2 = ssl.create_default_context()
        with urllib.request.urlopen(req2, context=ctx2, timeout=8) as r:
            new_data = json.loads(r.read())
        items = new_data if isinstance(new_data, list) else (new_data.get('data') or [])
        result = []
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
            poster = c.get('poster', '') or c.get('banner', '') or ''
            title = (c.get('cn_title', '') or c.get('title', '') or c_code)
            result.append({
                'id': c_code,
                'tmdb_id': c_code,
                'title': title,
                'poster_path': poster,
                'backdrop_path': c.get('banner', '') or '',
                'overview': '',
                'vote_average': 0,
                'source': 'bytemuse',
                'type': '电影',
                'year': (c.get('create_time', '') or '')[:4],
                'media_id': c_code,
                'mediaid_prefix': 'metatube',
            })
        return result
    except Exception:
        return []

        current_actors = set()
        actors_data = current_data.get('data', {}).get('actors') or []
        if actors_data and isinstance(actors_data[0], dict):
            main_actor = actors_data[0].get('name', '')
            if main_actor:
                current_actors.add(main_actor)

        # Get new releases
        req2 = urllib.request.Request(
            'http://10.0.0.1:3750/api/v1/codes/release_today',
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        body = json.dumps({'page': 1, 'page_size': 20}).encode('utf-8')
        req2 = urllib.request.Request(
            'http://10.0.0.1:3750/api/v1/codes/release_today',
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        ctx2 = ssl.create_default_context()
        with urllib.request.urlopen(req2, context=ctx2, timeout=8) as r:
            new_data = json.loads(r.read())

        items = new_data if isinstance(new_data, list) else (new_data.get('data') or [])
        result = []
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
            poster = c.get('poster', '') or c.get('banner', '') or ''
            title = (c.get('cn_title', '') or c.get('title', '') or c_code)
            result.append({
                'id': c_code,
                'tmdb_id': None,
                'title': title,
                'poster_path': poster,
                'backdrop_path': c.get('banner', '') or '',
                'overview': '',
                'vote_average': 0,
                'source': 'bytemuse',
                'type': '电影',
                'year': (c.get('create_time', '') or '')[:4],
                'media_id': c_code,
                'mediaid_prefix': 'metatube_search',
            })
        return result
    except Exception:
        return []
