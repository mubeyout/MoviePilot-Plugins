import base64
import re
from typing import Optional, Tuple
from urllib.parse import unquote, urlparse

from app.log import logger
from app.utils.http import RequestUtils


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


class Xunlei:
    """迅雷NAS远程下载器 (NAS CLI + 云 API fallback)"""

    _SSH_HOST = "127.0.0.1"
    _SSH_PORT = 22
    _SSH_USER = "root"
    _SSH_PASS_FILE = "/home/mubey/.xl_ssh_pass"
    _CLI_PGREP = "xunlei-pan-cli.3.21.0"
    _CLOUD_API = "https://api-pan.xunlei.com"
    _cloud_token = ""
    _cloud_token_expire = 0.0

    def __init__(self, name: str, server_url: Optional[str] = None,
                 pan_auth: Optional[str] = None,
                 file_id: Optional[str] = None,
                 nas_user: Optional[str] = None,
                 nas_pass: Optional[str] = None,
                 **kwargs):
        self._name = name
        self._server_url = (server_url or "").rstrip("/")
        self._pan_auth = pan_auth or ""
        self._file_id = file_id or ""
        self._nas_user = nas_user or ""
        self._nas_pass = nas_pass or ""

    @property
    def base_url(self) -> str:
        return f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi"

    @property
    def headers(self) -> dict:
        h = {"Content-Type": "application/json", "pan-auth": self._pan_auth}
        # 面板 CGI 的 401 需要 Basic 认证层（仅 pan-auth 会被拒）
        if self._nas_user:
            basic = base64.b64encode(f"{self._nas_user}:{self._nas_pass}".encode()).decode()
            h["Authorization"] = f"Basic {basic}"
        return h

    def is_inactive(self) -> bool:
        """判断是否需要重连（供 SyncDownloadFiles 等插件调用，与 qbittorrent 同款语义）"""
        if not self._server_url:
            return False
        return not (self._pan_auth or self._nas_user or self._cloud_token)

    def test_connection(self) -> Tuple[bool, str]:
        if not self._server_url:
            return False, "未配置服务器地址"
        try:
            self._ensure_fresh_token()
            if not self._pan_auth:
                return False, "获取 pan_auth token 失败"
            res = RequestUtils(headers=self.headers).get_res(url=f"{self.base_url}/device/now")
            if res is not None and res.status_code == 200:
                return True, ""
            return False, f"连接迅雷NAS失败: HTTP {res.status_code if res else 'No response'}"
        except Exception as e:
            return False, f"连接异常: {str(e)}"

    def refresh_token(self) -> Optional[str]:
        if not self._server_url:
            return None
        try:
            import requests as _req
            url = f"{self._server_url}/webman/3rdparty/pan-xunlei-com/index.cgi/"
            if self._nas_user and self._nas_pass:
                auth = (self._nas_user, self._nas_pass)
            else:
                auth = None
            try:
                res = RequestUtils().get_res(url=url)
                if res is None or res.status_code != 200:
                    raise Exception(f"HTTP {res.status_code if res else 'None'}")
            except Exception:
                try:
                    res = _req.get(url, auth=auth, timeout=10, allow_redirects=True)
                except Exception:
                    return None
            if res is not None and res.status_code == 200:
                match = re.search(r'function\s+uiauth\s*\(\s*\w+\s*\)\s*\{\s*return\s*"([^"]+)"', res.text)
                if match:
                    logger.info(f"迅雷下载器 {self._name} pan_auth token 刷新成功")
                    return match.group(1)
                else:
                    logger.error(f"迅雷下载器 {self._name} 未找到 uiauth token")
            else:
                logger.error(f"迅雷下载器 {self._name} 访问NAS页面失败: HTTP {res.status_code if res else 'None'}")
        except Exception as e:
            logger.error(f"迅雷下载器 {self._name} 刷新token失败: {e}")
        return None

    def _ensure_fresh_token(self) -> Optional[str]:
        """每次使用前刷新 token"""
        import time as _t, base64 as _b64
        token = self.refresh_token()
        if token:
            self._pan_auth = token
            try:
                parts = token.split(".")
                payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
                data = json.loads(_b64.urlsafe_b64decode(payload))
                if data.get("exp", 0) < _t.time():
                    logger.warning(f"迅雷下载器 {self._name} token 已过期, 再刷新一次")
                    token2 = self.refresh_token()
                    if token2:
                        self._pan_auth = token2
            except Exception:
                pass
        return self._pan_auth

    def _post_task(self, url: str, payload: dict):
        import requests as _req
        try:
            res = RequestUtils(headers=self.headers).post_res(url=url, json=payload)
            if res is None:
                res = _req.post(url, json=payload, headers=self.headers, timeout=30)
        except Exception:
            res = _req.post(url, json=payload, headers=self.headers, timeout=30)
        return res

    # ===== Cloud API (bypasses 3-task/day NAS CLI limit) =====

    def _extract_cloud_token(self) -> Optional[str]:
        """从 NAS CLI 进程内存提取云 API Bearer token (via sshpass+ssh)"""
        import subprocess as _sp, tempfile as _tf
        try:
            with open(self._SSH_PASS_FILE, 'r') as _f:
                _pw = _f.read().strip()
        except Exception:
            return None
        try:
            # Upload scan script via sshpass
            _scan = (
                "import re,json,subprocess\n"
                "pid=subprocess.run(['pgrep','-f','" + self._CLI_PGREP + "'],"
                "capture_output=True,text=True).stdout.strip().split(chr(10))[0]\n"
                "if not pid: print('NO_CLI'); exit()\n"
                "maps=open(f'/proc/{pid}/maps').readlines()\n"
                "found=[]\n"
                "for line in maps:\n"
                "  p=line.strip().split()\n"
                "  if len(p)<2 or 'r' not in p[1]: continue\n"
                "  try: s,e=[int(x,16) for x in p[0].split('-')]\n"
                "  except: continue\n"
                "  if e-s>200*1024*1024: continue\n"
                "  try:\n"
                "    with open(f'/proc/{pid}/mem','rb',0) as mem:\n"
                "      mem.seek(s)\n"
                "      data=mem.read(min(e-s,2*1024*1024))\n"
                "      for m in re.finditer(rb'eyJhbGciOiJSUzI1Ni[A-Za-z0-9_\-\.]+',data):\n"
                "        t=m.group().decode()\n"
                "        if len(t)>200 and t not in found: found.append(t)\n"
                "  except: pass\n"
                "for t in found:\n"
                "  dp=t.split('.')\n"
                "  if len(dp)<3: continue\n"
                "  sig=re.sub(r'[^A-Za-z0-9_\-]','',dp[2])\n"
                "  if len(sig)<20: continue\n"
                "  c=f'{dp[0]}.{dp[1]}.{sig}'\n"
                "  try:\n"
                "    p2=dp[1]; p2+='='*(4-len(p2)%4)\n"
                "    d=json.loads(__import__('base64').urlsafe_b64decode(p2))\n"
                "    if d.get('sub') and d.get('exp',0)>0:\n"
                "      print(c); break\n"
                "  except: pass\n"
            )
            # Write script locally, scp to NAS
            _script_path = "/tmp/xl_cloud_scan.py"
            with open(_script_path, 'w') as _f:
                _f.write(_scan)
            # scp
            _scp = _sp.run(
                ['sshpass', '-p', _pw, 'scp', '-o', 'StrictHostKeyChecking=no',
                 _script_path, f'{self._SSH_USER}@{self._SSH_HOST}:/tmp/xl_cloud_scan.py'],
                capture_output=True, text=True, timeout=10
            )
            # ssh execute
            _result = _sp.run(
                ['sshpass', '-p', _pw, 'ssh', '-o', 'StrictHostKeyChecking=no',
                 f'{self._SSH_USER}@{self._SSH_HOST}',
                 'python3 /tmp/xl_cloud_scan.py'],
                capture_output=True, text=True, timeout=30
            )
            _token = _result.stdout.strip()
            _scan = (
                "import re,json,subprocess\n"
                "pid=subprocess.run(['pgrep','-f','" + self._CLI_PGREP + "'],"
                "capture_output=True,text=True).stdout.strip().split(chr(10))[0]\n"
                "if not pid: print('NO_CLI'); exit()\n"
                "maps=open(f'/proc/{pid}/maps').readlines()\n"
                "found=[]\n"
                "for line in maps:\n"
                "  p=line.strip().split()\n"
                "  if len(p)<2 or 'r' not in p[1]: continue\n"
                "  try: s,e=[int(x,16) for x in p[0].split('-')]\n"
                "  except: continue\n"
                "  if e-s>200*1024*1024: continue\n"
                "  try:\n"
                "    with open(f'/proc/{pid}/mem','rb',0) as mem:\n"
                "      mem.seek(s)\n"
                "      data=mem.read(min(e-s,2*1024*1024))\n"
                "      for m in re.finditer(rb'eyJhbGciOiJSUzI1Ni[A-Za-z0-9_\\-\\.]+',data):\n"
                "        t=m.group().decode()\n"
                "        if len(t)>200 and t not in found: found.append(t)\n"
                "  except: pass\n"
                "for t in found:\n"
                "  dp=t.split('.')\n"
                "  if len(dp)<3: continue\n"
                "  sig=re.sub(r'[^A-Za-z0-9_\\-]','',dp[2])\n"
                "  if len(sig)<20: continue\n"
                "  c=f'{dp[0]}.{dp[1]}.{sig}'\n"
                "  try:\n"
                "    p2=dp[1]; p2+='='*(4-len(p2)%4)\n"
                "    d=json.loads(__import__('base64').urlsafe_b64decode(p2))\n"
                "    if d.get('sub') and d.get('exp',0)>0:\n"
                "      print(c); break\n"
                "  except: pass\n"
            )
            if _token and len(_token) > 200 and _token.startswith("eyJ"):
                logger.info(f"迅雷下载器 {self._name} 云 API token 提取成功 ({len(_token)} chars)")
                return _token
            else:
                logger.warning(f"迅雷下载器 {self._name} cloud token empty, stderr: {_result.stderr[:200]}")
        except Exception as _e:
            logger.error(f"迅雷下载器 {self._name} 云 API token 提取失败: {_e}")
        return None

    def _get_cloud_token(self) -> Optional[str]:
        """获取有效的云 API token (带缓存, 提前1h刷新)"""
        import time as _t
        _now = _t.time()
        if Xunlei._cloud_token and _now < Xunlei._cloud_token_expire - 3600:
            return Xunlei._cloud_token
        _token = self._extract_cloud_token()
        if _token:
            Xunlei._cloud_token = _token
            try:
                import base64
                _parts = _token.split(".")
                _payload = _parts[1] + "=" * (4 - len(_parts[1]) % 4)
                _data = json.loads(base64.urlsafe_b64decode(_payload))
                Xunlei._cloud_token_expire = _data.get("exp", _now + 86400)
            except Exception:
                Xunlei._cloud_token_expire = _now + 86400
        return _token if _token else (Xunlei._cloud_token if _now < Xunlei._cloud_token_expire else None)

    def _add_task_cloud(self, url: str, display_name: str) -> Tuple[Optional[str], Optional[str]]:
        """通过云 API 创建任务 (不受 NAS CLI 3任务限制)"""
        import ssl as _ssl
        from urllib.request import Request as _Req, urlopen as _open, HTTPError
        _token = self._get_cloud_token()
        if not _token:
            return None, "云 API token 获取失败"
        _payload = {
            "type": "user#download-url",
            "name": display_name,
            "file_name": display_name,
            "file_size": "0",
            "params": {
                "url": url,
                "total_file_count": "0",
                "parent_folder_id": self._file_id or "",
                "mime_type": "",
                "file_id": "",
            }
        }
        _headers = {
            "Authorization": f"Bearer {_token}",
            "Content-Type": "application/json",
            "User-Agent": "pan.xunlei.com",
        }
        _req = _Req(f"{self._CLOUD_API}/drive/v1/task",
                     data=json.dumps(_payload).encode(), method="POST", headers=_headers)
        try:
            with _open(_req, timeout=20, context=_ssl.create_default_context()) as _resp:
                _data = _resp.json()
            if "error" in _data:
                return None, f"云 API 错误: {_data.get('error_description', _data.get('error', ''))[:100]}"
            _task = _data.get("task", _data)
            _task_id = _task.get("id", "")
            _task_name = _task.get("name", display_name)
            logger.info(f"迅雷下载器 {self._name} 云 API 任务创建成功: {_task_id} - {_task_name}")
            return _task_id, None
        except HTTPError as _e:
            _body = ""
            try: _body = _e.read().decode()[:200]
            except Exception: pass
            return None, f"云 API HTTP {_e.code}: {_body[:100]}"
        except Exception as _e:
            return None, f"云 API 异常: {_e}"

    # ===== Main task creation =====

    def _torrent_to_magnet(self, url: str) -> Optional[str]:
        """下载 .torrent 文件并转换为磁力链接"""
        try:
            import hashlib, base64 as _b64, ssl as _ssl
            from urllib.request import Request as _Req, urlopen as _open
            _req = _Req(url)
            with _open(_req, timeout=30, context=_ssl.create_default_context()) as _resp:
                _data = _resp.read()
            # Parse bencode to find info_hash
            # Simple bencode parser: find "info" dict, hash its raw bytes
            _idx = _data.find(b'4:info')
            if _idx < 0:
                _idx = _data.find(b'info')  # try without length prefix
            if _idx < 0:
                logger.warning(f"迅雷下载器 {self._name} .torrent 文件解析失败: 找不到 info")
                return None
            # Skip "4:info" or "info"
            if _data[_idx:_idx+6] == b'4:info':
                _info_start = _idx + 6
            else:
                _info_start = _idx + 4
            # Decode bencode value to find its end, then hash raw bytes
            _end = self._bencode_skip(_data, _info_start)
            if _end <= _info_start:
                _end = len(_data)
            _info_raw = _data[_info_start:_end]
            _info_hash = hashlib.sha1(_info_raw).hexdigest().upper()
            # Extract name from torrent
            _name = ""
            _name_idx = _data.find(b'4:name')
            if _name_idx >= 0:
                _nstart = _name_idx + 6
                _plen = self._bencode_read_int(_data, _nstart)
                if _plen > 0 and _plen < 500:
                    _nstart2 = _plen_len = len(str(_plen)) + 1
                    _nstart += len(str(_plen)) + 1
                    _name = _data[_nstart:_nstart + _plen].decode('utf-8', errors='ignore')
            _magnet = f"magnet:?xt=urn:btih:{_info_hash}"
            if _name:
                _magnet += f"&dn={_name}"
            logger.info(f"迅雷下载器 {self._name} .torrent 转磁力: {_magnet[:80]}")
            return _magnet
        except Exception as _e:
            logger.error(f"迅雷下载器 {self._name} .torrent 转磁力失败: {_e}")
            return None

    @staticmethod
    def _bencode_read_int(data: bytes, pos: int) -> int:
        """Read bencode integer"""
        end = data.index(b'e', pos)
        return int(data[pos+1:end])

    @staticmethod
    def _bencode_skip(data: bytes, pos: int) -> int:
        """Skip one bencode value, return end position"""
        if pos >= len(data):
            return pos
        c = chr(data[pos])
        if c == 'i':  # integer
            return data.index(b'e', pos) + 1
        elif c == 'l' or c == 'd':  # list or dict
            pos += 1
            while data[pos] != ord('e'):
                pos = Xunlei._bencode_skip(data, pos)
            return pos + 1
        elif c.isdigit():  # string
            colon = data.index(b':', pos)
            length = int(data[pos:colon])
            return colon + 1 + length
        return pos + 1

    def add_task(self, url: str, download_dir: str = None) -> Tuple[Optional[str], Optional[str]]:
        """创建下载任务: NAS CLI 优先, 3任务限制时自动 fallback 云 API"""
        # .torrent 文件自动转磁力
        if url.endswith('.torrent') and not url.startswith('magnet:'):
            magnet = self._torrent_to_magnet(url)
            if magnet:
                url = magnet
            else:
                return None, "torrent 文件解析失败"
        self._ensure_fresh_token()
        if not self._pan_auth:
            return None, "pan_auth token 获取失败，请确认迅雷NAS地址和账号绑定状态"

        display_name = _extract_display_name(url)
        payload = {
            "kind": "drive#task",
            "type": "user#download-url",
            "name": display_name,
            "file_name": display_name,
            "file_size": "0",
            "params": {
                "url": url,
                "total_file_count": "0",
                "parent_folder_id": self._file_id or "",
                "mime_type": "",
                "file_id": "",
            }
        }

        task_url = f"{self.base_url}/drive/v1/task"

        try:
            res = self._post_task(task_url, payload)

            if res is None:
                return None, "迅雷NAS无响应"

            if hasattr(res, 'status_code') and res.status_code == 401:
                logger.warning(f"迅雷下载器 {self._name} token 过期(401)，尝试刷新")
                new_token = self.refresh_token()
                if new_token:
                    self._pan_auth = new_token
                    res = self._post_task(task_url, payload)
                else:
                    return None, "pan_auth token 过期且刷新失败"

            try:
                data = res.json()
            except Exception:
                return None, f"HTTP {res.status_code}: {res.text[:200]}"

            if "error" in data:
                error_code = data.get("error", "")
                error_desc = data.get("error_description", "")

                if error_code == "unauthorized" or (hasattr(res, 'status_code') and res.status_code == 401):
                    return None, "迅雷token无效或已过期，请在迅雷NAS中重新绑定账号"

                if error_code == "task_create_count_limit":
                    # NAS CLI 3任务/天限制 → 自动切换云 API
                    logger.warning(f"迅雷下载器 {self._name} NAS CLI 任务限额, 切换云 API")
                    return self._add_task_cloud(url, display_name)

                return None, f"迅雷错误: {error_code} - {error_desc}"

            task = data.get("task", {})
            task_id = task.get("id", "")
            task_name = task.get("name", display_name)
            logger.info(f"迅雷下载器 {self._name} 创建任务: {task_id} - {task_name}")
            return task_id, None
        except Exception as e:
            logger.error(f"迅雷下载器 {self._name} 创建任务失败: {e}")
            return None, str(e)

    def get_tasks(self) -> Tuple[Optional[list], Optional[str]]:
        """获取任务列表"""
        self._ensure_fresh_token()
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
