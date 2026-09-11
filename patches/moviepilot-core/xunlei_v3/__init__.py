# ============ V3 迅雷下载器模块（按 V3 Module/capability 合同迁移）============
# 迁移自 V2 补丁 xunlei/。日志/HTTP import 已对齐 V3 路径。
# DownloaderType.Xunlei 由 types.py 补丁注入（见 patches Dockerfile），本模块直接引用。

from pathlib import Path
from typing import Optional, Set, Tuple, Union

from app.modules import _ModuleBase, _DownloaderBase
from app.runtime.log import logger
from app.schemas.types import DownloaderType, ModuleType
from app.modules.xunlei.xunlei import Xunlei


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

    def stop(self) -> None:
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
        :return: 下载器名称、任务ID(替代hash)、布局、错误原因
        """
        if not content:
            return None, None, None, "下载内容为空"

        server: Xunlei = self.get_instance(downloader)
        if not server:
            return None

        download_url = None
        if isinstance(content, (str, bytes)):
            text = content if isinstance(content, str) else content.decode('utf-8', errors='ignore')
            if text.startswith(("magnet:", "http://", "https://")):
                download_url = text  # .torrent URL 由 xunlei.py add_task 自动转磁力

        if not download_url:
            return None, None, None, "迅雷下载器不支持该内容类型"

        task_id, error = server.add_task(url=download_url, download_dir=str(download_dir) if download_dir else None)
        if error:
            return None, None, None, f"添加迅雷下载任务失败: {error}"

        return downloader or server._name, task_id, "Original", ""

    def list_torrents(self, status=None, hashs: Union[list, str] = None,
                      downloader: Optional[str] = None, include_all_tags: bool = False):
        """
        列出迅雷任务（V3 契约签名；hashs 过滤在返回后按需匹配）
        """
        server: Xunlei = self.get_instance(downloader)
        if not server:
            return None
        items, error = server.get_tasks()
        if error:
            return None
        from app.schemas.transfer import DownloaderTorrent
        rets = []
        want = set(hashs) if isinstance(hashs, list) else ({hashs} if isinstance(hashs, str) and hashs else None)
        for task in items or []:
            task_hash = str(task.get("id") or task.get("task_id") or "")
            if want and task_hash not in want:
                continue
            name = str(task.get("name") or "")
            progress = task.get("progress") or 0
            state = str(task.get("status") or task.get("phase") or "")
            rets.append(DownloaderTorrent(
                hash=task_hash,
                name=name,
                progress=float(progress),
                state=state,
            ))
        return rets
