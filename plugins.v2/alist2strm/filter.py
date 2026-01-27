from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator, Set

import aiofiles.os as aio_os
from app.log import logger
from app.plugins.alist2strm.bloom import CoutingBloomFilter


class Cleaner(ABC):
    """
    抽象基类，定义 Cleaner 的通用接口。
    """

    def __init__(self, need_suffix: list, target_dir: Path) -> None:
        """
        初始化 Cleaner。

        :param need_suffix: 需要处理的文件后缀列表
        :param target_dir: 目标目录
        """
        self.target_dir = target_dir
        self.need_suffix = tuple(need_suffix)
        self._last_initialized_at = None  # 上次初始化时间
        self._init_interval = timedelta(days=30)  # 默认初始化间隔为 30 天

    @abstractmethod
    async def init_cleaner(self) -> None:
        """
        初始化过滤器，加载本地文件。
        """
        pass

    def needs_reinitialization(self) -> bool:
        """
        检查是否需要重新初始化。

        :return: 如果需要重新初始化返回 True，否则返回 False
        """
        if self._last_initialized_at is None:
            return True
        return datetime.now() - self._last_initialized_at > self._init_interval

    @abstractmethod
    def add(self, item: Path) -> None:
        """
        添加路径到过滤器中。
        """
        pass

    @abstractmethod
    def remove(self, item: Path) -> None:
        """
        从过滤器中移除路径。
        """
        pass

    @abstractmethod
    def contains(self, item: Path) -> bool:
        """
        检查路径是否存在于过滤器中。

        :return: 如果存在返回 True，否则返回 False
        """
        pass

    @abstractmethod
    async def clean_inviially(self, all_remote_files: Set[Path]) -> None:
        """
        清理无效文件。

        :param all_remote_files: 远程文件集合
        """
        pass

    async def _walk_local_files(self, target_dir: Path) -> AsyncGenerator[Path, None]:
        """
        遍历本地文件路径。

        :param target_dir: 目标目录
        :param need_suffix: 需要处理的文件后缀列表
        :yield: 文件路径
        """
        entries = target_dir
        for entry in await aio_os.scandir(entries):
            if entry.is_dir():
                async for sub_path in self._walk_local_files(Path(entry.path)):
                    yield sub_path
            elif entry.is_file() and entry.name.endswith(self.need_suffix):
                yield Path(entry.path)

    @staticmethod
    async def delete_file(file_path: Path):
        await aio_os.unlink(file_path)
        logger.info(f"删除文件：{file_path}")


class SetCleaner(Cleaner):
    """
    使用集合实现的 Cleaner。
    """

    def __init__(self, need_suffix: list, target_dir: Path) -> None:
        super().__init__(need_suffix, target_dir)
        self._filter: Set[Path] = set()

    async def init_cleaner(self) -> None:
        """
        初始化过滤器，加载本地文件。
        """
        if not self.needs_reinitialization():
            logger.info("SetCleaner 已初始化过，跳过重新初始化")
            return

        self._filter.clear()  # 清空现有数据
        async for path in self._walk_local_files(self.target_dir):
            self._filter.add(path)

        self._last_initialized_at = datetime.now()
        logger.info(f"SetCleaner 已重新初始化，时间戳: {self._last_initialized_at}")

    def add(self, item: Path) -> None:
        self._filter.add(item)

    def remove(self, item: Path) -> None:
        self._filter.remove(item)

    def contains(self, item: Path) -> bool:
        return item in self._filter

    async def clean_inviially(self, all_remote_files: Set[Path]) -> None:
        """
        清理无效文件。
        """
        need_delete_files = self._filter - all_remote_files
        for path in need_delete_files:
            await self.delete_file(path)
            self._filter.remove(path)


class IoCleaner(Cleaner):
    """
    基于文件系统 I/O 实现的 Cleaner。
    """

    def __init__(self, need_suffix: list, target_dir: Path) -> None:
        super().__init__(need_suffix, target_dir)

    async def init_cleaner(self) -> None:
        """
        初始化过滤器，加载本地文件。
        """
        logger.info("IoCleaner 已初始化过，跳过重新初始化")
        return

    def add(self, item: Path) -> None:
        pass

    def remove(self, item: Path) -> None:
        pass

    def contains(self, item: Path) -> bool:
        return item.exists()

    async def clean_inviially(self, all_remote_files: Set[Path]) -> None:
        """
        清理无效文件。
        """
        async for path in self._walk_local_files(self.target_dir):
            if path not in all_remote_files:
                await self.delete_file(path)


class BloomCleaner(Cleaner):
    """
    基于布隆过滤器实现的 Cleaner。
    """

    def __init__(self, need_suffix: list, target_dir: Path) -> None:
        super().__init__(need_suffix, target_dir)
        self._filter = CoutingBloomFilter()

    async def init_cleaner(self) -> None:
        """
        初始化过滤器，加载本地文件。
        """
        if not self.needs_reinitialization():
            logger.info("BloomCleaner 已初始化过，跳过重新初始化")
            return

        self._filter = CoutingBloomFilter()  # 清空现有数据
        async for path in self._walk_local_files(target_dir=self.target_dir):
            self._filter.add(str(path))
        self._last_initialized_at = datetime.now()
        logger.info(f"BloomCleaner 已重新初始化，时间戳: {self._last_initialized_at}")

    def add(self, item: Path) -> None:
        self._filter.add(str(item))

    def remove(self, item: Path) -> None:
        self._filter.remove(item)

    def contains(self, item: Path) -> bool:
        return str(item) in self._filter

    async def clean_inviially(self, all_remote_files: Set[Path]) -> None:
        """
        清理无效文件。
        """
        async for path in self._walk_local_files(self.target_dir):
            if path not in all_remote_files:
                await self.delete_file(path)
                self._filter.remove(path)
