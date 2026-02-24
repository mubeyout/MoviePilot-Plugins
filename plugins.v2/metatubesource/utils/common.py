# Category: 工具
"""
Metatube 工具函数
"""
import re
from typing import Optional, List, Dict, Any
from ..models.base import MediaInfo, NamingTemplate

class NumberExtractor:
    """番号提取器"""

    @staticmethod
    def extract_number(filename: str) -> Optional[str]:
        """从文件名中提取番号"""
        if not filename:
            return None

        # 清理文件名
        name = filename.upper().strip()

        # 移除常见的无关前缀和后缀
        name = re.sub(r'\[.*?\]', ' ', name)
        name = re.sub(r'\(.*?\)', ' ', name)
        name = re.sub(r'[@＠].*', '', name)

        # 番号正则表达式列表（按优先级排序）
        number_patterns = [
            # FC2 系列
            r'(FC2)[-_]?(PPV)?[-_]?(\d{5,7})',
            # HEYZO 系列
            r'(HEYZO)[-_]?(\d{4})',
            # Tokyo Hot 系列
            r'([nNK]|K|KD)[-_]?(\d{4,5})',
            # 主流标准格式
            r'([A-Z]{2,10})[-_]?(\d{2,5})',
            # 素人/单体系列
            r'(10MUSUME|10MU)[-_]?(\d{2,4})',
            r'(PACO|PACOPACO)[-_]?(\d{3,5})',
            r'(XXX[-_]?AV|AV)[-_]?(\d{5})',
            # 网站系列
            r'(CARIB|CARIBPR|CARIBBEANCOM)[-_]?(\d{6})[-_]?(\d{3})',
            r'(\d{6})[_-](\d{3})',
            r'(S2M|SKY|SKYHIGH)[-_]?(\d{3,4})',
            r'(RED|REDHOT)[-_]?(\d{3})',
            # 数字编号系列
            r'(H\d{4})[-_]?(\d{3})',
            r'(C\d{4})[-_]?(\d{3})',
            r'(\d{6})[-_](\d{3})',
            # 特殊厂商
            r'(KIN8|TENGOKU|ENG)[-_]?(\d{3,5})',
            r'(GOLD)[-_]?(\d{3,4})',
            r'(CWP)[-_]?(\d{3,5})',
            r'(ABP|ABW|BKSP)[-_]?(\d{3,4})',
            r'(SSIS|STARS|SSND|SNIS)[-_]?(\d{3,4})',
            r'(IPX|IPZ|IPZZ|MIAE|MIRD)[-_]?(\d{3,4})',
            r'(EBOD|EBODY)[-_]?(\d{3,4})',
            r'(WANZ|WAAA)[-_]?(\d{3,4})',
            # VR系列
            r'(VR|3DVR|VRVR)[-_]?(\d{3,5})',
            # 欧美系列
            r'(RK)[-_]?(\d{4,5})',
            r'(XEMPIRE|DARKX|EROTICAX|HARDX|LESBIANX)[-_]?(\d{3,5})',
            r'(21SEXTURY|21NATURALS|21FOOTART|21EROTICA)[-_]?(\d{3,5})',
            # 中文系列
            r'(MDTV|MDX|MD|JD)[-_]?(\d{3,4})',
            # 复合格式
            r'([A-Z]{2,6})[-_]?(\d{3,5})[-_]?([A-Z]{0,4})',
            r'(\d{5,6})[-_](\d{3})',
        ]

        for pattern in number_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return f"{groups[0]}-{groups[1]}".upper()
                elif len(groups) == 3:
                    if groups[0] == 'FC2':
                        if groups[1]:
                            return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()
                        else:
                            return f"{groups[0]}-{groups[2]}".upper()
                    elif groups[0] in ['CARIB', 'CARIBPR', 'CARIBBEANCOM']:
                        return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()
                    elif groups[1] is None or groups[1] == '':
                        return f"{groups[0]}-{groups[2]}".upper()
                    else:
                        return f"{groups[0]}-{groups[1]}-{groups[2]}".upper()

        return None

    @staticmethod
    def normalize_number(number: str) -> str:
        """标准化番号格式"""
        if not number:
            return ""

        # 转大写并清理空格
        number = number.upper().strip()

        # 替换全角字符
        number = number.replace('－', '-').replace('＿', '_')

        return number

class NamingTemplateEngine:
    """命名模板引擎"""

    def __init__(self):
        self.templates = {
            "number_actor_studio": NamingTemplate(
                template="{number} {actor} [{studio}]",
                label="番号 演员 [片商]",
                variables=["number", "actor", "studio"]
            ),
            "number_actor": NamingTemplate(
                template="{number} {actor}",
                label="番号 演员",
                variables=["number", "actor"]
            ),
            "number_studio_actor": NamingTemplate(
                template="{number} [{studio}] {actor}",
                label="番号 [片商] 演员",
                variables=["number", "studio", "actor"]
            ),
            "number_only": NamingTemplate(
                template="{number}",
                label="仅番号",
                variables=["number"]
            ),
            "number_year": NamingTemplate(
                template="{number} ({year})",
                label="番号 (年份)",
                variables=["number", "year"]
            ),
            "number_actor_year": NamingTemplate(
                template="{number} {actor} ({year})",
                label="番号 演员 (年份)",
                variables=["number", "actor", "year"]
            ),
            "full": NamingTemplate(
                template="{number} {actor} [{studio}] ({year})",
                label="完整格式",
                variables=["number", "actor", "studio", "year"]
            ),
            "custom": NamingTemplate(
                template="",
                label="自定义模板",
                variables=[]
            )
        }

    def get_template(self, template_name: str) -> NamingTemplate:
        """获取命名模板"""
        return self.templates.get(template_name, self.templates["number_actor_year"])

    def apply_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """应用命名模板"""
        template = self.get_template(template_name)
        if not template.template:
            return ""

        # 限制演员数量
        max_actors = data.get('max_actors', 2)
        actors = data.get('actors', [])
        if len(actors) > max_actors:
            actors = actors[:max_actors] + [f"+{len(actors) - max_actors}"]

        # 构建变量映射
        variables = {
            'number': data.get('number', ''),
            'actor': ', '.join(actors) if actors else '',
            'studio': data.get('studio', ''),
            'year': data.get('year', ''),
            'title': data.get('title', ''),
            'series': data.get('series', '')
        }

        # 应用模板
        try:
            return template.template.format(**variables)
        except (KeyError, ValueError) as e:
            print(f"应用命名模板失败: {str(e)}")
            return data.get('number', '')

    def get_template_labels(self) -> Dict[str, str]:
        """获取模板标签"""
        return {name: template.label for name, template in self.templates.items()}

class MediaInfoConverter:
    """媒体信息转换器"""

    @staticmethod
    def to_dict(mediainfo: MediaInfo) -> Dict[str, Any]:
        """将 MediaInfo 转换为字典"""
        return {
            'source': mediainfo.source,
            'type': mediainfo.type.value if mediainfo.type else '',
            'title': mediainfo.title,
            'original_title': mediainfo.original_title,
            'imdb_id': mediainfo.imdb_id,
            'tmdb_id': mediainfo.tmdb_id,
            'douban_id': mediainfo.douban_id,
            'category': mediainfo.category,
            'year': mediainfo.year,
            'description': mediainfo.description,
            'poster': mediainfo.poster,
            'backdrop': mediainfo.backdrop,
            'actors': mediainfo.actors,
            'directors': mediainfo.directors,
            'studios': mediainfo.studios,
            'genres': mediainfo.genres,
            'tags': mediainfo.tags,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> MediaInfo:
        """从字典创建 MediaInfo"""
        mediainfo = MediaInfo()
        mediainfo.source = data.get('source', '')
        mediainfo.type = MediaType(data.get('type', 'movie'))
        mediainfo.title = data.get('title', '')
        mediainfo.original_title = data.get('original_title', '')
        mediainfo.imdb_id = data.get('imdb_id', '')
        mediainfo.tmdb_id = data.get('tmdb_id')
        mediainfo.douban_id = data.get('douban_id', '')
        mediainfo.category = data.get('category', '')
        mediainfo.year = data.get('year')
        mediainfo.description = data.get('description', '')
        mediainfo.poster = data.get('poster', '')
        mediainfo.backdrop = data.get('backdrop', '')
        mediainfo.actors = data.get('actors', [])
        mediainfo.directors = data.get('directors', [])
        mediainfo.studios = data.get('studios', [])
        mediainfo.genres = data.get('genres', [])
        mediainfo.tags = data.get('tags', [])
        return mediainfo

class LogUtils:
    """日志工具"""

    @staticmethod
    def format_log_entry(entry: Any) -> str:
        """格式化日志条目"""
        if hasattr(entry, 'to_dict'):
            entry = entry.to_dict()
        return f"[{entry.get('timestamp', '')}] [{entry.get('level', '')}] {entry.get('message', '')}"

    @staticmethod
    def filter_logs_by_level(logs: List[Any], level: str) -> List[Any]:
        """按级别过滤日志"""
        return [log for log in logs if log.get('level', '').upper() == level.upper()]

    @staticmethod
    def get_latest_logs(logs: List[Any], count: int = 10) -> List[Any]:
        """获取最新日志"""
        return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:count]