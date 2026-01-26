from typing import Optional, List
from pydantic import BaseModel, Field


class MetatubeMovie(BaseModel):
    """Metatube 电影信息"""
    id: str = Field(..., description="唯一ID")
    number: str = Field(..., description="番号")
    title: str = Field(..., description="标题")
    provider: str = Field(..., description="提供者")
    homepage: str = Field(..., description="主页链接")
    thumb_url: Optional[str] = Field(None, description="缩略图URL")
    cover_url: Optional[str] = Field(None, description="封面图URL")
    score: float = Field(0.0, description="评分")
    actors: List[str] = Field(default_factory=list, description="演员列表")
    release_date: Optional[str] = Field(None, description="发布日期")


class MetatubeSearchResponse(BaseModel):
    """Metatube 搜索响应"""
    data: List[MetatubeMovie] = Field(default_factory=list, description="搜索结果列表")
