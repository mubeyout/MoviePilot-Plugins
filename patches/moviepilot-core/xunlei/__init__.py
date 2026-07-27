from pathlib import Path
from typing import Set, Tuple, Optional, Union

from app.log import logger
from app.modules import _ModuleBase, _DownloaderBase
from app.modules.xunlei.xunlei import Xunlei
from app.schemas.types import (
    DownloaderType,
    ModuleType,
)


class XunleiModule(_ModuleBase, _DownloaderBase[Xunlei]):

    def init_module(self) -> None:
        super().init_service(service_name=Xunlei.__name__.lower(),
                             service_type=Xunlei)

    @staticmethod
    def get_name() -> str:
        return "Xunlei"

    @staticmethod
    def get_type() -> ModuleType:
        return ModuleType.Downloader

    @staticmethod
    def get_subtype() -> DownloaderType:
        return DownloaderType.Xunlei

    @staticmethod
    def get_priority() -> int:
        return 10

    def stop(self):
        pass

    def test(self) -> Optional[Tuple[bool, str]]:
        if not self.get_instances():
            return None
        for name, server in self.get_instances().items():
            ok, msg = server.test_connection()
            if not ok:
                return False, msg
        return True, ""

    def init_setting(self) -> Tuple[str, Union[str, bool]]:
        pass

    def download(self, content: Union[Path, str, bytes], download_dir: Path, cookie: str,
                 episodes: Set[int] = None, category: Optional[str] = None, label: Optional[str] = None,
                 downloader: Optional[str] = None) -> Optional[Tuple[Optional[str], Optional[str], Optional[str], str]]:
        """
        添加下载任务到迅雷下载器
        :param content: 种子文件路径或磁力链接
        :param download_dir: 下载目录
        :param cookie: cookie
        :param episodes: 需要下载的集数
        :param category: 分类
        :param label: 标签
        :param downloader: 下载器名称
        :return: 下载器名称、种子Hash、种子文件布局、错误原因
        """
        if not content:
            return None, None, None, "下载内容为空"

        # 获取下载器实例
        server: Xunlei = self.get_instance(downloader)
        if not server:
            return None

        # 解析下载URL
        download_url = None
        if isinstance(content, (str, bytes)):
            text = content if isinstance(content, str) else content.decode('utf-8', errors='ignore')
            if text.startswith("magnet:") or text.startswith("http://") or text.startswith("https://"):
                download_url = text

        if not download_url:
            return None, None, None, "迅雷下载器不支持该内容类型（仅支持磁力链接和HTTP/HTTPS URL）"

        # 发送到迅雷
        task_id, error = server.add_task(url=download_url, download_dir=str(download_dir) if download_dir else None)
        if error:
            return None, None, None, f"添加迅雷下载任务失败: {error}"

        # 返回: (下载器名称, 种子Hash, 布局, 错误)
        # 迅雷没有传统种子hash概念，用task_id代替
        return downloader or server._name, task_id, "Original", ""
