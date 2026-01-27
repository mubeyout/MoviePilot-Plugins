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
    plugin_name = "Alist2Strm"
    # 插件描述
    plugin_desc = "从alist生成strm。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/yubanmeiqin9048/MoviePilot-Plugins/main/icons/Alist.png"
    # 插件版本
    plugin_version = "1.8.3"
    # 插件作者
    plugin_author = "yubanmeiqin9048"
    # 作者主页
    author_url = "https://github.com/yubanmeiqin9048"
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
    _source_dir = ""
    _target_dir = ""
    _sync_remote = False
    _path_replace = ""
    _url_replace = ""
    _cron = ""
    _scheduler = None
    _onlyonce = False
    _process_file_suffix = settings.RMT_SUBEXT + settings.RMT_MEDIAEXT
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
            self._source_dir = config.get("source_dir", "")
            self._sync_remote = config.get("sync_remote")
            self._target_dir = config.get("target_dir", "")
            self._cron = config.get("cron")
            self._path_replace = config.get("path_replace", "")
            self._url_replace = config.get("url_replace")
            self._max_download_worker = int(config.get("max_download_worker", 3))
            self._max_list_worker = int(config.get("max_list_worker", 7))
            self._max_depth = config.get("max_depth") or -1
            self._traversal_mode = config.get("traversal_mode") or "bfs"
            self._filter_mode = config.get("filter_mode") or "set"
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
        self.cleaner = use_cleaner(
            need_suffix=self._process_file_suffix + ["strm"],
            target_dir=Path(self._target_dir),
        )

    def run_in_scheduler(self) -> None:
        asyncio.run(self.alist2strm())

    async def alist2strm(self):
        try:
            self.__max_download_sem = asyncio.Semaphore(self._max_download_worker)
            self.__max_list_sem = asyncio.Semaphore(self._max_list_worker)
            self.__iter_tasks_done = asyncio.Event()
            logger.info("Alist2Strm 插件开始执行")
            await self.cleaner.init_cleaner()
            await self.__process()
            logger.info("Alist2Strm 插件执行完成")
        except Exception as e:
            logger.error(
                f"Alist2Strm 插件执行出错：{str(e)} - {traceback.format_exc()}"
            )

    def __filter_func(self, remote_path: AlistFile) -> bool:
        if remote_path.suffix.lower() not in self._process_file_suffix:
            logger.info(f"文件类型 {remote_path.path} 不在处理列表中")
            return False

        local_path = self.__computed_target_path(remote_path)
        if self._sync_remote:
            self.processed_remote_paths_in_local.add(local_path)

        if self.cleaner.contains(local_path):
            logger.info(f"文件 {local_path.name} 已存在，跳过处理 {remote_path.path}")
            return False

        return True

    async def __process(self) -> None:
        strm_queue = asyncio.Queue()
        subtitle_queue = asyncio.Queue()

        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(
                AlistClient(url=self._url, token=self._token)
            )
            session = await stack.enter_async_context(ClientSession())
            tg = await stack.enter_async_context(asyncio.TaskGroup())

            # 启动生产者线程
            tg.create_task(
                self.__produce_paths(
                    client=client, strm_queue=strm_queue, subtitle_queue=subtitle_queue
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
            target_path = self.__computed_target_path(path)
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

    def __computed_target_path(self, path: AlistFile) -> Path:
        """
        计算strm文件保存路径。

        :param path: AlistFile 对象
        :return: 本地文件路径,如果是媒体文件，则返回 .strm 后缀
        """
        return self.__cached_computed_target_path(path.path, path.suffix)

    @lru_cache(maxsize=10000)
    def __cached_computed_target_path(self, path: str, suffix: str) -> Path:
        target_path = Path(self._target_dir) / path.replace(
            self._source_dir, self._path_replace, 1
        ).lstrip("/")

        if suffix.lower() in settings.RMT_MEDIAEXT:
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
                "target_dir": self._target_dir,
                "cron": self._cron,
                "path_replace": self._path_replace,
                "url_replace": self._url_replace,
                "max_download_worker": self._max_download_worker,
                "max_list_worker": self._max_list_worker,
                "max_depth": self._max_depth,
                "traversal_mode": self._traversal_mode,
                "filter_mode": self._filter_mode,
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
                                                "model": "target_dir",
                                                "label": "本地保存根目录",
                                                "placeholder": "/target_path",
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
                "source_dir": "",
                "target_dir": "",
                "path_replace": "",
                "url_replace": "",
                "max_list_worker": None,
                "max_download_worker": None,
                "max_depth": -1,
                "traversal_mode": "bfs",
                "filter_mode": "set",
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
