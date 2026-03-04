"""
ByteMuseServices 数据模型
"""
from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_validator


# ==================== ByteMuse 数据模型 ====================

class ByteMuseActor(BaseModel):
    """ByteMuse 演员"""
    name: str = Field(default="", description="演员名称")
    role: Optional[str] = Field(default=None, description="角色类型")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ByteMuseMovie(BaseModel):
    """ByteMuse 电影搜索结果"""
    id: str = Field(default="", description="电影ID")
    code: str = Field(default="", description="番号")
    title: str = Field(default="", description="标题")
    cn_title: Optional[str] = Field(default=None, description="中文标题")
    actors: List[ByteMuseActor] = Field(default_factory=list, description="演员列表")
    casts: Optional[str] = Field(default=None, description="演员(逗号分隔)")
    studio: Optional[str] = Field(default=None, description="制作商")
    publisher: Optional[str] = Field(default=None, description="发行商")
    label: Optional[str] = Field(default=None, description="标签")
    series: Optional[str] = Field(default=None, description="系列")
    release_date: Optional[str] = Field(default=None, description="发布日期")
    duration: Optional[int] = Field(default=None, description="时长(秒)")
    runtime: Optional[int] = Field(default=None, description="时长(分钟)")
    director: Optional[str] = Field(default=None, description="导演")
    producer: Optional[str] = Field(default=None, description="制片人")
    cover_url: str = Field(default="", alias="banner", description="封面URL")
    poster_url: str = Field(default="", alias="poster", description="海报URL")
    thumb_url: str = Field(default="", description="缩略图URL")
    preview_url: Optional[str] = Field(default=None, description="预览URL")
    still_photo: Optional[str] = Field(default=None, description="剧照")
    score: Optional[float] = Field(default=None, description="评分")
    genres: Optional[str] = Field(default=None, description="类型标签(逗号分隔)")
    summary: str = Field(default="", description="简介")
    images: List[str] = Field(default_factory=list, description="预览图列表")
    # API 返回的额外字段
    create_time: Optional[str] = Field(default=None, description="创建时间")
    update_time: Optional[str] = Field(default=None, description="更新时间")
    status: Optional[str] = Field(default=None, description="状态")
    mode: Optional[str] = Field(default=None, description="模式")
    star: Optional[str] = Field(default=None, description="星标")
    weight: Optional[float] = Field(default=None, description="权重")
    is_exist_server: Optional[bool] = Field(default=None, description="服务器是否存在")

    class Config:
        populate_by_name = True
        extra = 'allow'


# ==================== ThePornDB 数据模型 ====================
# 移植自 Jellyfin.Plugin.ThePornDB

class ThePornDBImage(BaseModel):
    """ThePornDB 图片"""
    url: str = Field(default="", description="图片URL")
    large: str = Field(default="", description="大图URL")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBSite(BaseModel):
    """ThePornDB 站点信息"""
    id: Optional[int] = Field(default=None, description="站点ID")
    name: str = Field(default="", description="站点名称")
    logo: str = Field(default="", description="站点Logo")
    parent_id: Optional[int] = Field(default=None, alias="parent_id", description="父站点ID")
    network_id: Optional[int] = Field(default=None, alias="network_id", description="网络ID")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBPerformerExtras(BaseModel):
    """ThePornDB 演员额外信息"""
    gender: str = Field(default="", description="性别")
    birthday: str = Field(default="", description="生日")
    birthplace: str = Field(default="", description="出生地")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBPerformer(BaseModel):
    """ThePornDB 演员"""
    uuid: str = Field(default="", description="演员UUID")
    name: str = Field(default="", description="演员名称")
    face: str = Field(default="", description="头像URL")
    image: str = Field(default="", description="图片URL")
    extras: ThePornDBPerformerExtras = Field(default_factory=ThePornDBPerformerExtras, description="额外信息")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBTag(BaseModel):
    """ThePornDB 标签"""
    id: Optional[int] = Field(default=None, description="标签ID")
    name: str = Field(default="", description="标签名称")

    class Config:
        populate_by_name = True
        extra = 'allow'


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
        extra = 'allow'


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
        extra = 'allow'


class ThePornDBDetailResponse(BaseModel):
    """ThePornDB 详情响应"""
    data: Optional[ThePornDBSceneDetail] = None


# ==================== ThePornDB JAV 数据模型 ====================

class ThePornDBJAVPerformerExtra(BaseModel):
    """ThePornDB JAV 演员额外信息 (extra 字段)"""
    gender: Optional[str] = Field(default=None, description="性别")
    birthday: Optional[str] = Field(default=None, description="生日")
    birthplace: Optional[str] = Field(default=None, description="出生地")
    birthplace_code: Optional[str] = Field(default=None, description="出生地代码")
    cupsize: Optional[str] = Field(default=None, description="罩杯")
    ethnicity: Optional[str] = Field(default=None, description="种族")
    eye_colour: Optional[str] = Field(default=None, description="眼睛颜色")
    hair_colour: Optional[str] = Field(default=None, description="头发颜色")
    height: Optional[str] = Field(default=None, description="身高")
    measurements: Optional[str] = Field(default=None, description="三围")
    nationality: Optional[str] = Field(default=None, description="国籍")
    weight: Optional[str] = Field(default=None, description="体重")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBJAVPerformerParent(BaseModel):
    """ThePornDB JAV 演员父信息 (parent 字段)"""
    id: str = Field(default="", description="UUID")
    internal_id: int = Field(default=0, alias="_id", description="内部ID")
    slug: str = Field(default="", description="Slug")
    name: str = Field(default="", description="名称")
    full_name: Optional[str] = Field(default=None, description="全名")
    extras: ThePornDBJAVPerformerExtra = Field(default_factory=ThePornDBJAVPerformerExtra, description="额外信息")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBJAVPerformer(BaseModel):
    """ThePornDB JAV 演员"""
    id: str = Field(default="", description="UUID")
    internal_id: int = Field(default=0, alias="_id", description="内部ID")
    slug: str = Field(default="", description="Slug")
    name: str = Field(default="", description="演员名称")
    extra: ThePornDBJAVPerformerExtra = Field(default_factory=ThePornDBJAVPerformerExtra, description="额外信息")
    parent: Optional[ThePornDBJAVPerformerParent] = Field(default=None, description="父信息")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBJAVImage(BaseModel):
    """ThePornDB JAV 图片 (支持 full/large/medium/small)"""
    full: str = Field(default="", description="原图URL")
    large: str = Field(default="", description="大图URL")
    medium: str = Field(default="", description="中图URL")
    small: str = Field(default="", description="小图URL")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBJAVSite(BaseModel):
    """ThePornDB JAV 站点信息"""
    id: Optional[int] = Field(default=None, description="站点ID")
    name: Optional[str] = Field(default=None, description="站点名称")
    url: Optional[str] = Field(default=None, description="站点URL")
    logo: Optional[str] = Field(default=None, description="Logo URL")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBJAVBackground(BaseModel):
    """ThePornDB JAV 背景图片"""
    url: Optional[str] = Field(default=None, description="原图URL")
    large: Optional[str] = Field(default=None, description="大图URL")
    medium: Optional[str] = Field(default=None, description="中图URL")
    small: Optional[str] = Field(default=None, description="小图URL")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBJAVScene(BaseModel):
    """ThePornDB JAV 搜索结果"""
    id: str = Field(default="", description="场景ID (UUID字符串)")
    uuid: Optional[str] = Field(default=None, description="场景UUID (可能不存在)")
    title: str = Field(default="", description="标题")
    slug: Optional[str] = Field(default=None, description="Slug (用于构建详情URL)")
    external_id: Optional[str] = Field(default=None, description="外部ID/番号")
    date: Optional[str] = Field(default=None, description="日期")
    duration: Optional[int] = Field(default=None, description="时长(秒)")
    link: Optional[str] = Field(default=None, description="页面链接")
    type: str = Field(default="JAV", description="类型")
    background: Optional[ThePornDBJAVBackground] = Field(default=None, description="背景图片")
    site: Optional[ThePornDBJAVSite] = Field(default=None, description="站点信息")
    performers: List[ThePornDBJAVPerformer] = Field(default_factory=list, description="演员列表")

    class Config:
        populate_by_name = True
        extra = 'allow'


class ThePornDBJAVSearchResponse(BaseModel):
    """ThePornDB JAV 搜索响应 (HTML 页面嵌入的 JSON)"""
    data: List[ThePornDBJAVScene] = Field(default_factory=list)


class ThePornDBJAVDetail(BaseModel):
    """ThePornDB JAV 详情"""
    id: str = Field(default="", description="UUID")
    internal_id: int = Field(default=0, alias="_id", description="内部ID")
    title: str = Field(default="", description="标题")
    type: str = Field(default="JAV", description="类型")
    slug: str = Field(default="", description="Slug")
    external_id: str = Field(default="", alias="external_id", description="外部ID/番号")
    description: str = Field(default="", description="描述")
    date: Optional[str] = Field(default=None, description="日期")
    duration: Optional[int] = Field(default=None, description="时长(秒)")
    poster: str = Field(default="", description="海报URL")
    posters: ThePornDBJAVImage = Field(default_factory=ThePornDBJAVImage, description="海报图片")
    background: ThePornDBJAVImage = Field(default_factory=ThePornDBJAVImage, description="背景图片")
    site: ThePornDBJAVSite = Field(default_factory=ThePornDBJAVSite, description="站点信息")
    performers: List[ThePornDBJAVPerformer] = Field(default_factory=list, description="演员列表")
    tags: List[ThePornDBTag] = Field(default_factory=list, description="标签列表")
    url: str = Field(default="", description="来源链接")

    class Config:
        populate_by_name = True
        extra = 'allow'
