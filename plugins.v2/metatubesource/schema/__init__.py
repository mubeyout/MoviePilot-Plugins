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
    status: str = Field(default="", description="状态: success/failed")
    message: str = Field(default="", description="详细信息")
