from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class MetatubeMovie(BaseModel):
    """Metatube 电影搜索结果"""
    id: str = Field(default="", description="电影ID")
    number: str = Field(default="", description="番号")
    title: str = Field(default="", description="标题")
    provider: str = Field(default="", description="数据来源")
    homepage: str = Field(default="", description="主页链接")
    thumb_url: str = Field(default="", alias="thumb_url", description="缩略图URL")
    cover_url: str = Field(default="", alias="cover_url", description="封面URL")
    score: float = Field(default=0.0, description="评分")
    actors: List[str] = Field(default_factory=list, description="演员列表")
    release_date: Optional[str] = Field(default=None, alias="release_date", description="发布日期")

    class Config:
        populate_by_name = True


class MetatubeSearchResponse(BaseModel):
    """Metatube 搜索响应"""
    data: List[MetatubeMovie] = Field(default_factory=list)


class MetatubeMovieDetail(BaseModel):
    """Metatube 电影详情"""
    id: str = Field(default="", description="电影ID")
    number: str = Field(default="", description="番号")
    title: str = Field(default="", description="标题")
    provider: str = Field(default="", description="数据来源")
    homepage: str = Field(default="", description="主页链接")
    thumb_url: str = Field(default="", alias="thumb_url", description="缩略图URL")
    cover_url: str = Field(default="", alias="cover_url", description="封面URL")
    poster_url: str = Field(default="", alias="poster_url", description="海报URL")
    score: float = Field(default=0.0, description="评分")
    actors: List[str] = Field(default_factory=list, description="演员列表")
    release_date: Optional[str] = Field(default=None, alias="release_date", description="发布日期")
    runtime: Optional[int] = Field(default=None, description="时长(分钟)")
    director: str = Field(default="", description="导演")
    studio: str = Field(default="", description="制作商")
    label: str = Field(default="", description="发行商")
    series: str = Field(default="", description="系列")
    genres: List[str] = Field(default_factory=list, description="类型标签")
    summary: str = Field(default="", description="简介")
    images: List[str] = Field(default_factory=list, description="预览图列表")

    class Config:
        populate_by_name = True


class MetatubeDetailResponse(BaseModel):
    """Metatube 详情响应"""
    data: Optional[MetatubeMovieDetail] = None


class LogEntry(BaseModel):
    """日志条目"""
    timestamp: str = Field(default="", description="时间戳")
    level: str = Field(default="INFO", description="日志级别")
    keyword: str = Field(default="", description="搜索关键词")
    result: str = Field(default="", description="识别结果")
    category: str = Field(default="", description="分类")
    status: str = Field(default="", description="状态: success/failed")
    message: str = Field(default="", description="详细信息")


# ==================== ThePornDB 数据模型 ====================
# 移植自 Jellyfin.Plugin.ThePornDB

class ThePornDBImage(BaseModel):
    """ThePornDB 图片"""
    url: str = Field(default="", description="图片URL")
    large: str = Field(default="", description="大图URL")

    class Config:
        populate_by_name = True


class ThePornDBSite(BaseModel):
    """ThePornDB 站点信息"""
    id: Optional[int] = Field(default=None, description="站点ID")
    name: str = Field(default="", description="站点名称")
    logo: str = Field(default="", description="站点Logo")
    parent_id: Optional[int] = Field(default=None, alias="parent_id", description="父站点ID")
    network_id: Optional[int] = Field(default=None, alias="network_id", description="网络ID")

    class Config:
        populate_by_name = True


class ThePornDBPerformerExtras(BaseModel):
    """ThePornDB 演员额外信息"""
    gender: str = Field(default="", description="性别")
    birthday: str = Field(default="", description="生日")
    birthplace: str = Field(default="", description="出生地")

    class Config:
        populate_by_name = True


class ThePornDBPerformer(BaseModel):
    """ThePornDB 演员"""
    uuid: str = Field(default="", description="演员UUID")
    name: str = Field(default="", description="演员名称")
    face: str = Field(default="", description="头像URL")
    image: str = Field(default="", description="图片URL")
    extras: ThePornDBPerformerExtras = Field(default_factory=ThePornDBPerformerExtras, description="额外信息")

    class Config:
        populate_by_name = True


class ThePornDBTag(BaseModel):
    """ThePornDB 标签"""
    id: Optional[int] = Field(default=None, description="标签ID")
    name: str = Field(default="", description="标签名称")

    class Config:
        populate_by_name = True


class ThePornDBScene(BaseModel):
    """ThePornDB 场景搜索结果"""
    uuid: str = Field(default="", description="场景UUID")
    title: str = Field(default="", description="标题")
    slug: str = Field(default="", description="Slug")
    date: Optional[str] = Field(default=None, description="日期")
    poster: str = Field(default="", description="海报URL")
    url: str = Field(default="", description="页面URL")

    class Config:
        populate_by_name = True


class ThePornDBSearchResponse(BaseModel):
    """ThePornDB 搜索响应"""
    data: List[ThePornDBScene] = Field(default_factory=list)


class ThePornDBSceneDetail(BaseModel):
    """ThePornDB 场景详情"""
    uuid: str = Field(default="", description="场景UUID")
    title: str = Field(default="", description="标题")
    slug: str = Field(default="", description="Slug")
    description: str = Field(default="", description="描述")
    date: Optional[str] = Field(default=None, description="日期")
    trailer: str = Field(default="", description="预告片URL")
    duration: Optional[int] = Field(default=None, description="时长(秒)")
    poster: str = Field(default="", alias="poster", description="海报URL")
    posters: ThePornDBImage = Field(default_factory=ThePornDBImage, description="海报图片")
    background: ThePornDBImage = Field(default_factory=ThePornDBImage, description="背景图片")
    site: ThePornDBSite = Field(default_factory=ThePornDBSite, description="站点信息")
    performers: List[ThePornDBPerformer] = Field(default_factory=list, description="演员列表")
    tags: List[ThePornDBTag] = Field(default_factory=list, description="标签列表")

    class Config:
        populate_by_name = True


class ThePornDBDetailResponse(BaseModel):
    """ThePornDB 详情响应"""
    data: Optional[ThePornDBSceneDetail] = None


# ==================== ThePornDB JAV 数据模型 ====================

class ThePornDBJAVBackground(BaseModel):
    """ThePornDB JAV 背景图"""
    full: str = Field(default="", description="完整URL")
    large: str = Field(default="", description="大图URL")
    medium: str = Field(default="", description="中图URL")
    small: str = Field(default="", description="小图URL")
    thumb: Optional[str] = Field(default=None, description="缩略图URL")
    url: str = Field(default="", description="原始URL")

    class Config:
        populate_by_name = True


class ThePornDBJAVPerformer(BaseModel):
    """ThePornDB JAV 演员"""
    id: str = Field(default="", description="演员ID")
    name: str = Field(default="", description="演员名称")
    gender: Optional[str] = Field(default=None, description="性别")
    link: str = Field(default="", description="演员链接")
    image: Optional[str] = Field(default=None, description="演员图片")
    face: Optional[str] = Field(default=None, description="演员头像")

    class Config:
        populate_by_name = True


class ThePornDBJAVSite(BaseModel):
    """ThePornDB JAV 站点信息"""
    id: int = Field(default=0, description="站点ID")
    name: str = Field(default="", description="站点名称")
    short_name: str = Field(default="", description="站点短名称")
    url: str = Field(default="", description="站点URL")
    logo: Optional[str] = Field(default=None, description="站点Logo")
    favicon: Optional[str] = Field(default=None, description="站点图标")

    class Config:
        populate_by_name = True


class ThePornDBJAV(BaseModel):
    """ThePornDB JAV 搜索结果"""
    id: str = Field(default="", description="JAV ID (UUID)")
    _id: int = Field(default=0, alias="_id", description="内部ID")
    title: str = Field(default="", description="标题")
    type: str = Field(default="JAV", description="类型")
    slug: str = Field(default="", description="Slug")
    external_id: str = Field(default="", alias="external_id", description="外部ID(番号)")
    date: Optional[str] = Field(default=None, description="发布日期")
    duration: Optional[int] = Field(default=None, description="时长(秒)")
    background: ThePornDBJAVBackground = Field(default_factory=ThePornDBJAVBackground, description="背景图")
    poster: str = Field(default="", description="海报URL")
    link: str = Field(default="", description="页面链接")
    performers: List[ThePornDBJAVPerformer] = Field(default_factory=list, description="演员列表")
    site: ThePornDBJAVSite = Field(default_factory=ThePornDBJAVSite, description="站点信息")

    class Config:
        populate_by_name = True


class ThePornDBJAVDetail(BaseModel):
    """ThePornDB JAV 详情"""
    id: str = Field(default="", description="JAV ID")
    title: str = Field(default="", description="标题")
    type: str = Field(default="JAV", description="类型")
    slug: str = Field(default="", description="Slug")
    external_id: str = Field(default="", alias="external_id", description="外部ID(番号)")
    description: str = Field(default="", description="描述")
    date: Optional[str] = Field(default=None, description="发布日期")
    duration: Optional[int] = Field(default=None, description="时长(秒)")
    poster: str = Field(default="", description="海报URL")
    background: ThePornDBJAVBackground = Field(default_factory=ThePornDBJAVBackground, description="背景图")
    performers: List[ThePornDBJAVPerformer] = Field(default_factory=list, description="演员列表")
    site: ThePornDBJAVSite = Field(default_factory=ThePornDBJAVSite, description="站点信息")
    tags: List[ThePornDBTag] = Field(default_factory=list, description="标签列表")
    directors: List[Dict] = Field(default_factory=list, description="导演列表")

    class Config:
        populate_by_name = True


# ==================== Byte-Muse 数据模型 ====================

class ByteMuseActor(BaseModel):
    """Byte-Muse 演员"""
    name: str = Field(default="", description="演员名称")
    photo: str = Field(default="", description="演员照片URL")
    update_time: Optional[str] = Field(default=None, description="更新时间")
    create_time: Optional[str] = Field(default=None, description="创建时间")
    limit_date: Optional[str] = Field(default=None, description="限制日期")

    class Config:
        populate_by_name = True


class ByteMuseMovie(BaseModel):
    """Byte-Muse 电影搜索结果"""
    code: str = Field(default="", description="番号")
    title: str = Field(default="", description="标题")
    cn_title: Optional[str] = Field(default=None, alias="cn_title", description="中文标题")
    poster: str = Field(default="", description="海报URL")
    banner: str = Field(default="", description="横幅URL")
    still_photo: str = Field(default="", alias="still_photo", description="剧照URL列表(逗号分隔)")
    preview_url: str = Field(default="", alias="preview_url", description="预览视频URL")
    publisher: str = Field(default="", description="发行商")
    producer: str = Field(default="", description="制作商")
    series: str = Field(default="", description="系列")
    casts: str = Field(default="", description="演员列表(逗号分隔)")
    release_date: Optional[str] = Field(default=None, alias="release_date", description="发布日期")
    duration: Optional[int] = Field(default=None, description="时长(分钟)")
    genres: str = Field(default="", description="类型标签(逗号分隔)")
    status: str = Field(default="", description="状态")
    mode: str = Field(default="", description="匹配模式")
    star: Optional[str] = Field(default=None, description="评分")
    is_exist_server: bool = Field(default=False, alias="is_exist_server", description="服务器是否存在")
    create_time: Optional[str] = Field(default=None, description="创建时间")
    update_time: Optional[str] = Field(default=None, description="更新时间")

    class Config:
        populate_by_name = True


class ByteMuseSearchData(BaseModel):
    """Byte-Muse 搜索数据"""
    codes: List[ByteMuseMovie] = Field(default_factory=list, description="电影列表")
    actors: List[ByteMuseActor] = Field(default_factory=list, description="演员列表")


class ByteMuseSearchResponse(BaseModel):
    """Byte-Muse 搜索响应"""
    success: bool = Field(default=False, description="是否成功")
    message: str = Field(default="", description="响应消息")
    data: Optional[ByteMuseSearchData] = Field(default=None, description="响应数据")

    class Config:
        populate_by_name = True
