# alist.py
#
# This file is based on AGPL-3.0 licensed code.
# Original author: Akimio521 (https://github.com/Akimio521)
# Modifications by: yubanmeiqin9048 (https://github.com/yubanmeiqin9048)
#
# Licensed under the AGPL-3.0 license.
# See the LICENSE file in the / directory for more details.

import asyncio
from enum import Enum
from json import dumps
from typing import AsyncGenerator, Callable, List

from aiohttp import ClientSession
from app.log import logger


class AlistApi(Enum):
    """
    AlistApi路径
    """

    list = "/api/fs/list"

    def full_url(self, base_url: str) -> str:
        """
        拼接基础URL和路径，并格式化路径参数
        """
        return f"{base_url}{self.value}"


class AlistFile:
    """
    Alist 文件/目录
    """

    def __init__(
        self,
        alist_url: str,
        _path: str,
        is_dir: bool,
        modified: str,
        name: str,
        sign: str,
        size: int,
        thumb: str,
        type: int,
        created: str,
        hash_info: str,
        **_,
    ) -> None:
        self._alist_url = alist_url
        self._path = _path
        self._is_dir = is_dir
        self._modified = modified
        self._name = name
        self._sign = sign
        self._size = size
        self._thumb = thumb
        self._type = type
        self._created = created
        self._hash_info = hash_info

    @property
    def is_dir(self) -> bool:
        """
        是否为路径
        """
        return self._is_dir

    @property
    def path(self) -> str:
        """
        文件路径
        """
        return self._path

    @property
    def suffix(self) -> str:
        """
        文件后缀
        """
        if self.is_dir:
            return ""
        else:
            return "." + self._name.split(".")[-1]

    @property
    def download_url(self) -> str:
        """
        文件下载地址
        """
        if self._sign:
            url = self._alist_url + "/d" + self.path + "?sign=" + self._sign
        else:
            url = self._alist_url + "/d" + self.path

        return url

    @property
    def alist_url(self) -> str:
        """
        alist地址
        """
        return self._alist_url


class AlistClient:
    """
    Alist 客户端 API
    """

    def __init__(self, url: str, token: str) -> None:
        """
        AlistClient 类初始化

        :param url: Alist 服务器地址
        :param token: Alist 访问令牌
        """
        self._HEADERS = {
            "Content-Type": "application/json",
        }
        self._url = url.rstrip("/")
        self._token = token

    async def __aenter__(self):
        headers = self._HEADERS.copy()
        headers.update({"Authorization": self._token})
        self._session = ClientSession(headers=headers)
        return self

    async def __aexit__(self, *_):
        await self._session.close()

    async def __async_fs_list(self, path_in: str) -> List[AlistFile]:
        """
        获取文件列表

        :param path_in: 文件路径
        :return: AlistFile 对象列表
        """

        dir_path = path_in
        logger.debug(f"获取目录{dir_path}下的文件列表")

        api_url = AlistApi.list.full_url(self._url)
        payload = dumps(
            {
                "path": dir_path,
                "password": "",
                "page": 1,
                "per_page": 0,
                "refresh": False,
            }
        )

        try:
            async with self._session.post(api_url, data=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"获取目录{dir_path}的文件列表请求发送失败，状态码：{resp.status}"
                    )

                result = await resp.json()
        except asyncio.TimeoutError:
            raise RuntimeError(f"获取目录{dir_path}的文件列表的请求超时")

        if result["code"] != 200:
            raise RuntimeError(
                f"获取目录{dir_path}的文件列表失败，错误信息：{result['message']}"
            )

        logger.debug(f"获取目录{dir_path}的文件列表成功")

        # 处理 `content` 为空的情况
        if not result["data"]["content"]:
            return []

        try:
            return [
                AlistFile(
                    alist_url=self._url,
                    _path=dir_path + content["name"],
                    **content,
                )
                for content in result["data"]["content"]
            ]
        except Exception as e:
            raise RuntimeError(
                f"返回目录{dir_path}的AlistFile对象列表失败，错误信息：{e}"
            )

    async def iter_path(
        self,
        iter_tasks_done: asyncio.Event,
        max_list_workers: asyncio.Semaphore,
        iter_dir: str,
        max_depth: int = -1,
        traversal_mode: str = "bfs",
        filter_func: Callable[[AlistFile], bool] = lambda x: True,
    ) -> AsyncGenerator[AlistFile, None]:
        """
        异步路径生成器

        :param iter_tasks_done: 事件对象，用于通知遍历已经结束
        :param max_list_workers: 信号量对象，用于控制并发列出目录的协程数量
        :param iter_dir: 要遍历的起始目录路径
        :param max_depth: 最大遍历深度。默认值为 -1
        :param traversal_mode: 遍历模式，支持“bfs”和“dfs”
        :param filter_func: 过滤函数，接收一个 AlistFile 对象并返回布尔值
        :return: AlistFile 对象生成器
        """
        # 初始化队列类型
        queue_class = asyncio.Queue if traversal_mode == "bfs" else asyncio.LifoQueue
        queue = queue_class()
        start_dir = (iter_dir or "").rstrip("/") + "/"
        await queue.put((start_dir, 0))

        async def process_dir(current_dir: str, current_depth: int):
            """处理单个目录，返回文件列表和子目录信息"""
            async with max_list_workers:
                try:
                    entries = await self.__async_fs_list(current_dir)
                    files = []
                    subdirs = []
                    for path in entries:
                        if path.is_dir:
                            next_depth = current_depth + 1
                            if max_depth == -1 or next_depth <= max_depth:
                                subdirs.append(
                                    (path.path.rstrip("/") + "/", next_depth)
                                )
                        elif filter_func(path):
                            files.append(path)
                    return files, subdirs
                except Exception as e:
                    logger.error(f"目录处理失败 {current_dir}: {str(e)}")
                    raise e

        # BFS层级并发逻辑
        async def bfs_traversal():
            current_level = 0
            current_level_dirs = []
            while not queue.empty():
                # 提取当前层级所有目录
                while not queue.empty():
                    dir_path, depth = await queue.get()
                    if depth == current_level:
                        current_level_dirs.append(dir_path)
                    else:
                        await queue.put((dir_path, depth))
                        break

                # 并发处理当前层级
                if current_level_dirs:
                    tasks = [
                        asyncio.create_task(process_dir(dir_path, current_level))
                        for dir_path in current_level_dirs
                    ]

                    for task in asyncio.as_completed(tasks):
                        files, subdirs = await task
                        for file in files:
                            yield file
                        # 子目录入队（下一层级）
                        for subdir_path, next_depth in subdirs:
                            await queue.put((subdir_path, next_depth))

                    current_level_dirs.clear()
                    current_level += 1

        # DFS递归逻辑
        async def dfs_traversal():
            while not queue.empty():
                current_dir, depth = await queue.get()
                files, subdirs = await process_dir(current_dir, depth)
                # 先返回当前目录的文件
                for file in files:
                    yield file
                for subdir_path, next_depth in subdirs:
                    await queue.put((subdir_path, next_depth))
                queue.task_done()

        if traversal_mode == "bfs":
            async for file in bfs_traversal():
                yield file
        else:
            async for file in dfs_traversal():
                yield file

        iter_tasks_done.set()
        logger.info(f"目录遍历完成: {start_dir}")
