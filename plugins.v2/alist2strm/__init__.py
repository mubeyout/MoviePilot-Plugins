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

from .alist import AlistClient, AlistFile
from .filter import BloomCleaner, IoCleaner, SetCleaner


class Alist2StrmPro(_PluginBase):
    # 插件名称
    plugin_name = "Alist2StrmPro"
    # 插件描述
    plugin_desc = "从alist生成音视频strm。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/mubeyout/MoviePilot-Plugins/main/icons/Alist.png"
    # 插件版本
    plugin_version = "3.0.0"
    # 插件作者
    plugin_author = "MUBEY"
    # 作者主页
    author_url = "https://github.com/mubeyout"
    # 插件配置项ID前缀
    plugin_config_prefix = "alist2strm_"
    # 加载顺序
    plugin_order = 32
    # 可使用的用户级别
    auth_level = 1

    # 默认后缀常量
    DEFAULT_VIDEO_SUFFIX = ".mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.ts,.rmvb,.iso"
    DEFAULT_AUDIO_SUFFIX = ".mp3,.flac,.wav,.aac,.ogg,.m4a,.wma,.ape,.opus,.alac,.dsd,.dsf"
    DEFAULT_OTHER_SUFFIX = ".nfo,.jpg,.png,.jpeg,.gif,.bmp,.srt,.ass,.ssa,.sub,.idx,.txt"

    # 私有属性
    _enabled = False
    _url = ""
    _token = ""
    _source_dir = ""
    _sync_remote = False
    _path_replace = ""
    _url_replace = ""
    _cron = ""
    _scheduler = None
    _onlyonce = False
    _max_download_worker = 3
    _max_list_worker = 7
    _max_depth = -1
    _traversal_mode = "bfs"
    _filter_mode = "set"
    # 按类别分组的已处理远程路径集合
    processed_remote_paths_by_category: Dict[str, Set[Path]] = {}
    # 各类别独立的 cleaner 实例
    _cleaners: Dict[str, any] = {}

    # 视频类配置
    _video_enabled = True
    _video_target_dir = ""
    _video_suffix = ""
    _video_suffix_set: Set[str] = set()

    # 音频类配置
    _audio_enabled = False
    _audio_target_dir = ""
    _audio_suffix = ""
    _audio_suffix_set: Set[str] = set()

    # 其他类配置
    _other_enabled = False
    _other_target_dir = ""
    _other_suffix = ""
    _other_suffix_set: Set[str] = set()

    def init_plugin(self, config: Optional[dict] = None) -> None:
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._url = config.get("url", "")
            self._token = config.get("token", "")
            self._source_dir = config.get("source_dir", "")
            self._sync_remote = config.get("sync_remote")
            self._cron = config.get("cron")
            self._path_replace = config.get("path_replace", "")
            self._url_replace = config.get("url_replace")
            self._max_download_worker = int(config.get("max_download_worker", 3))
            self._max_list_worker = int(config.get("max_list_worker", 7))
            self._max_depth = config.get("max_depth") or -1
            self._traversal_mode = config.get("traversal_mode") or "bfs"
            self._filter_mode = config.get("filter_mode") or "set"

            # 视频配置
            self._video_enabled = config.get("video_enabled", True)
            self._video_target_dir = config.get("video_target_dir", "")
            self._video_suffix = config.get("video_suffix", self.DEFAULT_VIDEO_SUFFIX)

            # 音频配置
            self._audio_enabled = config.get("audio_enabled", False)
            self._audio_target_dir = config.get("audio_target_dir", "")
            self._audio_suffix = config.get("audio_suffix", self.DEFAULT_AUDIO_SUFFIX)

            # 其他配置
            self._other_enabled = config.get("other_enabled", False)
            self._other_target_dir = config.get("other_target_dir", "")
            self._other_suffix = config.get("other_suffix", self.DEFAULT_OTHER_SUFFIX)

            # 构建后缀集合（用于快速查找）
            self._video_suffix_set = set(
                s.strip().lower() for s in self._video_suffix.split(",") if s.strip()
            )
            self._audio_suffix_set = set(
                s.strip().lower() for s in self._audio_suffix.split(",") if s.strip()
            )
            self._other_suffix_set = set(
                s.strip().lower() for s in self._other_suffix.split(",") if s.strip()
            )

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
        支持多个目标目录的独立清理。
        """
        if self._filter_mode == "set":
            use_cleaner = SetCleaner
        elif self._filter_mode == "io":
            use_cleaner = IoCleaner
        elif self._filter_mode == "bf":
            use_cleaner = BloomCleaner
        else:
            raise ValueError(f"未知的过滤模式: {self._filter_mode}")

        # 构建所有需要处理的后缀列表（用于过滤）
        all_suffixes = list(self._video_suffix_set | self._audio_suffix_set | self._other_suffix_set)
        all_suffixes.append("strm")

        # 收集所有启用的目标目录
        target_dirs = []
        if self._video_enabled and self._video_target_dir:
            target_dirs.append(("video", Path(self._video_target_dir)))
        if self._audio_enabled and self._audio_target_dir:
            target_dirs.append(("audio", Path(self._audio_target_dir)))
        if self._other_enabled and self._other_target_dir:
            target_dirs.append(("other", Path(self._other_target_dir)))

        # 为每个类别创建独立的 cleaner
        self._cleaners = {}
        for category, target_dir in target_dirs:
            # 根据类别选择对应的后缀
            if category == "video":
                category_suffixes = list(self._video_suffix_set)
            elif category == "audio":
                category_suffixes = list(self._audio_suffix_set)
            else:  # other
                category_suffixes = list(self._other_suffix_set)
            category_suffixes.append("strm")

            self._cleaners[category] = use_cleaner(
                need_suffix=category_suffixes,
                target_dir=target_dir,
            )
            logger.info(f"已创建 {category} 类别的 Cleaner，目录：{target_dir}")

        # 保存所有目标目录供清理时使用
        self._all_target_dirs = target_dirs

        # 主 cleaner（用于兼容旧逻辑，使用视频目录）
        primary_target_dir = Path(self._video_target_dir or self._audio_target_dir or self._other_target_dir or "/tmp")
        self.cleaner = use_cleaner(
            need_suffix=all_suffixes,
            target_dir=primary_target_dir,
        )

    def _get_file_category(self, suffix: str) -> Optional[str]:
        """
        根据文件后缀判断文件类别
        :return: 'video' | 'audio' | 'other' | None
        """
        suffix_lower = suffix.lower()
        if suffix_lower in self._video_suffix_set:
            return "video" if self._video_enabled else None
        elif suffix_lower in self._audio_suffix_set:
            return "audio" if self._audio_enabled else None
        elif suffix_lower in self._other_suffix_set:
            return "other" if self._other_enabled else None
        return None

    def _get_target_dir_by_category(self, category: str) -> str:
        """根据类别返回对应的保存目录"""
        return {
            "video": self._video_target_dir,
            "audio": self._audio_target_dir,
            "other": self._other_target_dir,
        }.get(category, self._video_target_dir)

    def run_in_scheduler(self) -> None:
        asyncio.run(self.alist2strm())

    async def alist2strm(self):
        try:
            self.__max_download_sem = asyncio.Semaphore(self._max_download_worker)
            self.__max_list_sem = asyncio.Semaphore(self._max_list_worker)
            self.__iter_tasks_done = asyncio.Event()

            # 初始化按类别分组的已处理路径集合
            self.processed_remote_paths_by_category = {
                "video": set(),
                "audio": set(),
                "other": set()
            }

            logger.info("Alist2Strm 插件开始执行")
            await self.cleaner.init_cleaner()

            # 初始化各类别的 cleaner
            for category, cleaner in self._cleaners.items():
                await cleaner.init_cleaner()

            await self.__process()
            logger.info("Alist2Strm 插件执行完成")
        except Exception as e:
            logger.error(
                f"Alist2Strm 插件执行出错：{str(e)} - {traceback.format_exc()}"
            )

    def __filter_func(self, remote_path: AlistFile) -> bool:
        category = self._get_file_category(remote_path.suffix)
        if category is None:
            logger.debug(f"文件 {remote_path.path} 不在处理列表中或类别未启用")
            return False

        # 根据类别获取对应保存目录和 cleaner
        target_dir = self._get_target_dir_by_category(category)
        local_path = self.__computed_target_path(remote_path, target_dir)

        # 记录到对应类别的已处理路径集合
        if self._sync_remote and category in self.processed_remote_paths_by_category:
            self.processed_remote_paths_by_category[category].add(local_path)

        # 使用对应类别的 cleaner 进行检查
        category_cleaner = self._cleaners.get(category, self.cleaner)
        if category_cleaner.contains(local_path):
            logger.debug(f"文件 {local_path.name} 已存在，跳过处理 {remote_path.path}")
            return False

        return True

    async def __process(self) -> None:
        strm_queue = asyncio.Queue()
        subtitle_queue = asyncio.Queue()
        other_queue = asyncio.Queue()

        # 收集所有已处理的远程路径（按类别分组）
        self.processed_remote_paths_by_category = {
            "video": set(),
            "audio": set(),
            "other": set()
        }

        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(
                AlistClient(url=self._url, token=self._token)
            )
            session = await stack.enter_async_context(ClientSession())
            tg = await stack.enter_async_context(asyncio.TaskGroup())

            # 启动生产者线程
            tg.create_task(
                self.__produce_paths(
                    client=client,
                    strm_queue=strm_queue,
                    subtitle_queue=subtitle_queue,
                    other_queue=other_queue,
                )
            )

            # 启动消费者线程
            tg.create_task(self.__strm_tasks(strm_queue))
            tg.create_task(self.__subtitle_tasks(subtitle_queue, session))
            tg.create_task(self.__other_tasks(other_queue, session))

            # 清理任务
            if self._sync_remote:
                await self.__iter_tasks_done.wait()
                await self.__clean_all_categories()
                logger.info("清理所有类别的过期文件完成")

    async def __produce_paths(
        self,
        client: AlistClient,
        strm_queue: asyncio.Queue,
        subtitle_queue: asyncio.Queue,
        other_queue: asyncio.Queue,
    ) -> None:
        """遍历Alist目录并分发任务到相应队列"""
        async for path in client.iter_path(
            iter_tasks_done=self.__iter_tasks_done,
            max_depth=self._max_depth,
            traversal_mode=self._traversal_mode,
            max_list_workers=self.__max_list_sem,
            iter_dir=self._source_dir,
            filter_func=self.__filter_func,
        ):
            category = self._get_file_category(path.suffix)
            target_dir = self._get_target_dir_by_category(category)
            target_path = self.__computed_target_path(path, target_dir)

            if category == "video":
                # 视频：生成 .strm 文件
                await strm_queue.put((path, target_path))
            elif category == "audio":
                # 音频：生成 .strm 文件（与视频相同处理）
                await strm_queue.put((path, target_path))
            elif category == "other":
                # 其他：字幕下载或直接复制
                suffix_lower = path.suffix.lower()
                if suffix_lower in [".srt", ".ass", ".ssa", ".sub", ".idx"]:
                    await subtitle_queue.put((path, target_path))
                else:
                    await other_queue.put((path, target_path))

            # 记录已处理文件到对应类别的 cleaner
            category_cleaner = self._cleaners.get(category, self.cleaner)
            if category_cleaner:
                category_cleaner.add(target_path)

        # 发送结束信号
        await strm_queue.put(None)
        await subtitle_queue.put(None)
        await other_queue.put(None)

    async def __clean_all_categories(self) -> None:
        """
        清理所有类别的失效文件
        """
        for category, remote_paths in self.processed_remote_paths_by_category.items():
            if category in self._cleaners:
                cleaner = self._cleaners[category]
                try:
                    await cleaner.clean_inviially(remote_paths)
                    logger.info(f"类别 {category} 的过期文件清理完成")
                except Exception as e:
                    logger.error(f"清理类别 {category} 的过期文件失败：{str(e)}")
            # 清空该类别的已处理路径
            remote_paths.clear()

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

    async def __other_tasks(
        self, queue: asyncio.Queue, session: ClientSession
    ) -> None:
        """其他文件下载队列（图片、nfo等）"""
        while True:
            item = await queue.get()
            if item is None:  # 结束信号
                queue.task_done()
                logger.info("所有其他文件下载完成")
                break
            path, target_path = item
            try:
                await self.__download_file(path, target_path, session)
            except Exception as e:
                logger.error(f"下载文件失败: {target_path}, 错误: {str(e)}")
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

    async def __download_file(
        self, path: AlistFile, target_path: Path, session: ClientSession
    ) -> None:
        """下载其他文件（图片、nfo等）"""
        await aio_os.makedirs(target_path.parent, exist_ok=True)
        async with self.__max_download_sem:
            async with session.get(path.download_url) as resp:
                async with async_open(target_path, mode="wb") as file:
                    await file.write(await resp.read())
        logger.info(f"已下载文件: {target_path}")

    def __computed_target_path(self, path: AlistFile, target_dir: str = None) -> Path:
        """
        计算文件保存路径，支持按类别使用不同目录。

        :param path: AlistFile 对象
        :param target_dir: 目标目录，如果为None则根据文件类别自动获取
        :return: 本地文件路径,如果是视频/音频文件，则返回 .strm 后缀
        """
        if target_dir is None:
            category = self._get_file_category(path.suffix)
            target_dir = self._get_target_dir_by_category(category) if category else self._video_target_dir

        return self.__cached_computed_target_path(path.path, path.suffix, target_dir)

    @lru_cache(maxsize=10000)
    def __cached_computed_target_path(self, path: str, suffix: str, target_dir: str) -> Path:
        target_path = Path(target_dir) / path.replace(
            self._source_dir, self._path_replace, 1
        ).lstrip("/")

        # 视频和音频文件改为 .strm 后缀
        suffix_lower = suffix.lower()
        if suffix_lower in self._video_suffix_set or suffix_lower in self._audio_suffix_set:
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
                "source_dir": self._source_dir,
                "sync_remote": self._sync_remote,
                "cron": self._cron,
                "path_replace": self._path_replace,
                "url_replace": self._url_replace,
                "max_download_worker": self._max_download_worker,
                "max_list_worker": self._max_list_worker,
                "max_depth": self._max_depth,
                "traversal_mode": self._traversal_mode,
                "filter_mode": self._filter_mode,
                # 视频配置
                "video_enabled": self._video_enabled,
                "video_target_dir": self._video_target_dir,
                "video_suffix": self._video_suffix,
                # 音频配置
                "audio_enabled": self._audio_enabled,
                "audio_target_dir": self._audio_target_dir,
                "audio_suffix": self._audio_suffix,
                # 其他配置
                "other_enabled": self._other_enabled,
                "other_target_dir": self._other_target_dir,
                "other_suffix": self._other_suffix,
            }
        )

    def get_state(self) -> bool:
        return (
            True
            if self._enabled and self._cron and self._token and self._url
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
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 4},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "source_dir",
                                                "label": "同步源根目录",
                                                "placeholder": "/source_path",
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
                        {
                            "component": "VDivider",
                            "props": {
                                "class": "my-4",
                            },
                        },
                        {
                            "component": "VRow",
                            "content": [
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12},
                                    "content": [
                                        {
                                            "component": "h3",
                                            "props": {
                                                "class": "text-h6 mb-2",
                                            },
                                            "text": "🎬 视频文件配置",
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
                                    "props": {"cols": 12, "md": 3},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "video_enabled",
                                                "label": "启用视频处理",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 5},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "video_target_dir",
                                                "label": "视频保存目录",
                                                "placeholder": "/path/to/videos",
                                                "hint": "视频类文件的本地保存路径",
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
                                                "model": "video_suffix",
                                                "label": "视频后缀",
                                                "placeholder": ".mp4,.mkv,.avi",
                                                "hint": "逗号分隔，默认：.mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.ts,.rmvb,.iso",
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
                                    "props": {"cols": 12},
                                    "content": [
                                        {
                                            "component": "h3",
                                            "props": {
                                                "class": "text-h6 mb-2 mt-2",
                                            },
                                            "text": "🎵 音频文件配置",
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
                                    "props": {"cols": 12, "md": 3},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "audio_enabled",
                                                "label": "启用音频处理",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 5},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "audio_target_dir",
                                                "label": "音频保存目录",
                                                "placeholder": "/path/to/audios",
                                                "hint": "音频类文件的本地保存路径",
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
                                                "model": "audio_suffix",
                                                "label": "音频后缀",
                                                "placeholder": ".mp3,.flac,.wav",
                                                "hint": "逗号分隔，默认：.mp3,.flac,.wav,.aac,.ogg,.m4a,.wma,.ape,.opus,.alac,.dsd,.dsf",
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
                                    "props": {"cols": 12},
                                    "content": [
                                        {
                                            "component": "h3",
                                            "props": {
                                                "class": "text-h6 mb-2 mt-2",
                                            },
                                            "text": "📄 其他文件配置",
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
                                    "props": {"cols": 12, "md": 3},
                                    "content": [
                                        {
                                            "component": "VSwitch",
                                            "props": {
                                                "model": "other_enabled",
                                                "label": "启用其他处理",
                                            },
                                        }
                                    ],
                                },
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12, "md": 5},
                                    "content": [
                                        {
                                            "component": "VTextField",
                                            "props": {
                                                "model": "other_target_dir",
                                                "label": "其他保存目录",
                                                "placeholder": "/path/to/others",
                                                "hint": "其他类文件的本地保存路径（字幕、图片、NFO等）",
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
                                                "model": "other_suffix",
                                                "label": "其他后缀",
                                                "placeholder": ".srt,.ass,.nfo,.jpg",
                                                "hint": "逗号分隔，默认：.nfo,.jpg,.png,.jpeg,.gif,.bmp,.srt,.ass,.ssa,.sub,.idx,.txt",
                                            },
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "component": "VDivider",
                            "props": {
                                "class": "my-4",
                            },
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
                        {
                            "component": "VRow",
                            "content": [
                                {
                                    "component": "VCol",
                                    "props": {"cols": 12},
                                    "content": [
                                        {
                                            "component": "VAlert",
                                            "props": {
                                                "type": "warning",
                                                "variant": "tonal",
                                                "text": "💡 提示：视频和音频文件会生成 .strm 文件；字幕文件会下载到本地；其他文件（图片、NFO等）会下载到本地。三类文件可独立启用/禁用，保存目录也可分别设置。",
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
                "source_dir": "",
                "path_replace": "",
                "url_replace": "",
                "max_list_worker": None,
                "max_download_worker": None,
                "max_depth": -1,
                "traversal_mode": "bfs",
                "filter_mode": "set",
                # 视频配置
                "video_enabled": True,
                "video_target_dir": "",
                "video_suffix": ".mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.ts,.rmvb,.iso",
                # 音频配置
                "audio_enabled": False,
                "audio_target_dir": "",
                "audio_suffix": ".mp3,.flac,.wav,.aac,.ogg,.m4a,.wma,.ape,.opus,.alac,.dsd,.dsf",
                # 其他配置
                "other_enabled": False,
                "other_target_dir": "",
                "other_suffix": ".nfo,.jpg,.png,.jpeg,.gif,.bmp,.srt,.ass,.ssa,.sub,.idx,.txt",
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
