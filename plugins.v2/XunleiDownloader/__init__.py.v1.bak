import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.log import logger
from app.plugins import _PluginBase
from app.utils.http import RequestUtils


def _extract_display_name(url: str) -> str:
    """
    从磁力链接或 HTTP URL 中提取显示名称
    """
    if url.startswith("magnet:"):
        match = re.search(r'\bdn=([^&]+)', url)
        if match:
            try:
                return unquote(match.group(1))
            except Exception:
                return match.group(1)
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


class XunleiDownloader(_PluginBase):
    """
    迅雷远程下载器插件
    将磁力链接/种子 URL 发送到迅雷 NAS 进行下载
    """

    plugin_name = "XunleiDownloader"
    plugin_desc = "将磁力链接/种子发送到迅雷NAS远程下载器"
    plugin_icon = "xunlei.png"
    plugin_version = "1.0"
    plugin_author = "KAI"
    author_url = "https://github.com/mubeyout"
    plugin_config_prefix = "xunlei_"
    plugin_order = 30
    auth_level = 1

    def init_plugin(self, config: dict = None):
        """
        初始化插件
        """
        if config:
            self._enabled = config.get("enabled")
            self._server_url = (config.get("server_url", "") or "").rstrip("/")
            self._file_id = config.get("file_id", "") or ""
            self._pan_auth = config.get("pan_auth", "") or ""
        else:
            self._enabled = False
            self._server_url = ""
            self._file_id = ""
            self._pan_auth = ""

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return [
            {
                "cmd": "/xunlei_download",
                "action": "xunlei_download",
                "desc": "通过迅雷下载磁力链接或种子",
                "usage": "/xunlei_download <magnet_url_or_torrent_url>",
                "min_level": 1,
            },
            {
                "cmd": "/xunlei_refresh_token",
                "action": "xunlei_refresh_token",
                "desc": "刷新迅雷 pan_auth token",
                "usage": "/xunlei_refresh_token",
                "min_level": 1,
            },
            {
                "cmd": "/xunlei_tasks",
                "action": "xunlei_tasks",
                "desc": "查看迅雷下载任务列表",
                "usage": "/xunlei_tasks",
                "min_level": 1,
            },
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/xunlei/download",
                "endpoint": self.xunlei_download_api,
                "methods": ["POST"],
                "summary": "发送下载任务到迅雷",
                "description": "接收磁力链接或种子URL，发送到迅雷NAS下载",
            },
            {
                "path": "/xunlei/tasks",
                "endpoint": self.xunlei_tasks_api,
                "methods": ["GET"],
                "summary": "获取迅雷下载任务列表",
                "description": "查看当前迅雷NAS的所有下载任务",
            },
            {
                "path": "/xunlei/refresh_token",
                "endpoint": self.xunlei_refresh_token_api,
                "methods": ["POST"],
                "summary": "刷新迅雷认证token",
                "description": "从迅雷NAS获取新的pan_auth token",
            },
            {
                "path": "/xunlei/paths",
                "endpoint": self.xunlei_paths_api,
                "methods": ["GET"],
                "summary": "获取迅雷下载目录列表",
                "description": "获取迅雷NAS配置的所有下载目录",
            },
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'server_url',
                                            'label': '迅雷NAS地址',
                                            'placeholder': 'http://10.0.0.1:2345',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'file_id',
                                            'label': '下载目录ID（留空使用默认）',
                                            'placeholder': '迅雷NAS下载目录的file_id',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'pan_auth',
                                            'label': 'Authorization Token (pan_auth)',
                                            'placeholder': '从迅雷NAS获取的 pan_auth JWT token',
                                            'rows': 3,
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "server_url": "",
            "file_id": "",
            "pan_auth": "",
        }

    def get_page(self) -> List[dict]:
        """
        插件详情页面
        """
        return []

    def stop_service(self):
        """停止插件服务"""
        pass

    # ===== 私有方法 =====

    def _get_base_url(self) -> str:
        if not self._server_url:
            return ""
        return f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi"

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "pan-auth": self._pan_auth,
        }

    def _refresh_token_from_server(self) -> Optional[str]:
        """
        从迅雷NAS HTML页面刷新获取 pan_auth token
        """
        if not self._server_url:
            return None
        try:
            url = f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi/"
            res = RequestUtils().get_res(url=url)
            if res is not None and res.status_code == 200:
                html = res.text
                match = re.search(
                    r'function\s+uiauth\s*\(\s*\w+\s*\)\s*\{\s*return\s*"([^"]+)"',
                    html
                )
                if match:
                    token = match.group(1)
                    logger.info("成功从迅雷NAS刷新 pan_auth token")
                    return token
                else:
                    logger.error("从迅雷NAS页面中未找到 uiauth token，可能需要先登录绑定迅雷账号")
            else:
                logger.error(f"访问迅雷NAS页面失败: {res.status_code if res else 'No response'}")
        except Exception as e:
            logger.error(f"刷新 pan_auth token 失败: {e}")
        return None

    def _create_task(self, url: str, file_id: str = None) -> Tuple[bool, str]:
        """
        创建迅雷下载任务
        """
        base_url = self._get_base_url()
        if not base_url or not self._pan_auth:
            return False, "迅雷下载器未配置或缺少 pan_auth token"

        display_name = _extract_display_name(url)
        task_url = f"{base_url}/drive/v1/task"
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
            res = RequestUtils(headers=self._get_headers()).post_res(
                url=task_url, json=payload
            )
            if res is not None and res.status_code == 200:
                data = res.json()
                if "error" in data:
                    error_msg = data.get("error", "Unknown error")
                    return False, f"迅雷API错误: {error_msg}"
                task_data = data.get("task", data)
                task_id = task_data.get("id", "")
                task_name = task_data.get("name", display_name)
                logger.info(f"迅雷下载任务已创建: {task_id} - {task_name}")
                return True, f"下载任务已创建: {task_name[:40]} (ID: {task_id})"
            else:
                status = res.status_code if res else "No response"
                body = res.text[:500] if res and res.text else ""
                return False, f"创建下载任务失败: HTTP {status} - {body}"
        except Exception as e:
            logger.error(f"创建迅雷下载任务异常: {e}")
            return False, f"创建下载任务异常: {str(e)}"

    def _list_tasks(self, page: int = 1, page_size: int = 50) -> Tuple[bool, list]:
        """
        获取迅雷下载任务列表
        """
        base_url = self._get_base_url()
        if not base_url or not self._pan_auth:
            return False, []

        from urllib.parse import quote
        task_type = quote("user#runner")
        url = f"{base_url}/drive/v1/tasks?type={task_type}&pan_auth={self._pan_auth}&device_space="

        try:
            res = RequestUtils(headers=self._get_headers()).get_res(url=url)
            if res is not None and res.status_code == 200:
                data = res.json()
                tasks = data.get("tasks", data if isinstance(data, list) else [])
                return True, tasks
            else:
                status = res.status_code if res else "No response"
                logger.error(f"获取迅雷任务列表失败: HTTP {status}")
            return False, []
        except Exception as e:
            logger.error(f"获取迅雷任务列表失败: {e}")
            return False, []

    def _list_download_paths(self) -> Tuple[bool, list]:
        """
        获取迅雷下载目录列表
        """
        base_url = self._get_base_url()
        if not base_url or not self._pan_auth:
            return False, []

        try:
            res = RequestUtils(headers=self._get_headers()).get_res(
                url=f"{base_url}/device/download_paths"
            )
            if res is not None and res.status_code == 200:
                data = res.json()
                return True, data if isinstance(data, list) else []
            return False, []
        except Exception as e:
            logger.error(f"获取迅雷下载目录失败: {e}")
            return False, []

    # ===== API 端点 =====

    def xunlei_download_api(self, data: dict = None) -> dict:
        """
        POST /xunlei/download
        """
        if not data:
            return {"success": False, "message": "请提供下载数据"}
        url = data.get("url", "")
        file_id = data.get("file_id", "")
        if not url:
            return {"success": False, "message": "缺少下载URL"}
        success, message = self._create_task(url=url, file_id=file_id)
        return {"success": success, "message": message}

    def xunlei_tasks_api(self, data: dict = None) -> dict:
        """
        GET /xunlei/tasks
        """
        success, tasks = self._list_tasks()
        if not success:
            return {"success": False, "message": "获取任务列表失败", "tasks": []}

        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.get("id", ""),
                "name": task.get("name", ""),
                "state": task.get("state", ""),
                "status": task.get("status", ""),
                "file_size": task.get("file_size", "0"),
                "downloaded": task.get("downloaded", "0"),
                "speed": task.get("speed", ""),
                "created_time": task.get("created_time", ""),
                "updated_time": task.get("updated_time", ""),
                "message": task.get("message", ""),
            })

        return {"success": True, "total": len(task_list), "tasks": task_list}

    def xunlei_refresh_token_api(self, data: dict = None) -> dict:
        """
        POST /xunlei/refresh_token
        """
        token = self._refresh_token_from_server()
        if token:
            self._pan_auth = token
            self.update_config({"pan_auth": token})
            return {"success": True, "message": "Token刷新成功"}
        return {"success": False, "message": "Token刷新失败，请检查迅雷NAS地址和迅雷账号绑定状态"}

    def xunlei_paths_api(self, data: dict = None) -> dict:
        """
        GET /xunlei/paths
        """
        success, paths = self._list_download_paths()
        if not success:
            return {"success": False, "message": "获取下载目录失败", "paths": []}

        path_list = []
        for p in paths:
            path_list.append({
                "id": p.get("Id", ""),
                "name": p.get("FileName", ""),
                "real_path": p.get("RealPath", ""),
            })

        return {"success": True, "paths": path_list}

    # ===== 命令处理 =====

    def xunlei_download(self, command: str, message: str) -> Optional[str]:
        if not message or not message.strip():
            return "用法: /xunlei_download <磁力链接或种子URL>"
        url = message.strip()
        if not url.startswith("magnet:") and not url.startswith("http"):
            return "仅支持磁力链接(magnet:)或HTTP种子链接"
        success, msg = self._create_task(url=url)
        return msg

    def xunlei_refresh_token(self, command: str, message: str) -> Optional[str]:
        token = self._refresh_token_from_server()
        if token:
            self._pan_auth = token
            self.update_config({"pan_auth": token})
            return "✅ pan_auth token 已刷新"
        return "❌ Token 刷新失败，请检查迅雷NAS地址和迅雷账号绑定状态"

    def xunlei_tasks(self, command: str, message: str) -> Optional[str]:
        success, tasks = self._list_tasks()
        if not success:
            return "❌ 获取任务列表失败"
        if not tasks:
            return "📋 当前没有下载任务"

        lines = ["📋 迅雷下载任务:\n"]
        for task in tasks[:10]:
            name = task.get("name", "未知")[:40]
            state = task.get("state", "")
            size = int(task.get("file_size", 0) or 0)
            size_str = f"{size / 1024 / 1024:.1f}MB" if size > 0 else "-"
            lines.append(f"  • {name} | {state} | {size_str}")
        if len(tasks) > 10:
            lines.append(f"\n  ... 共 {len(tasks)} 个任务")
        return "\n".join(lines)

    def stop(self):
        pass
