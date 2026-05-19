# MoviePilot 补丁说明

本目录包含 MoviePilot 的核心补丁文件，用于实现自定义功能（ByteMuse 探索详情、成人内容搜索、前端增强等）。

> **版本对应**: MoviePilot v2.10.2 (`jxxghp/moviepilot:2.10.2`)
> **更新日期**: 2026-05-19

---

## 补丁清单

### 1. `entrypoint.sh` — 容器启动入口（总调度）

**作用**: 替代原始 entrypoint，在 MoviePilot 启动前执行所有补丁。

**主要功能**:
- 降级 FastAPI/Starlette 兼容性 (`fastapi==0.115.6`)
- 注入 ByteMuseDiscover / MetatubeSource / AdultSubscribe 插件
- 补丁 `tmdb.py`、`media.py`、`search.py` 核心文件
- 注入前端剧照/灯箱脚本 (通过 `inject_stills.py`)
- 补丁 nginx 缓存策略

---

### 2. `media_patched.py` → `media.py`

**作用**: ByteMuse 媒体详情 API 增强。

**改动内容**:
- 拦截非数字 tmdb_id（如 `MIHD-001`），从 ByteMuse API 获取详情
- 返回 `stills`（剧照列表，含图片代理）
- 返回 `recommendations`（同演员作品，通过 ByteMuse 搜索）
- 返回 `similar`（类似作品，调用 PluginManager 获取 new_releases）
- 返回 `source: bytemuse` 标识来源
- 使用 `http.client` 替代 `requests`（MoviePilot 进程内 requests 被代理干扰会卡死）

---

### 3. `tmdb_patched.py` → `tmdb.py`

**作用**: TMDB 端点补丁，支持 metatube_search 前缀。

**挂载**: entrypoint.sh 中 cp

---

### 4. `search_patched.py` → `search.py`

**作用**: 搜索端点补丁，支持 adult/normal/all 搜索类型。

---

### 5-9. `chain_search.py`, `chain_init.py`, `indexer_init.py`, `spider_init.py`, `mtorrent.py`

**作用**: 搜索链路 + 爬虫补丁，支持成人内容搜索。

**挂载**: docker-compose.yml 中直接挂载到容器（`ro`），容器更新后不受影响。

---

### 10. `nginx_common_patched.conf` → `/etc/nginx/common.conf`

**作用**: nginx 缓存策略。

**注意**: 不能用 `{n,m}` 正则花括号（nginx 会当成配置块分隔符，导致启动失败）。

---

### 11. `stills-inject.js` — 前端注入脚本 (v13)

**作用**: ByteMuse 详情页增强。

**功能**:
- **剧照 slider**: 横向滚动展示剧照，点击弹出灯箱（◀▶ 按钮 + 键盘左右 + 缩略图条），注入到 `media-overview`
- **推荐**: 同演员作品（排除当前作品），填充到 MoviePilot 原生"推荐"slider
- **类似**: 今日上新内容，填充到 MoviePilot 原生"类似"slider
- 不再隐藏原生 slider，而是检测到空 slider 后填充内容

**技术方案**:
- 直连插件匿名 API `/api/v1/plugin/ByteMuseDiscover/bytemuse_detail/{mediaid}`
- 不依赖 JSON.parse hook 或 MoviePilot media API
- hashchange 后 300ms 发请求，数据到达即注入（首次进入即可显示）
- 等待 Vue 渲染原生 slider 后再填充（重试机制，最多 12 秒）

---

### 12. `inject_stills.py` — 注入辅助脚本

**作用**: 将 loader 注入到 index.html。

**实现**:
- 在 `<head>` 内注入 inline `<script>` 安装 JSON.parse hook（向后兼容，v13 不再依赖但保留）
- 在 `</body>` 前注入 `<script src="/stills-inject.js?v=timestamp">`（外部加载，绕过 SW 缓存）
- 将 stills-inject.js 复制到 `/public/` 目录（nginx root）

**重要**: 前端文件（stills-inject.js、inject_stills.py）必须放在宿主机 `/config` 挂载目录下，因为 docker-compose 的 volume 挂载会遮盖镜像内 COPY 的文件。

### 13. ByteMuseDiscover 插件增强

**新增匿名 API**: `/api/v1/plugin/ByteMuseDiscover/bytemuse_detail/{mediaid}`（`allow_anonymous: True`）

**返回数据**:
- `stills`: 剧照列表（图片代理 URL）
- `similar`: 同演员作品（排除当前作品，最多 12 条）
- `monthly`: 今日上新内容（排除当前作品和同演员作品，最多 12 条）

**技术细节**:
- ByteMuse 月榜单 API 数据为空（`/api/v1/ranks?type=monthly` 返回 `[]`），"类似"栏使用今日上新替代
- 使用 `http.client` + JWT 登录（`RequestUtils` 在 MoviePilot 进程内被代理干扰）
- `import json` 必须显式声明（插件文件顶部无此 import）

---

## 重新部署步骤

### 方式一：自定义镜像（推荐）

```bash
# 1. 克隆仓库
cd /mnt/nvme0n1p1/MubeyWork/MUBEY/PandoraBox/MoviePilot-Plugins

# 2. 构建镜像
docker build -t mubeyout/moviepilot:2.10.2-patched .

# 3. 复制前端注入文件到宿主机配置目录（必须！volume 挂载会遮盖镜像 COPY）
cp patches/moviepilot-core/stills-inject.js /mnt/nvme0n1p1/Configs/MoviePilot/
cp patches/moviepilot-core/inject_stills.py /mnt/nvme0n1p1/Configs/MoviePilot/
cp patches/moviepilot-core/nginx_common_patched.conf /mnt/nvme0n1p1/Configs/MoviePilot/

# 4. docker-compose up -d MoviePilot
```

**优势**: 后端 Python 补丁全部 baked in 镜像，启动快（~15s），不需要运行时 cp。

**前端文件为什么必须手动复制到 /config?**
docker-compose 中 `/config` volume 挂载会完全遮盖镜像内 `/config` 目录。所以 `stills-inject.js` 和 `inject_stills.py` 需要放在宿主机的挂载目录下。

### 方式二：仅用补丁文件（不用自定义镜像）

```bash
# 1. 复制所有补丁文件
cp patches/moviepilot-core/* /mnt/nvme0n1p1/Configs/MoviePilot/
mkdir -p /mnt/nvme0n1p1/Configs/MoviePilot/patches
cp patches/moviepilot-core/entrypoint.sh /mnt/nvme0n1p1/Configs/MoviePilot/patches/

# 2. 复制插件
cp -r plugins.v2/bytemusediscover /mnt/nvme0n1p1/Configs/MoviePilot/plugins/v2/
cp -r plugins.v2/metatubesource /mnt/nvme0n1p1/Configs/MoviePilot/plugins/v2/

# 3. docker-compose up -d MoviePilot
```

### 容器启动后热更新前端（无需重启）

```bash
# 修改 stills-inject.js 后，在容器内重新执行注入脚本
docker exec MoviePilot python3 /config/inject_stills.py
# 浏览器 Ctrl+Shift+R 强制刷新
```

---

## docker-compose.yml 挂载配置

```yaml
services:
  MoviePilot:
    image: mubeyout/moviepilot:2.10.2-patched
    container_name: MoviePilot
    volumes:
      - /mnt/nvme0n1p1/Configs/MoviePilot:/config
      - /mnt/nvme0n1p1/Configs/MoviePilot/cache:/moviepilot/.cache
      - /mnt/nvme0n1p1:/mnt
      - /var/run/docker.sock:/var/run/docker.sock
      # 后端补丁挂载（方式二才需要，方式一已 baked in）
      # - /mnt/nvme0n1p1/Configs/MoviePilot/patches/entrypoint.sh:/entrypoint.sh:ro
      # - /mnt/nvme0n1p1/Configs/MoviePilot/mtorrent.py:/app/app/modules/indexer/spider/mtorrent.py:ro
      # - /mnt/nvme0n1p1/Configs/MoviePilot/spider_init.py:/app/app/modules/indexer/spider/__init__.py:ro
      # - /mnt/nvme0n1p1/Configs/MoviePilot/indexer_init.py:/app/app/modules/indexer/__init__.py:ro
      # - /mnt/nvme0n1p1/Configs/MoviePilot/chain_init.py:/app/app/chain/__init__.py:ro
      # - /mnt/nvme0n1p1/Configs/MoviePilot/chain_search.py:/app/app/chain/search.py:ro
    environment:
      - SUPERUSER=mubey
      - MOVIEPILOT_AUTO_UPDATE=none
```

---

## 官方更新时如何迁移

```bash
# 1. 修改 Dockerfile 中 FROM 版本号
# FROM jxxghp/moviepilot:2.10.2  →  FROM jxxghp/moviepilot:2.11.0

# 2. 更新补丁文件（重新 diff 原始文件）
# media_patched.py、tmdb_patched.py、search_patched.py 需要基于新版本重新 diff

# 3. 重新构建
docker build -t mubeyout/moviepilot:2.11.0-patched .
```

---

## 重要教训

1. **MoviePilot 进程内 requests 不可用** — 被框架级代理干扰，必须用 `http.client`
2. **nginx 正则不能用 `{n,m}` 花括号** — 被当作配置块分隔符，导致 nginx 启动失败 → 容器循环重启
3. **Volume 挂载遮盖镜像 COPY** — `/config` 挂载完全遮盖镜像内文件，前端注入文件必须放宿主机
4. **Service Worker 缓存** — MoviePilot 前端有 SW precache，内联脚本到 `</body>` 太晚（Vue 先执行了），必须注入到 `<head>`
5. **前端 JS 外部加载不能含 `<script>` 标签** — `<script src="x.js">` 加载的文件里如果有 `<script>` 标签会报语法错误
6. **JSON.parse hook 是最可靠的前端拦截方式** — 不依赖 HTTP 库（axios/fetch/XHR），任何 JSON 响应都会经过
