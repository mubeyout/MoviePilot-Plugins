import re
from typing import Optional, Tuple
from urllib.parse import unquote, urlparse

from app.log import logger
from app.utils.http import RequestUtils


def _extract_display_name(url: str) -> str:
    """
    从磁力链接或 HTTP URL 中提取显示名称
    - magnet:?...&dn=显示名 → 显示名
    - http://.../文件名.torrent → 文件名
    - 其他 → URL前50字符
    """
    if url.startswith("magnet:"):
        match = re.search(r'\bdn=([^&]+)', url)
        if match:
            try:
                return unquote(match.group(1))
            except Exception:
                return match.group(1)
        # 没有 dn，用 btih 前几位代替
        match = re.search(r'btih:([A-Fa-f0-9]{40})', url)
        if match:
            return match.group(1)[:12]
    elif url.startswith(("http://", "https://")):
        path = urlparse(url).path
        if path:
            name = path.rstrip('/').rsplit('/', 1)[-1]
            if name:
                return unquote(name)
    return url[:50]


class Xunlei:
    """
    迅雷NAS远程下载器
    """

    def __init__(self, name: str, server_url: Optional[str] = None,
                 pan_auth: Optional[str] = None,
                 file_id: Optional[str] = None,
                 **kwargs):
        self._name = name
        self._server_url = (server_url or "").rstrip("/")
        self._pan_auth = pan_auth or ""
        self._file_id = file_id or ""

    @property
    def base_url(self) -> str:
        return f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi"

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "pan-auth": self._pan_auth,
        }

    def test_connection(self) -> Tuple[bool, str]:
        """测试连接"""
        if not self._server_url:
            return False, "未配置服务器地址"
        try:
            token = self.refresh_token()
            if token:
                self._pan_auth = token
            res = RequestUtils(headers=self.headers).get_res(
                url=f"{self.base_url}/device/now"
            )
            if res is not None and res.status_code == 200:
                return True, ""
            return False, f"连接迅雷NAS失败: HTTP {res.status_code if res else 'No response'}"
        except Exception as e:
            return False, f"连接异常: {str(e)}"

    def refresh_token(self) -> Optional[str]:
        """从迅雷NAS页面获取pan_auth token"""
        if not self._server_url:
            return None
        try:
            url = f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi/"
            res = RequestUtils().get_res(url=url)
            if res is not None and res.status_code == 200:
                match = re.search(
                    r'function\s+uiauth\s*\(\s*\w+\s*\)\s*\{\s*return\s*"([^"]+)"',
                    res.text
                )
                if match:
                    logger.info(f"迅雷下载器 {self._name} pan_auth token 刷新成功")
                    return match.group(1)
                else:
                    logger.error(f"迅雷下载器 {self._name} 未找到 uiauth token，请确认迅雷账号已绑定")
            else:
                logger.error(f"迅雷下载器 {self._name} 访问NAS页面失败")
        except Exception as e:
            logger.error(f"迅雷下载器 {self._name} 刷新token失败: {e}")
        return None

    def add_task(self, url: str, download_dir: str = None) -> Tuple[Optional[str], Optional[str]]:
        """
        创建下载任务
        返回: (task_id, error)
        """
        if not self._pan_auth:
            self._pan_auth = self.refresh_token()
        if not self._pan_auth:
            return None, "pan_auth token 获取失败，请确认迅雷NAS地址和账号绑定状态"

        display_name = _extract_display_name(url)
        payload = {
            "kind": "drive#task",
            "type": "user#download",
            "name": display_name,
            "file_size": "0",
            "params": {
                "url": url,
            }
        }

        try:
            try:
                res = RequestUtils(headers=self.headers).post_res(
                    url=f"{self.base_url}/drive/v1/task",
                    json=payload
                )
                if res is None:
                    # RequestUtils returns None on non-2xx, fallback to raw request
                    import requests as _req
                    res = _req.post(
                        f"{self.base_url}/drive/v1/task",
                        json=payload,
                        headers=self.headers,
                        timeout=30
                    )
            except Exception as e:
                logger.error(f"迅雷下载器 {self._name} HTTP请求异常: {e}")
                return None, str(e)

            if res is not None:
                try:
                    data = res.json()
                except Exception:
                    return None, f"HTTP {res.status_code}: {res.text[:200]}"
                if "error" in data:
                    error_code = data.get("error", "")
                    error_desc = data.get("error_description", "")
                    # task_create_count_limit: 先清理 PENDING 任务再重试
                    if error_code == "task_create_count_limit":
                        logger.warning(f"迅雷下载器 {self._name} 任务创建次数达到上限，尝试清理 PENDING 任务")
                        self._cleanup_pending_tasks()
                        import requests as _req
                        res = _req.post(
                            f"{self.base_url}/drive/v1/task",
                            json=payload,
                            headers=self.headers,
                            timeout=30
                        )
                        if res is not None:
                            retry_data = res.json()
                            if "error" not in retry_data:
                                task = retry_data.get("task", {})
                                task_id = task.get("id", "")
                                task_name = task.get("name", display_name)
                                logger.info(f"迅雷下载器 {self._name} 重试创建任务成功: {task_id} - {task_name}")
                                return task_id, None
                            else:
                                return None, f"迅雷错误: {retry_data.get('error')} - {retry_data.get('error_description', '')}"
                    return None, f"迅雷错误: {error_code} - {error_desc}"
                task = data.get("task", {})
                task_id = task.get("id", "")
                task_name = task.get("name", display_name)
                logger.info(f"迅雷下载器 {self._name} 创建任务: {task_id} - {task_name}")
                return task_id, None
            else:
                return None, "迅雷NAS无响应"
        except Exception as e:
            logger.error(f"迅雷下载器 {self._name} 创建任务失败: {e}")
            return None, str(e)

    def _cleanup_pending_tasks(self) -> int:
        """
        清理 PENDING 状态的下载任务（通常是种子无做种者卡住的）
        返回清理的任务数
        """
        if not self._pan_auth:
            return 0
        try:
            from urllib.parse import quote
            task_type = quote("user#download")
            url = f"{self.base_url}/drive/v1/tasks?type={task_type}&pan_auth={self._pan_auth}&device_space="
            res = RequestUtils(headers=self.headers).get_res(url=url)
            if res is not None and res.status_code == 200:
                data = res.json()
                tasks = data.get("tasks", [])
                cleaned = 0
                for t in tasks:
                    if t.get("phase") == "PHASE_TYPE_PENDING":
                        tid = t.get("id", "")
                        del_url = f"{self.base_url}/drive/v1/task/{tid}"
                        RequestUtils(headers=self.headers).delete_res(url=del_url)
                        cleaned += 1
                if cleaned > 0:
                    logger.info(f"迅雷下载器 {self._name} 清理了 {cleaned} 个 PENDING 任务")
                return cleaned
        except Exception as e:
            logger.error(f"迅雷下载器 {self._name} 清理 PENDING 任务失败: {e}")
        return 0

    def get_tasks(self) -> Tuple[Optional[list], Optional[str]]:
        """获取任务列表"""
        if not self._pan_auth:
            return None, "No token"
        from urllib.parse import quote
        task_type = quote("user#runner")
        url = f"{self.base_url}/drive/v1/tasks?type={task_type}&pan_auth={self._pan_auth}&device_space="
        try:
            res = RequestUtils(headers=self.headers).get_res(url=url)
            if res is not None and res.status_code == 200:
                data = res.json()
                return data.get("tasks", []), None
            return None, f"HTTP {res.status_code if res else 'No response'}"
        except Exception as e:
            return None, str(e)
