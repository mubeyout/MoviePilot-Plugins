# __init__.py
#
# This file is based on AGPL-3.0 licensed code.
# Original author: Akimio521 (https://github.com/Akimio521)
# Modifications by: yubanmeiqin9048 (https://github.com/yubanmeiqin9048)
#
# Licensed under the AGPL-3.0 license.
# See the LICENSE file in the / directory for more details.

import asyncio
import traceback
from contextlib import AsyncExitStack
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiofiles.os as aio_os
import pytz
from aiofiles import open as async_open
from aiohttp import ClientSession
from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from plugins.alist2strm.alist import AlistClient, AlistFile
from plugins.alist2strm.filter import BloomCleaner, IoCleaner, SetCleaner


class Alist2Strm(_PluginBase):
    # 插件名称
    plugin_name = "Alist2Strm(高级版)"
    # 插件描述
    plugin_desc = "从alist生成strm，支持多目录，自定义格式。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/mubeyout/MoviePilot-Plugins/main/icons/Alist.png"
    # 插件版本
    plugin_version = "2.0.0"
    # 插件作者
    plugin_author = "mubey"
    # 作者主页
    author_url = "https://github.com/mubeyout"
    # 插件配置项ID前缀
    plugin_config_prefix = "alist2strm_"
    # 加载顺序
    plugin_order = 32
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _url = ""
    _token = ""
    _dir_mappings = ""  # 改为目录映射，格式：源目录#目标目录，每行一个
    _sync_remote = False
    _path_replace = ""
    _url_replace = ""
    _cron = ""
    _scheduler = None
    _onlyonce = False
    # 新增：文件类型配置相关属性
    _video_enabled = True
    _audio_enabled = True
    _other_enabled = False
    _video_suffix = settings.RMT_MEDIAEXT
    _audio_suffix = ".mp3,.flac,.wav,.ogg,.aac,.m4a"
    _other_suffix = ".iso,.img,.bin"
    _max_download_worker = 3
    _max_list_worker = 7
    _max_depth = -1
    _traversal_mode = "bfs"
    _filter_mode = "set"
    processed_remote_paths_in_local: Set[Path] = set()

    def init_plugin(self, config: Optional[dict] = None) -> None:
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._url = config.get("url", "")
            self._token = config.get("token", "")
            self._dir_mappings = config.get("dir_mappings", "")  # 读取目录映射配置
            self._sync_remote = config.get("sync_remote")
            self._cron = config.get("cron")
            self._path_replace = config.get("path_replace", "")
            self._url_replace = config.get("url_replace")
            self._max_download_worker = int(config.get("max_download_worker", 3))
            self._max_list_worker = int(config.get("max_list_worker", 7))
            self._max_depth = config.get("max_depth") or -1
            self._traversal_mode = config.get("traversal_mode") or "bfs"
            self._filter_mode = config.get("filter_mode") or "set"
            # 新增：初始化文件类型配置
            self._video_enabled = config.get("video_enabled", True)
            self._audio_enabled = config.get("audio_enabled", True)
            self._other_enabled = config.get("other_enabled", False)
            self._video_suffix = config.get("video_suffix", ",".join(settings.RMT_MEDIAEXT))
            self._audio_suffix = config.get("audio_suffix", ".mp3,.flac,.wav,.ogg,.aac,.m4a")
            self._other_suffix = config.get("other_suffix", ".iso,.img,.bin")
            self.init_cleaner()
            self.__update_config()

        if self.get_state() or self._onlyonce:
            if self._onlyonce:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                self._scheduler.add_job(
                    self.run_in_scheduler,
                    "date",
                    run_date=datetime.now(tz=pytz.timezone(settings.TZ))
                    + timedelta(seconds=3),
                )
                # 关闭一次性开关
                self._onlyonce = False
                if self._scheduler.get_jobs():
                    self._scheduler.print_jobs()
                    self._scheduler.start()
            self.__update_config()

    def init_cleaner(self) -> None:
        """
        根据 filter_mode 实例化对应的 Cleaner。
        """
        if self._filter_mode == "set":
            use_cleaner = SetCleaner
        elif self._filter_mode == "io":
            use_cleaner = IoCleaner
        elif self._filter_mode == "bf":
            use_cleaner = BloomCleaner
        else:
            raise ValueError(f"未知的过滤模式: {self._filter_mode}")
        # 新增：更新需要处理的后缀列表
        self._process_file_suffix = self.__get_process_suffix() + ["strm"]
        # 初始化清理器时使用所有目标目录的父目录
        target_dirs = [Path(mapping.split('#')[1]) for mapping in self._parse_dir_mappings() if len(mapping.split('#')) == 2]
        if target_dirs:
            # 使用第一个目标目录作为主要清理根目录，实际清理会处理所有映射目录
            self.cleaner = use_cleaner(
                need_suffix=self._process_file_suffix,
                target_dir=target_dirs[0]
            )
        else:
            self.cleaner = use_cleaner(
                need_suffix=self._process_file_suffix,
                target_dir=Path("")
            )

    def _parse_dir_mappings(self) -> List[str]:
        """解析目录映射配置，返回非空且格式正确的映射列表"""
        mappings = []
        if not self._dir_mappings:
            return mappings
        for line in self._dir_mappings.splitlines():
            line = line.strip()
            if line and '#' in line:
                mappings.append(line)
        return mappings

    def __get_process_suffix(self) -> List[str]:
        """获取需要处理的文件后缀列表"""
        suffix_list = []
        # 处理视频后缀
        if self._video_enabled and self._video_suffix:
            suffix_list.extend([s.lower().strip() for s in self._video_suffix.split(',') if s.strip()])
        # 处理音频后缀
        if self._audio_enabled and self._audio_suffix:
            suffix_list.extend([s.lower().strip() for s in self._audio_suffix.split(',') if s.strip()])
        # 处理其他后缀
        if self._other_enabled and self._other_suffix:
            suffix_list.extend([s.lower().strip() for s in self._other_suffix.split(',') if s.strip()])
        # 添加上字幕后缀
        suffix_list.extend(settings.RMT_SUBEXT)
        return list(set(suffix_list))

    def run_in_scheduler(self) -> None:
        asyncio.run(self.alist2strm())

    async def alist2strm(self):
        try:
            self.__max_download_sem = asyncio.Semaphore(self._max_download_worker)
            self.__max_list_sem = asyncio.Semaphore(self._max_list_worker)
            self.__iter_tasks_done = asyncio.Event()
            logger.info("Alist2Strm 插件开始执行")
            # 重新初始化清理器以应用最新的后缀配置
            self.init_cleaner()
            await self.cleaner.init_cleaner()
            # 处理所有目录映射
            dir_mappings = self._parse_dir_mappings()
            if not dir_mappings:
                logger.warning("未配置有效的目录映射，跳过执行")
                return
            for mapping in dir_mappings:
                source_dir, target_dir = mapping.split('#', 1)
                source_dir = source_dir.strip()
                target_dir = target_dir.strip()
                logger.info(f"开始处理目录映射: {source_dir} -> {target_dir}")
                await self.__process(source_dir, target_dir)
            logger.info("Alist2Strm 插件执行完成")
        except Exception as e:
            logger.error(
                f"Alist2Strm 插件执行出错：{str(e)} - {traceback.format_exc()}"
            )

    def __filter_func(self, remote_path: AlistFile) -> bool:
        # 检查是否是字幕文件
        if remote_path.suffix.lower() in settings.RMT_SUBEXT:
            return True
            
        # 检查是否是视频/音频/其他文件并启用
        suffix = remote_path.suffix.lower()
        video_suffix = [s.lower() for s in self._video_suffix.split(',') if s.strip()]
        audio_suffix = [s.lower() for s in self._audio_suffix.split(',') if s.strip()]
        other_suffix = [s.lower() for s in self._other_suffix.split(',') if s.strip()]
        
        # 检查文件类型是否启用且后缀匹配
        if (self._video_enabled and suffix in video_suffix) or \
           (self._audio_enabled and suffix in audio_suffix) or \
           (self._other_enabled and suffix in other_suffix):
            pass  # 符合条件，继续处理
        else:
            logger.info(f"文件类型 {remote_path.path} 不在处理列表中")
            return False

        # 这里的source_dir和target_dir会在__process中动态传入，临时使用第一个映射进行计算
        dir_mappings = self._parse_dir_mappings()
        if not dir_mappings:
            return False
            
        source_dir, target_dir = dir_mappings[0].split('#', 1)
        local_path = self.__computed_target_path(remote_path, source_dir, target_dir)
        if self._sync_remote:
            self.processed_remote_paths_in_local.add(local_path)

        if self.cleaner.contains(local_path):
            logger.info(f"文件 {local_path.name} 已存在，跳过处理 {remote_path.path}")
            return False

        return True

    async def __process(self, source_dir: str, target_dir: str) -> None:
        strm_queue = asyncio.Queue()
        subtitle_queue = asyncio.Queue()

        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(
                AlistClient(url=self._url, token=self._token)
            )
            session = await stack.enter_async_context(ClientSession())
            tg = await stack.enter_async_context(asyncio.TaskGroup())

            # 启动生产者线程，传入当前处理的源目录
            tg.create_task(
                self.__produce_paths(
                    client=client, 
                    strm_queue=strm_queue, 
                    subtitle_queue=subtitle_queue,
                    source_dir=source_dir,
                    target_dir=target_dir
                )
            )

            # 启动消费者线程
            tg.create_task(self.__strm_tasks(strm_queue))
            tg.create_task(self.__subtitle_tasks(subtitle_queue, session))

            # 清理任务
            if self._sync_remote:
                await self.__iter_tasks_done.wait()
                await self.cleaner.clean_inviially(self.processed_remote_paths_in_local)
                self.processed_remote_paths_in_local.clear()
                logger.info("清理过期的 .strm 文件完成")

    async def __produce_paths(
        self,
        client: AlistClient,
        strm_queue: asyncio.Queue,
        subtitle_queue: asyncio.Queue,
        source_dir: str,
        target_dir: str
    ) -> None:
        """遍历Alist目录并分发任务到相应队列"""
        async for path in client.iter_path(
            iter_tasks_done=self.__iter_tasks_done,
            max_depth=self._max_depth,
            traversal_mode=self._traversal_mode,
            max_list_workers=self.__max_list_sem,
            iter_dir=source_dir,  # 使用当前处理的源目录
            filter_func=self.__filter_func,
        ):
            target_path = self.__computed_target_path(path, source_dir, target_dir)
            # 根据文件类型分发到不同队列
            if path.suffix in settings.RMT_SUBEXT:
                await subtitle_queue.put((path, target_path))
            else:
                await strm_queue.put((path, target_path))
            # 记录已处理文件
            self.cleaner.add(target_path)
        # 发送结束信号
        await strm_queue.put(None)
        await subtitle_queue.put(None)

    async def __strm_tasks(self, queue: asyncio.Queue) -> None:
        """strm生成队列"""
        while True:
            item = await queue.get()
            if item is None:  # 结束信号
                queue.task_done()
                logger.info("所有strm生成完成")
                break
            path, target_path = item
            try:
                await self.__to_strm(path, target_path)
            except Exception as e:
                logger.error(f"生成.strm失败: {target_path}, 错误: {str(e)}")
            finally:
                queue.task_done()

    async def __subtitle_tasks(
        self, queue: asyncio.Queue, session: ClientSession
    ) -> None:
        """字幕下载队列"""
        while True:
            item = await queue.get()
            if item is None:  # 结束信号
                queue.task_done()
                logger.info("所有字幕下载完成")
                break
            path, target_path = item
            try:
                await self.__download_subtitle(path, target_path, session)
            except Exception as e:
                logger.error(f"下载字幕失败: {target_path}, 错误: {str(e)}")
            finally:
                queue.task_done()

    async def __to_strm(self, path: AlistFile, target_path: Path) -> None:
        """生成strm文件"""
        content = (
            path.download_url
            if not self._url_replace
            else path.download_url.replace(f"{self._url}/d", self._url_replace)
        )
        await aio_os.makedirs(target_path.parent, exist_ok=True)
        async with async_open(target_path, mode="w", encoding="utf-8") as file:
            await file.write(content)
        logger.info(f"已写入.strm: {target_path}")

    async def __download_subtitle(
        self, path: AlistFile, target_path: Path, session: ClientSession
    ) -> None:
        """下载字幕"""
        await aio_os.makedirs(target_path.parent, exist_ok=True)
        async with self.__max_download_sem:
            async with session.get(path.download_url) as resp:
                async with async_open(target_path, mode="wb") as file:
                    await file.write(await resp.read())
        logger.info(f"已下载字幕: {target_path}")

    def __computed_target_path(self, path: AlistFile, source_dir: str, target_dir: str) -> Path:
        """
        计算strm文件保存路径。

        :param path: AlistFile 对象
        :param source_dir: 当前处理的源目录
        :param target_dir: 当前处理的目标目录
        :return: 本地文件路径,如果是媒体文件，则返回 .strm 后缀
        """
        return self.__cached_computed_target_path(path.path, path.suffix, source_dir, target_dir)

    @lru_cache(maxsize=10000)
    def __cached_computed_target_path(self, path: str, suffix: str, source_dir: str, target_dir: str) -> Path:
        # 使用当前映射的源目录和目标目录计算路径
        target_path = Path(target_dir) / path.replace(
            source_dir, self._path_replace, 1
        ).lstrip("/")

        # 检查是否需要生成strm文件（非字幕文件）
        if suffix.lower() not in settings.RMT_SUBEXT:
            target_path = target_path.with_suffix(".strm")

        return target_path

    def __update_config(self) -> None:
        """
        更新插件配置。
        """
        self.update_config(
            {
                "enabled": self._enabled,
                "onlyonce": False,
                "url": self._url,
                "token": self._token,
                "dir_mappings": self._dir_mappings,  # 保存目录映射配置
                "sync_remote": self._sync_remote,
                "cron": self._cron,
                "path_replace": self._path_replace,
                "url_replace": self._url_replace,
                "max_download_worker": self._max_download_worker,
                "max_list_worker": self._max_list_worker,
                "max_depth": self._max_depth,
                "traversal_mode": self._traversal_mode,
                "filter_mode": self._filter_mode,
                # 新增：保存文件类型配置
                "video_enabled": self._video_enabled,
                "audio_enabled": self._audio_enabled,
                "other_enabled": self._other_enabled,
                "video_suffix": self._video_suffix,
                "audio_suffix": self._audio_suffix,
                "other_suffix": self._other_suffix,
            }
        )

    def get_state(self) -> bool:
        # 检查是否配置了有效的目录映射
        return (
            True
            if self._enabled and self._cron and self._token and self._url and self._parse_dir_mappings()
            else False
        )

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        if self.get_state():
            return [
                {
                    "id": "Alist2strm",
                    "name": "全量生成STRM",
                    "trigger": CronTrigger.from_crontab(self._cron),
                    "func": self.run_in_scheduler,
                    "kwargs": {},
                }
            ]
        return []

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:  # type: ignore
        pass

    def get_api(self) -> List[Dict[str, Any]]:  # type: ignore
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return (
            [
                {
                    "component": "VForm",
                    "content": [
                        {
                            "component": "VRow",
                            "content": [
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "enabled",
                                                "label": "启用插件",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "onlyonce",
                                                "label": "立即运行一次",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "sync_remote",
                                                "label": "失效清理",
                                            },
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "component": "VRow",
                            "content": [
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "url",
                                                "label": "alist地址",
                                                "placeholder": "http://localhost:2111",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "token",
                                                "label": "令牌",
                                                "placeholder": "token",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "cron",
                                                "label": "定时",
                                                "placeholder": "0 1 * * 3",
                                            },
                                        }
                                    ],
                                },
                                # 目录映射配置，替换原来的source_dir和target_dir
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12},
                                    "content": [
                                        {
                                            "component": "VTextarea",
                                            "props": {
                                                "model": "dir_mappings",
                                                "label": "目录映射",
                                                "placeholder": "/alist/movies#/local/movies\n/alist/tv#/local/tv",
                                                "rows": 4,
                                                "hint": "每行一个映射，格式：同步源根目录#本地保存根目录，例如：/影视#/data/影视",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "path_replace",
                                                "label": "目的路径替换",
                                                "placeholder": "source_path -> replace_path",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "max_list_worker",
                                                "label": "扫库线程",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "max_download_worker",
                                                "label": "下载线程",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "url_replace",
                                                "label": "url替换",
                                                "placeholder": "url/d -> replace_url",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VSelect",
                                            "props": {
                                                "model": "traversal_mode",
                                                "label": "遍历模式",
                                                "items": [
                                                    {
                                                        "title": "广度优先(BFS)",
                                                        "value": "bfs",
                                                    },
                                                    {
                                                        "title": "深度优先(DFS)",
                                                        "value": "dfs",
                                                    },
                                                ],
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "max_depth",
                                                "label": "最大遍历深度",
                                                "placeholder": "-1表示无限深度",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VSelect",
                                            "props": {
                                                "model": "filter_mode",
                                                "label": "过滤模式",
                                                "items": [
                                                    {
                                                        "title": "集合过滤",
                                                        "value": "set",
                                                    },
                                                    {
                                                        "title": "磁盘过滤",
                                                        "value": "io",
                                                    },
                                                    {
                                                        "title": "布隆过滤",
                                                        "value": "bf",
                                                    },
                                                ],
                                            },
                                        }
                                    ],
                                },
                            ],
                        },
                        # 新增：文件类型配置区域
                        {
                            "component": "VRow",
                            "content": [
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12},
                                    "content": [
                                        {
                                            "component": "VSubheader",
                                            "props": {"title": "文件类型配置"},
                                        }
                                    ]
                                },
                                # 视频文件配置
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "video_enabled",
                                                "label": "启用视频STRM生成",
                                            },
                                        }
                                    ]
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 8},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "video_suffix",
                                                "label": "视频文件后缀",
                                                "placeholder": "例如: .mp4,.mkv,.avi",
                                                "hint": "多个后缀用逗号分隔",
                                            },
                                        }
                                    ]
                                },
                                # 音频文件配置
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "audio_enabled",
                                                "label": "启用音频STRM生成",
                                            },
                                        }
                                    ]
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 8},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "audio_suffix",
                                                "label": "音频文件后缀",
                                                "placeholder": "例如: .mp3,.flac,.wav",
                                                "hint": "多个后缀用逗号分隔",
                                            },
                                        }
                                    ]
                                },
                                # 其他文件配置
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "other_enabled",
                                                "label": "启用其他文件STRM生成",
                                            },
                                        }
                                    ]
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 8},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "other_suffix",
                                                "label": "其他文件后缀",
                                                "placeholder": "例如: .iso,.img,.bin",
                                                "hint": "多个后缀用逗号分隔",
                                            },
                                        }
                                    ]
                                },
                            ],
                        },
                        {
                            "component": "VRow",
                            "content": [
                                {
                                    "component": "VCol",
                                    "props": {
                                        "cols": 12,
                                    },
                                    "content": [
                                        {
                                            "component": "VAlert",
                                            "props": {
                                                "type": "info",
                                                "variant": "tonal",
                                                "text": "定期同步远端文件到本地strm，建议同步间隔大于一周。",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {
                                        "cols": 12,
                                    },
                                    "content": [
                                        {
                                            "component": "VAlert",
                                            "props": {
                                                "type": "info",
                                                "variant": "tonal",
                                                "text": "建议配合响应时间和QPS设置线程",
                                            },
                                        }
                                    ],
                                },
                            ],
                        },
                    ],
                }
            ],
            {
                "enabled": False,
                "onlyonce": False,
                "sync_remote": False,
                "url": "",
                "cron": "",
                "token": "",
                "dir_mappings": "",  # 目录映射默认值
                "path_replace": "",
                "url_replace": "",
                "max_list_worker": None,
                "max_download_worker": None,
                "max_depth": -1,
                "traversal_mode": "bfs",
                "filter_mode": "set",
                # 新增：文件类型配置默认值
                "video_enabled": True,
                "audio_enabled": True,
                "other_enabled": False,
                "video_suffix": ",".join(settings.RMT_MEDIAEXT),
                "audio_suffix": ".mp3,.flac,.wav,.ogg,.aac,.m4a",
                "other_suffix": ".iso,.img,.bin",
            },
        )

    def get_page(self) -> List[dict]:  # type: ignore
        pass

    def stop_service(self) -> None:
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("退出插件失败：%s" % str(e))
