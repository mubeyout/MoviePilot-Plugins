"""
ByteMuse 数据模型
"""
from typing import Optional, List
from pydantic import BaseModel, Field


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
