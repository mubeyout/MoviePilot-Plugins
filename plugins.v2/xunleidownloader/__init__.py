import re
import json
import time
import base64
import logging
import ssl
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen, HTTPError, URLError

from app.log import logger
from app.plugins import _PluginBase
from app.utils.http import RequestUtils

# logger.setLevel(logging.DEBUG)  # loguru 封装无 setLevel


def _extract_display_name(url: str) -> str:
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


# ========== 云 API Token 提取 ==========

SSH_HOST = "127.0.0.1"
SSH_PORT = 22
SSH_USER = "root"
SSH_PASS_FILE = "/mnt/sda1/Works/momo/.ssh_pass"
CLI_PGREP_PATTERN = "xunlei-pan-cli.3.21.0"
CLOUD_API_BASE = "https://api-pan.xunlei.com"


class CloudTokenManager:
    _token: str = ""
    _expire: float = 0
    _ssh_available: Optional[bool] = None

    @classmethod
    def _get_password(cls) -> str:
        try:
            with open(SSH_PASS_FILE, 'r') as f:
                return f.read().strip()
        except Exception:
            return ""

    @classmethod
    def _check_ssh(cls) -> bool:
        if cls._ssh_available is not None:
            return cls._ssh_available
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            cls._ssh_available = s.connect_ex((SSH_HOST, SSH_PORT)) == 0
            s.close()
        except Exception:
            cls._ssh_available = False
        return cls._ssh_available

    @classmethod
    def extract_token(cls) -> Optional[str]:
        import paramiko
        pw = cls._get_password()
        if not pw:
            logger.error("SSH 密码未配置")
            return None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER,
                       password=pw, timeout=5)
            lines = [
                "import re, base64, json, subprocess",
                "pid = subprocess.run(['pgrep', '-f', '" + CLI_PGREP_PATTERN + "'],",
                "    capture_output=True, text=True).stdout.strip().split(chr(10))[0]",
                "if not pid:",
                "    print('NO_CLI'); exit()",
                "maps = open(f'/proc/{pid}/maps').readlines()",
                "found = []",
                "for line in maps:",
                "    parts = line.strip().split()",
                "    if len(parts) < 2 or 'r' not in parts[1]: continue",
                "    try: s, e = [int(x, 16) for x in parts[0].split('-')]",
                "    except: continue",
                "    if e - s > 200*1024*1024: continue",
                "    try:",
                "        with open(f'/proc/{pid}/mem', 'rb', 0) as mem:",
                "            mem.seek(s)",
                "            data = mem.read(min(e - s, 2*1024*1024))",
                "            for m in re.finditer(rb'eyJhbGciOiJSUzI1Ni[A-Za-z0-9_\\-\\.]+', data):",
                "                t = m.group().decode()",
                "                if len(t) > 200 and t not in found:",
                "                    found.append(t)",
                "    except: pass",
                "for t in found:",
                "    dp = t.split('.')",
                "    if len(dp) < 3: continue",
                "    sig = re.sub(r'[^A-Za-z0-9_\\-]', '', dp[2])",
                "    if len(sig) < 20: continue",
                "    candidate = f'{dp[0]}.{dp[1]}.{sig}'",
                "    try:",
                "        p = dp[1]; p += '=' * (4 - len(p) % 4)",
                "        d = json.loads(base64.urlsafe_b64decode(p))",
                "        if d.get('sub') and d.get('exp', 0) > 0:",
                "            print(candidate); break",
                "    except: pass",
            ]
            scan_script = '\n'.join(lines)

            sftp = ssh.open_sftp()
            with sftp.file('/tmp/xl_extract_token.py', 'w') as f:
                f.write(scan_script)
            sftp.close()

            stdin, stdout, stderr = ssh.exec_command(
                'python3 /tmp/xl_extract_token.py', timeout=30)
            token = stdout.read().decode().strip()
            ssh.close()

            if token and len(token) > 200 and token.startswith("eyJ"):
                logger.info(f"云 API token 提取成功: {len(token)} chars")
                return token
            return None
        except Exception as e:
            logger.error(f"SSH token 提取失败: {e}")
            cls._ssh_available = False
            return None

    @classmethod
    def get_token(cls) -> Optional[str]:
        now = time.time()
        if cls._token and now < cls._expire - 3600:
            return cls._token

        token = cls.extract_token()
        if not token:
            remaining = max(0, cls._expire - now)
            if cls._token and remaining > 300:
                logger.warning(f"Token 提取失败, 用旧缓存 (剩余 {remaining:.0f}s)")
                return cls._token
            return None

        cls._token = token
        try:
            parts = token.split('.')
            payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            exp = decoded.get('exp', 0)
            cls._expire = exp if exp > now else now + 86400
            logger.info(f"云 API token 有效期至: "
                       f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cls._expire))}")
        except Exception:
            cls._expire = now + 86400
        return cls._token

    @classmethod
    def is_available(cls) -> bool:
        return cls._check_ssh()


class CloudAPIClient:
    _ssl_ctx: ssl.SSLContext = None

    @classmethod
    def _get_ssl_ctx(cls):
        if cls._ssl_ctx is None:
            cls._ssl_ctx = ssl.create_default_context()
        return cls._ssl_ctx

    @classmethod
    def _call(cls, path: str, method: str = "GET", data: dict = None,
              token: str = None) -> Optional[dict]:
        token = token or CloudTokenManager.get_token()
        if not token:
            return {"error": "no_token", "message": "无法获取 Bearer token"}

        url = f"{CLOUD_API_BASE}{path}"
        body = json.dumps(data).encode() if data else None
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "pan.xunlei.com",
        }
        req = Request(url, data=body, method=method, headers=headers)
        try:
            with urlopen(req, timeout=20, context=cls._get_ssl_ctx()) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            try:
                err_body = e.read().decode()[:500]
            except Exception:
                err_body = ""
            return {"error": f"HTTP_{e.code}", "message": err_body}
        except Exception as e:
            return {"error": str(e), "message": str(e)}

    @classmethod
    def create_task(cls, url: str, name: str = None,
                    parent_folder_id: str = "") -> Tuple[bool, str, dict]:
        if not name:
            name = _extract_display_name(url)
        data = {
            "type": "user#download-url",
            "name": name,
            "file_name": name,
            "file_size": "0",
            "params": {
                "url": url,
                "total_file_count": "0",
                "parent_folder_id": parent_folder_id,
                "mime_type": "",
                "file_id": "",
            }
        }
        result = cls._call("/drive/v1/task", "POST", data)
        if result is None:
            return False, "请求失败", {}
        if "error" in result:
            return False, f"云 API: {result.get('message', '')[:200]}", result
        task = result.get("task", result)
        task_id = task.get("id", "")
        task_name = task.get("name", name)
        logger.info(f"云 API 任务创建成功: {task_id} - {task_name}")
        return True, f"下载任务已创建 (云API): {task_name[:40]}", result

    @classmethod
    def list_tasks(cls, limit: int = 100) -> Tuple[bool, list]:
        result = cls._call(f"/drive/v1/tasks?limit={limit}")
        if result is None or "error" in result:
            return False, []
        return True, result.get("tasks", [])

    @classmethod
    def get_quota(cls) -> Optional[dict]:
        return cls._call("/drive/v1/about?with_quotas=CREATE_OFFLINE_TASK_LIMIT")


# ========== MoviePilot 插件 ==========

class XunleiDownloader(_PluginBase):
    """
    迅雷远程下载器 v3
    双模式: NAS CLI 代理 (优先) + 云 API 直连 (fallback)
    """

    plugin_name = "XunleiDownloader"
    plugin_desc = "迅雷远程下载 (支持云API绕过3任务限制)"
    plugin_icon = "xunlei.png"
    plugin_version = "3.0"
    plugin_author = "MOMO"
    author_url = "https://github.com/mubeyout"
    plugin_config_prefix = "xunlei_"
    plugin_order = 30
    auth_level = 1

    # 模式常量
    MODE_AUTO = "auto"
    MODE_NAS = "nas_proxy"
    MODE_CLOUD = "cloud_api"

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._server_url = (config.get("server_url", "") or "").rstrip("/")
            self._file_id = config.get("file_id", "") or ""
            self._pan_auth = config.get("pan_auth", "") or ""
            self._username = config.get("username", "mubey") or ""
            self._password = config.get("password", "") or ""
            self._mode = config.get("mode", self.MODE_AUTO) or self.MODE_AUTO
        else:
            self._enabled = False
            self._server_url = ""
            self._file_id = ""
            self._pan_auth = ""
            self._username = "mubey"
            self._password = ""
            self._mode = self.MODE_AUTO

        self._basic_auth = ""
        if self._username and self._password:
            self._basic_auth = base64.b64encode(
                f"{self._username}:{self._password}".encode()
            ).decode()

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return [
            {
                "cmd": "/xl",
                "action": "xunlei_download",
                "desc": "迅雷下载磁力/种子",
                "usage": "/xl <magnet_url_or_torrent_url>",
                "min_level": 1,
            },
            {
                "cmd": "/xl_token",
                "action": "xunlei_refresh_token",
                "desc": "刷新迅雷认证token",
                "usage": "/xl_token",
                "min_level": 1,
            },
            {
                "cmd": "/xl_tasks",
                "action": "xunlei_tasks",
                "desc": "查看迅雷下载任务",
                "usage": "/xl_tasks",
                "min_level": 1,
            },
            {
                "cmd": "/xl_status",
                "action": "xunlei_status",
                "desc": "查看迅雷下载器状态",
                "usage": "/xl_status",
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
                "description": "接收磁力链接或种子URL，发送到迅雷下载",
            },
            {
                "path": "/xunlei/tasks",
                "endpoint": self.xunlei_tasks_api,
                "methods": ["GET"],
                "summary": "获取迅雷下载任务列表",
            },
            {
                "path": "/xunlei/refresh_token",
                "endpoint": self.xunlei_refresh_token_api,
                "methods": ["POST"],
                "summary": "刷新迅雷认证token",
            },
            {
                "path": "/xunlei/status",
                "endpoint": self.xunlei_status_api,
                "methods": ["GET"],
                "summary": "查看迅雷下载器状态 (NAS+云API)",
            },
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
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
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'username',
                                            'label': '迅雷NAS用户名',
                                            'placeholder': 'mubey',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'password',
                                            'label': '迅雷NAS密码',
                                            'type': 'password',
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
                                            'label': '下载目录ID (留空使用默认)',
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
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'mode',
                                            'label': '下载模式',
                                            'items': [
                                                {'title': '自动 (NAS优先, 失败切云API)', 'value': 'auto'},
                                                {'title': '仅 NAS CLI 代理', 'value': 'nas_proxy'},
                                                {'title': '仅 云 API 直连', 'value': 'cloud_api'},
                                            ],
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                ]
            }
        ], {
            "enabled": False,
            "server_url": "",
            "username": "mubey",
            "password": "",
            "file_id": "",
            "mode": "auto",
        }

    def get_page(self) -> List[dict]:
        return []

    def stop_service(self):
        pass

    # ===== NAS CLI 代理方法 =====

    def _get_base_url(self) -> str:
        if not self._server_url:
            return ""
        return f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi"

    def _get_pan_auth(self) -> str:
        """从 NAS 面板 HTML 获取 pan-auth JWT (HS256, key=UIAuth, 30min)"""
        now = time.time()
        if self._pan_auth and now < self._pan_auth_expire - 300:
            return self._pan_auth

        try:
            url = f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi/"
            headers = {}
            if self._basic_auth:
                headers["Authorization"] = f"Basic {self._basic_auth}"
            req = Request(url, headers=headers)
            with urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            m = re.search(r'uiauth\(value\)\s*\{\s*return\s*"([^"]+)"', html)
            if m:
                self._pan_auth = m.group(1)
                try:
                    parts = self._pan_auth.split('.')
                    payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
                    decoded = json.loads(base64.urlsafe_b64decode(payload))
                    self._pan_auth_expire = decoded.get('exp', now + 1500)
                except Exception:
                    self._pan_auth_expire = now + 1500
                logger.info("pan_auth token 刷新成功")
        except Exception as e:
            logger.error(f"获取 pan_auth 失败: {e}")
        return self._pan_auth

    def _refresh_token_from_server(self) -> Optional[str]:
        """兼容旧接口: 从 NAS HTML 刷新 pan_auth"""
        if not self._server_url:
            return None
        try:
            url = f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi/"
            res = RequestUtils(headers={
                "Authorization": f"Basic {self._basic_auth}" if self._basic_auth else ""
            }).get_res(url=url)
            if res is not None and res.status_code == 200:
                html = res.text
                match = re.search(
                    r'function\s+uiauth\s*\(\s*\w+\s*\)\s*\{\s*return\s*"([^"]+)"',
                    html
                )
                if match:
                    return match.group(1)
        except Exception as e:
            logger.error(f"刷新 pan_auth token 失败: {e}")
        return None

    def _nas_create_task(self, url: str, name: str = None) -> Tuple[bool, str]:
        """通过 NAS CLI CGI 代理创建任务 (受 3/天限制)"""
        if not name:
            name = _extract_display_name(url)

        token = self._get_pan_auth()
        if not token:
            return False, "未获取到 pan_auth token"

        base_url = self._get_base_url()
        ts = str(int(time.time() * 1000))
        api_url = f"{base_url}/drive/v1/task?pan_auth={token}&device_space=&_={ts}"

        data = {
            "type": "user#download-url",
            "name": name,
            "file_name": name,
            "file_size": "0",
            "space": "",
            "params": {
                "url": url,
                "total_file_count": "0",
                "parent_folder_id": self._file_id or "",
                "mime_type": "",
                "file_id": "",
            }
        }

        headers = {
            "Content-Type": "application/json",
            "pan-auth": token,
        }
        if self._basic_auth:
            headers["Authorization"] = f"Basic {self._basic_auth}"

        try:
            req = Request(api_url, data=json.dumps(data).encode(),
                         method="POST", headers=headers)
            with urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read())
            task = result.get("task", result)
            task_id = task.get("id", "")
            task_name = task.get("name", name)
            logger.info(f"NAS 任务创建成功: {task_id} - {task_name}")
            return True, f"下载任务已创建 (NAS): {task_name[:40]}"
        except HTTPError as e:
            try:
                err_body = e.read().decode()[:300]
            except Exception:
                err_body = ""
            if e.code == 402:
                return False, "NAS_DAILY_LIMIT"
            return False, f"NAS API 错误 HTTP {e.code}: {err_body[:200]}"
        except Exception as e:
            return False, f"NAS 请求异常: {e}"

    def _nas_list_tasks(self) -> Tuple[bool, list]:
        base_url = self._get_base_url()
        token = self._get_pan_auth()
        if not base_url or not token:
            return False, []

        from urllib.parse import quote
        task_type = quote("user#runner")
        url = f"{base_url}/drive/v1/tasks?type={task_type}&pan_auth={token}&device_space="

        headers = {"pan-auth": token}
        if self._basic_auth:
            headers["Authorization"] = f"Basic {self._basic_auth}"

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            tasks = data.get("tasks", data if isinstance(data, list) else [])
            return True, tasks
        except Exception as e:
            logger.error(f"获取 NAS 任务列表失败: {e}")
            return False, []

    # ===== 统一下载接口 =====

    def _download(self, url: str, name: str = None) -> dict:
        """创建下载任务 (按模式选择)"""
        if self._mode == self.MODE_CLOUD:
            modes = [self.MODE_CLOUD]
        elif self._mode == self.MODE_NAS:
            modes = [self.MODE_NAS]
        else:
            modes = [self.MODE_NAS, self.MODE_CLOUD]

        last_error = ""
        for mode in modes:
            try:
                if mode == self.MODE_NAS:
                    success, msg = self._nas_create_task(url, name)
                else:
                    success, msg, _ = CloudAPIClient.create_task(
                        url, name, self._file_id or "")

                if success:
                    return {"success": True, "message": msg, "mode": mode}
                else:
                    last_error = msg
                    logger.info(f"[{mode}] 失败: {msg}")
                    if "NAS_DAILY_LIMIT" in msg and self._mode == self.MODE_AUTO:
                        logger.info("NAS 限额已用, 切换云 API")
                        continue
            except Exception as e:
                last_error = str(e)
                logger.error(f"[{mode}] 异常: {e}")

        return {"success": False, "message": f"所有模式均失败: {last_error}", "mode": "none"}

    # ===== API 端点 =====

    def xunlei_download_api(self, data: dict = None) -> dict:
        if not data:
            return {"success": False, "message": "请提供下载数据"}
        url = data.get("url", "")
        if not url:
            return {"success": False, "message": "缺少下载URL"}
        return self._download(url)

    def xunlei_tasks_api(self, data: dict = None) -> dict:
        """优先用云 API 获取任务列表"""
        if CloudTokenManager.is_available():
            ok, tasks = CloudAPIClient.list_tasks()
            if ok:
                task_list = []
                for t in tasks:
                    task_list.append({
                        "id": t.get("id", ""),
                        "name": t.get("name", ""),
                        "phase": t.get("phase", ""),
                        "file_size": t.get("file_size", "0"),
                        "speed": t.get("speed", ""),
                        "created_time": t.get("created_time", ""),
                    })
                return {"success": True, "total": len(task_list), "tasks": task_list}

        # Fallback to NAS
        ok, tasks = self._nas_list_tasks()
        if not ok:
            return {"success": False, "message": "获取任务列表失败", "tasks": []}
        return {"success": True, "total": len(tasks), "tasks": tasks}

    def xunlei_refresh_token_api(self, data: dict = None) -> dict:
        token = self._refresh_token_from_server()
        if token:
            self._pan_auth = token
            self.update_config({"pan_auth": token})
            return {"success": True, "message": "pan_auth token 刷新成功"}
        return {"success": False, "message": "Token 刷新失败"}

    def xunlei_status_api(self, data: dict = None) -> dict:
        status = {
            "nas_available": bool(self._server_url),
            "nas_token_valid": bool(self._get_pan_auth()),
            "cloud_available": CloudTokenManager.is_available(),
            "mode": self._mode,
        }
        # Cloud quota
        if CloudTokenManager.is_available():
            result = CloudAPIClient.get_quota()
            if result and "error" not in result:
                q = result.get("quotas", {}).get("CREATE_OFFLINE_TASK_LIMIT", {})
                status["cloud_quota_limit"] = q.get("limit", "?")
                status["cloud_quota_usage"] = q.get("usage", "?")
            token = CloudTokenManager.get_token()
            if token:
                parts = token.split('.')
                try:
                    payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
                    decoded = json.loads(base64.urlsafe_b64decode(payload))
                    status["cloud_token_expire"] = time.strftime(
                        '%Y-%m-%d %H:%M:%S',
                        time.localtime(decoded.get('exp', 0)))
                except Exception:
                    pass
        return status

    # ===== 命令处理 =====

    def xunlei_download(self, command: str, message: str) -> Optional[str]:
        if not message or not message.strip():
            return "用法: /xl <磁力链接或种子URL>"
        url = message.strip()
        if not url.startswith("magnet:") and not url.startswith("http"):
            return "仅支持磁力链接(magnet:)或HTTP种子链接"
        result = self._download(url)
        if result["success"]:
            return f"✅ {result['message']} [模式: {result['mode']}]"
        return f"❌ {result['message']}"

    def xunlei_refresh_token(self, command: str, message: str) -> Optional[str]:
        token = self._refresh_token_from_server()
        if token:
            self._pan_auth = token
            self.update_config({"pan_auth": token})
            return "✅ pan_auth token 已刷新"
        # 也尝试刷新云 API token
        if CloudTokenManager.is_available():
            ct = CloudTokenManager.extract_token()
            if ct:
                return "✅ pan_auth 刷新失败, 但云 API token 刷新成功"
            return "❌ Token 刷新失败"
        return "❌ Token 刷新失败"

    def xunlei_tasks(self, command: str, message: str) -> Optional[str]:
        ok, tasks = self._nas_list_tasks()
        if not ok:
            return "❌ 获取任务列表失败"
        if not tasks:
            return "📋 当前没有下载任务"

        lines = ["📋 迅雷下载任务:\n"]
        for task in tasks[:10]:
            name = task.get("name", "未知")[:40]
            phase = task.get("phase", task.get("state", ""))
            size = int(task.get("file_size", 0) or 0)
            size_str = f"{size / 1024 / 1024:.1f}MB" if size > 0 else "-"
            lines.append(f"  • {name} | {phase} | {size_str}")
        if len(tasks) > 10:
            lines.append(f"\n  ... 共 {len(tasks)} 个任务")
        return "\n".join(lines)

    def xunlei_status(self, command: str, message: str) -> Optional[str]:
        result = self.xunlei_status_api()
        lines = ["📊 迅雷下载器状态:\n"]
        lines.append(f"  模式: {result.get('mode', '?')}")
        lines.append(f"  NAS 代理: {'✅' if result.get('nas_available') else '❌'}")
        lines.append(f"  NAS Token: {'✅' if result.get('nas_token_valid') else '❌'}")
        lines.append(f"  云 API: {'✅' if result.get('cloud_available') else '❌'}")
        if result.get('cloud_quota_limit'):
            lines.append(f"  云端配额: {result.get('cloud_quota_usage', '?')}/{result.get('cloud_quota_limit', '?')}")
        if result.get('cloud_token_expire'):
            lines.append(f"  Token过期: {result.get('cloud_token_expire')}")
        return "\n".join(lines)

    def stop(self):
        pass
