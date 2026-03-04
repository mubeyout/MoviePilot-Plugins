"""
ByteMuseServices - ByteMuse探索服务聚合模块

基于 ByteMuse API 的探索数据源插件
提供演员、上新、推荐、榜单、厂牌、搜索等探索服务
"""
from typing import Any, List, Dict, Tuple, Optional
from app.plugins import _PluginBase
from app.core.event import eventmanager, Event
from app.schemas.types import ChainEventType, MediaType
from app.schemas import DiscoverSourceEventData, MediaInfo
from app.core.meta import MetaBase
from app.log import logger

# 导入子模块
from .modules import (
    actors,
    new_releases,
    recommendations,
    rankings,
    studios,
    search
)

MODULE_LABELS = {
    "actors": "演员",
    "new_releases": "上新",
    "recommendations": "推荐",
    "rankings": "榜单",
    "studios": "厂牌",
    "search": "搜索",
}


class ByteMuseServices(_PluginBase):
    # 插件名称
    plugin_name = "ByteMuse探索服务聚合"
    # 插件描述
    plugin_desc = "基于 ByteMuse API 的探索数据源插件，提供演员、上新、推荐、榜单、厂牌、搜索等探索服务。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/KoWming/MoviePilot-Plugins/main/icons/ExploreServices.png"
    # 插件版本
    plugin_version = "2.9.6"
    # 插件作者
    plugin_author = "Mubey"
    # 作者主页
    author_url = "https://github.com/mubey"
    # 插件配置项ID前缀
    plugin_config_prefix = "bytemuseservices_"
    # 加载顺序
    plugin_order = 13
    # 可使用的用户级别
    auth_level = 1

    # 子模块注册表
    modules = {
        "actors": actors,
        "new_releases": new_releases,
        "recommendations": recommendations,
        "rankings": rankings,
        "studios": studios,
        "search": search,
    }
    enabled_modules: Dict[str, bool] = {}

    # ThePornDB API 配置
    _theporndb_api_token: str = ""

    # ByteMuse API 配置
    _bytemuse_base_url: str = "http://10.0.0.1:3750"
    _bytemuse_username: str = "mubey"
    _bytemuse_password: str = "355492"

    # Metatube API 配置
    _metatube_base_url: str = "http://10.0.0.1:3244"

    def init_plugin(self, config: dict = None):
        if config:
            # 读取模块开关配置
            for name in self.modules:
                self.enabled_modules[name] = config.get(f"{name}_enabled", False)

            # 读取 ThePornDB API 配置
            self._theporndb_api_token = config.get("theporndb_api_token", "")

            # 读取 ByteMuse API 配置
            self._bytemuse_base_url = config.get("bytemuse_base_url", "http://10.0.0.1:3750")
            self._bytemuse_username = config.get("bytemuse_username", "mubey")
            self._bytemuse_password = config.get("bytemuse_password", "355492")

            # 读取 Metatube API 配置
            self._metatube_base_url = config.get("metatube_base_url", "http://10.0.0.1:3244")
        else:
            for name in self.modules:
                self.enabled_modules[name] = False

        logger.info(f"ByteMuseServices 插件初始化完成，已启用模块: {[name for name, enabled in self.enabled_modules.items() if enabled]}")

    def get_state(self) -> bool:
        return any(self.enabled_modules.values())

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        plugin_names = "、".join(MODULE_LABELS.values())
        form = [
            {
                "component": "VForm",
                "content": [
                    # 探索源开关
                    {
                        "component": "VCard",
                        "props": {"class": "mt-0"},
                        "content": [
                            {
                                "component": "VCardTitle",
                                "props": {"class": "d-flex align-center"},
                                "content": [
                                    {
                                        "component": "VIcon",
                                        "props": {"style": "color: #16b1ff;", "class": "mr-2"},
                                        "text": "mdi-compass-outline"
                                    },
                                    {
                                        "component": "span",
                                        "text": "探索源开关"
                                    }
                                ]
                            },
                            {"component": "VDivider"},
                            {
                                "component": "VCardText",
                                "content": [
                                    {
                                        "component": "VRow",
                                        "content": [
                                            {
                                                "component": "VCol",
                                                "props": {"cols": 12, "sm": 6, "md": 4},
                                                "content": [
                                                    {
                                                        "component": "VSwitch",
                                                        "props": {
                                                            "model": f"{name}_enabled",
                                                            "label": f"{MODULE_LABELS.get(name, name)}",
                                                        },
                                                    }
                                                ],
                                            }
                                            for name in self.modules
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    # API 配置
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mt-3',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {
                                    'class': 'px-6 pb-0'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-2'
                                                },
                                                'text': 'mdi-api'
                                            },
                                            {
                                                'component': 'span',
                                                'text': 'API 配置'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider'
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6'
                                },
                                'content': [
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            # ThePornDB Token
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'theporndb_api_token',
                                                            'label': 'ThePornDB Token',
                                                            'placeholder': '请输入API Token',
                                                            'variant': 'outlined',
                                                            'density': 'compact',
                                                        }
                                                    }
                                                ]
                                            },
                                            # ByteMuse 地址
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'bytemuse_base_url',
                                                            'label': 'ByteMuse 地址',
                                                            'placeholder': 'http://10.0.0.1:3750',
                                                            'variant': 'outlined',
                                                            'density': 'compact',
                                                        }
                                                    }
                                                ]
                                            },
                                            # ByteMuse 用户名
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'bytemuse_username',
                                                            'label': 'ByteMuse 用户名',
                                                            'placeholder': 'mubey',
                                                            'variant': 'outlined',
                                                            'density': 'compact',
                                                        }
                                                    }
                                                ]
                                            },
                                            # ByteMuse 密码
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'bytemuse_password',
                                                            'label': 'ByteMuse 密码',
                                                            'placeholder': '••••••',
                                                            'variant': 'outlined',
                                                            'density': 'compact',
                                                            'type': 'password',
                                                        }
                                                    }
                                                ]
                                            },
                                            # Metatube 地址
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'sm': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'metatube_base_url',
                                                            'label': 'Metatube 地址',
                                                            'placeholder': 'http://10.0.0.1:3244',
                                                            'variant': 'outlined',
                                                            'density': 'compact',
                                                        }
                                                    }
                                                ]
                                            },
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    # 使用说明
                    {
                        'component': 'VCard',
                        'props': {
                            'variant': 'flat',
                            'class': 'mt-3',
                            'color': 'surface'
                        },
                        'content': [
                            {
                                'component': 'VCardItem',
                                'props': {
                                    'class': 'px-6 pb-0'
                                },
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'props': {
                                            'class': 'd-flex align-center text-h6'
                                        },
                                        'content': [
                                            {
                                                'component': 'VIcon',
                                                'props': {
                                                    'style': 'color: #16b1ff;',
                                                    'class': 'mr-2'
                                                },
                                                'text': 'mdi-information'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '使用说明'
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                'component': 'VDivider'
                            },
                            {
                                'component': 'VCardText',
                                'props': {
                                    'class': 'px-6'
                                },
                                'content': [
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1'
                                        },
                                        'text': '开启对应探索服务将在MoviePilot探索服务中展示对应探索页面，可根据需要进行开启。'
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1 mt-2'
                                        },
                                        'text': f'当前聚合模块：{plugin_names}'
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1 mt-2'
                                        },
                                        'content': [
                                            {
                                                'component': 'span',
                                                'text': '数据源: '
                                            },
                                            {
                                                'component': 'a',
                                                'props': {
                                                    'href': 'https://theporndb.net',
                                                    'target': '_blank',
                                                    'style': 'color: #16b1ff; text-decoration: underline;'
                                                },
                                                'text': 'ThePornDB'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '、'
                                            },
                                            {
                                                'component': 'a',
                                                'props': {
                                                    'href': 'https://github.com/ByteDance/ByteMuse',
                                                    'target': '_blank',
                                                    'style': 'color: #16b1ff; text-decoration: underline;'
                                                },
                                                'text': 'ByteMuse'
                                            },
                                            {
                                                'component': 'span',
                                                'text': '、'
                                            },
                                            {
                                                'component': 'a',
                                                'props': {
                                                    'href': 'https://github.com/xxxhcm2019/metatube',
                                                    'target': '_blank',
                                                    'style': 'color: #16b1ff; text-decoration: underline;'
                                                },
                                                'text': 'Metatube'
                                            },
                                        ]
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-1 mt-2'
                                        },
                                        'text': 'API 端点结构:'
                                    },
                                    {
                                        'component': 'div',
                                        'props': {
                                            'class': 'text-body-2 mt-1'
                                        },
                                        'content': [
                                            {
                                                'component': 'ul',
                                                'props': {'class': 'ml-4'},
                                                'content': [
                                                    {'component': 'li', 'text': '/bytemuse_actors - 演员（订阅中/热门）'},
                                                    {'component': 'li', 'text': '/bytemuse_new_releases - 上新'},
                                                    {'component': 'li', 'text': '/bytemuse_recommendations - 推荐'},
                                                    {'component': 'li', 'text': '/bytemuse_rankings - 榜单（JavDB日榜/周榜/月榜、JavLibrary）'},
                                                    {'component': 'li', 'text': '/bytemuse_studios - 厂牌（9个厂牌）'},
                                                    {'component': 'li', 'text': '/bytemuse_search - 搜索（ThePornDB/ByteMuse/Metatube）'},
                                                ]
                                            }
                                        ]
                                    },
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        default_data = {
            f"{name}_enabled": False for name in self.modules
        }
        default_data.update({
            "theporndb_api_token": "",
            "bytemuse_base_url": "http://10.0.0.1:3750",
            "bytemuse_username": "mubey",
            "bytemuse_password": "355492",
            "metatube_base_url": "http://10.0.0.1:3244",
        })
        return form, default_data

    def get_api(self) -> List[Dict[str, Any]]:
        """获取API列表"""
        apis = []
        for name, mod in self.modules.items():
            if self.enabled_modules.get(name):
                module_apis = mod.get_api(self)
                if module_apis:
                    apis.extend(module_apis)
        return apis

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """注册探索源事件"""
        event_data: DiscoverSourceEventData = event.event_data
        for name, mod in self.modules.items():
            if self.enabled_modules.get(name):
                try:
                    mod.discover_source(self, event_data)
                except Exception as e:
                    logger.error(f"注册 {name} 探索源失败: {str(e)}")

    def stop_service(self):
        """停止服务"""
        for name, mod in self.modules.items():
            if hasattr(mod, "stop_service"):
                try:
                    mod.stop_service()
                except Exception as e:
                    logger.error(f"停止 {name} 模块服务失败: {str(e)}")

    # ===== 属性访问器 =====

    @property
    def theporndb_api_token(self) -> str:
        return self._theporndb_api_token

    @property
    def bytemuse_base_url(self) -> str:
        return self._bytemuse_base_url

    @property
    def bytemuse_username(self) -> str:
        return self._bytemuse_username

    @property
    def bytemuse_password(self) -> str:
        return self._bytemuse_password

    @property
    def metatube_base_url(self) -> str:
        return self._metatube_base_url

    def recognize_media(self, meta: MetaBase = None,
                        mtype: MediaType = None,
                        **kwargs) -> Optional[MediaInfo]:
        """
        识别媒体信息（处理 ByteMuse mediaid 点击）

        :param meta: 识别的元数据
        :param mtype: 识别的媒体类型
        :return: 识别的媒体信息
        """
        # 调试日志：打印所有接收到的参数
        logger.info(f"recognize_media 被调用: meta={meta}, mtype={mtype}, kwargs keys={list(kwargs.keys())}")

        if not meta:
            logger.warning("recognize_media: meta 为空，返回 None")
            return None

        # 从 kwargs 中获取 mediaid 信息
        mediaid = kwargs.get("mediaid", "")

        logger.info(f"recognize_media: mediaid={mediaid}, meta.org_string={meta.org_string}")

        if not mediaid or mediaid.endswith(":"):
            # 如果没有 mediaid 或 mediaid 为空（如 "bytemuse_search:"），尝试从 meta 中提取番号
            title = meta.org_string or meta.cn_name or meta.en_name or meta.name or ""
            if not title:
                logger.warning("recognize_media: 无法获取番号，meta 为空")
                return None

            # 检查是否是 ThePornDB 的 imdb_id 格式
            imdb_id = kwargs.get("imdb_id", "")
            if imdb_id and imdb_id.startswith("theporndb:"):
                # 从 imdb_id 中提取番号
                code = imdb_id.replace("theporndb:", "", 1)
                logger.info(f"recognize_media: 从 imdb_id 识别 ThePornDB 番号: {code}")
                return self._fetch_theporndb_detail(code)

            # 检查是否是 ByteMuse 的 imdb_id 格式
            if imdb_id and imdb_id.startswith("bytemuse:"):
                # 从 imdb_id 中提取番号
                code = imdb_id.replace("bytemuse:", "", 1)
                logger.info(f"recognize_media: 从 imdb_id 识别 ByteMuse 番号: {code}")
                return self._fetch_bytemuse_detail(code)

            # 使用标题作为番号进行搜索（默认使用 ByteMuse）
            logger.info(f"recognize_media: 使用标题作为番号搜索: {title}")
            return self._fetch_bytemuse_detail(title)

        # 解析 mediaid (格式: bytemuse_xxx:code 或 theporndb_xxx:code)
        if ":" in mediaid:
            prefix, code = mediaid.split(":", 1)
            logger.info(f"recognize_media: 解析 mediaid, prefix={prefix}, code={code}")

            # 检查是否是种子点击
            if prefix == "bytemuse_torrent":
                # 种子点击：触发下载
                logger.info(f"recognize_media: 识别为种子下载")
                return self._handle_torrent_download(code)
            # 检查是否是演员点击
            elif prefix == "bytemuse_actor":
                # 演员点击：返回演员信息（用于显示演员作品列表）
                logger.info(f"recognize_media: 识别为演员点击: {code}")
                return self._fetch_actor_info(code)
            # 检查是否是 ThePornDB JAV
            elif prefix == "theporndb_jav":
                # ThePornDB JAV 点击：获取详情
                logger.info(f"recognize_media: 识别为 ThePornDB JAV: {code}")
                return self._fetch_theporndb_detail(code)
            # 其他 ByteMuse 前缀
            elif prefix.startswith("bytemuse_"):
                logger.info(f"recognize_media: 识别为 ByteMuse 前缀: {prefix}, 番号: {code}")
                return self._fetch_bytemuse_detail(code)

        logger.warning(f"recognize_media: 无法处理的 mediaid 格式: {mediaid}")
        return None

    def _handle_torrent_download(self, magnet_b64: str) -> Optional[MediaInfo]:
        """
        处理种子下载（点击种子时触发）

        :param magnet_b64: base64 编码的磁力链接
        :return: 媒体信息
        """
        import base64
        import requests
        from app.core.config import settings

        try:
            # 解码磁力链接
            magnet = base64.b64decode(magnet_b64).decode()
            logger.info(f"触发种子下载: {magnet[:50]}...")

            # 调用 MoviePilot 的下载 API
            api_url = f"{settings.API_URL}/api/v1/download"
            headers = {
                "Authorization": f"Bearer {settings.API_TOKEN}",
                "Content-Type": "application/json"
            }

            payload = {
                "url": magnet,
                "type": "torrent"
            }

            response = requests.post(api_url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info(f"种子下载添加成功: {magnet[:50]}...")
                return MediaInfo(
                    type="电影",
                    title="✓ 下载已添加",
                    overview="种子已添加到下载队列，请在下载中心查看",
                    poster_path="",
                )
            else:
                logger.warning(f"种子下载添加失败: {response.status_code} - {response.text}")
                return MediaInfo(
                    type="电影",
                    title="✗ 下载失败",
                    overview=f"错误: {response.status_code} - {response.text[:100]}",
                    poster_path="",
                )

        except Exception as err:
            logger.error(f"种子下载失败: {str(err)}")
            return MediaInfo(
                type="电影",
                title="✗ 下载失败",
                overview=f"错误: {str(err)}",
                poster_path="",
            )

    def _fetch_actor_info(self, actor_name: str) -> Optional[MediaInfo]:
        """
        获取演员信息（点击演员时显示）

        :param actor_name: 演员名
        :return: 媒体信息
        """
        if not actor_name:
            return None

        # 返回演员信息，title 设置为演员名
        return MediaInfo(
            type="电视剧",
            title=actor_name,
            mediaid_prefix="bytemuse_actor",
            media_id=actor_name,
            imdb_id=f"bytemuse_actor:{actor_name}",
            overview=f"点击查看 {actor_name} 的作品列表",
        )

    def _fetch_bytemuse_detail(self, code: str) -> Optional[MediaInfo]:
        """
        从 ByteMuse API 获取详情

        :param code: 番号
        :return: 媒体信息
        """
        if not code:
            logger.warning("ByteMuse 详情获取失败: 番号为空")
            return None

        if not self._bytemuse_username or not self._bytemuse_password:
            logger.warning("ByteMuse 详情获取失败: 未配置用户名或密码")
            return None

        try:
            from .bytemuse_api import ByteMuseApiClient
            from .schema import ByteMuseMovie

            logger.info(f"ByteMuse 详情获取: 开始搜索番号 {code}")

            client = ByteMuseApiClient(
                base_url=self._bytemuse_base_url,
                username=self._bytemuse_username,
                password=self._bytemuse_password,
            )

            # 使用搜索接口获取详情
            result = client.search_by_code(query=code)

            if not result:
                logger.warning(f"ByteMuse 详情获取失败: API 未返回结果, code={code}")
                return None

            # 解析返回的数据
            codes = result.get("codes", [])
            if not codes:
                logger.warning(f"ByteMuse 详情获取失败: codes 列表为空, code={code}")
                return None

            # 取第一个匹配结果
            movie_data = codes[0]

            # 转换为 ByteMuseMovie
            movie = ByteMuseMovie(**movie_data)

            logger.info(f"ByteMuse 详情获取成功: {code} -> {movie.title}")

            # 转换为 MediaInfo
            return self._movie_to_media(movie)

        except Exception as err:
            logger.error(f"ByteMuse 详情获取失败: {str(err)}")
            import traceback
            logger.debug(f"ByteMuse 详情获取异常详情: {traceback.format_exc()}")
            return None

    def _movie_to_media(self, movie) -> MediaInfo:
        """
        将 ByteMuseMovie 转换为 MediaInfo

        :param movie: ByteMuseMovie 对象
        :return: MediaInfo 对象
        """
        from .schema import ByteMuseMovie

        if not isinstance(movie, ByteMuseMovie):
            # 如果是字典，先转换为 ByteMuseMovie
            if isinstance(movie, dict):
                movie = ByteMuseMovie(**movie)
            else:
                return MediaInfo()

        # 处理标题 - 只显示番号
        title = movie.code or movie.title or ""

        # 确保 media_id 永远不为空
        if movie.code:
            media_id = movie.code
        elif movie.id:
            media_id = f"bytemuse_{movie.id}"
        else:
            media_id = title or f"unknown_{id(movie)}"

        return MediaInfo(
            type="电影",
            title=title,
            mediaid_prefix="bytemuse",
            media_id=media_id,
            imdb_id=f"bytemuse:{movie.code}" if movie.code else f"bytemuse:{media_id}",  # 用于订阅识别
            poster_path=movie.poster_url or movie.cover_url or movie.thumb_url or "",
            vote_average=movie.score,
            year=movie.release_date[:4] if movie.release_date else None,
            overview=movie.summary or "",
            studio=movie.studio or movie.publisher or "",
        )

    def _fetch_theporndb_detail(self, code: str) -> Optional[MediaInfo]:
        """
        从 ThePornDB API 获取详情

        :param code: 番号
        :return: 媒体信息
        """
        if not code:
            return None

        if not self._theporndb_api_token:
            logger.warning("ThePornDB 详情获取失败: 未配置 API Token")
            return None

        try:
            from .theporndb_api import ThePornDBApiClient
            from .schema import ThePornDBJAVDetail

            client = ThePornDBApiClient(api_token=self._theporndb_api_token)

            # 使用 JAV 详情 API 获取详情
            detail = client.get_jav_detail(code)

            if not detail:
                logger.warning(f"ThePornDB 未找到番号: {code}")
                return None

            logger.info(f"ThePornDB 详情获取成功: {code} -> {detail.title}")

            # 转换为 MediaInfo
            code_value = detail.external_id or ""

            # 提取海报图片
            poster_url = ""
            if detail.background:
                if hasattr(detail.background, 'url') and detail.background.url:
                    poster_url = detail.background.url
                elif hasattr(detail.background, 'large') and detail.background.large:
                    poster_url = detail.background.large

            # 厂牌信息
            studio = ""
            if detail.site:
                if hasattr(detail.site, 'name') and detail.site.name:
                    studio = detail.site.name

            # 年份
            year = None
            if detail.date:
                try:
                    year = detail.date[:4]
                except (IndexError, TypeError):
                    pass

            return MediaInfo(
                type="电影",
                title=code_value if code_value else detail.title[:50],
                mediaid_prefix="theporndb_jav",
                media_id=code_value,
                imdb_id=f"theporndb:{code_value}" if code_value else "",
                poster_path=poster_url,
                vote_average=None,
                year=year,
                overview=detail.description or detail.title or "",
                studio=studio,
            )

        except Exception as err:
            logger.error(f"ThePornDB 详情获取失败: {str(err)}")
            return None
