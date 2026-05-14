# MoviePilot 补丁说明

本目录包含 MoviePilot 的核心补丁文件，用于实现自定义功能（ByteMuse 探索详情、成人内容搜索、前端增强等）。

> **版本对应**: MoviePilot v2.10.2 (`jxxghp/moviepilot:2.10.2`)
> **更新日期**: 2026-05-14

---

## 补丁清单

### 1. `entrypoint.sh` — 容器启动入口（总调度）

**作用**: 替代原始 entrypoint，在 MoviePilot 启动前执行所有补丁。

**主要功能**:
- 降级 FastAPI/Starlette 兼容性 (`fastapi==0.115.6`)
- 注入 ByteMuseDiscover / MetatubeSource / AdultSubscribe 插件
- 补丁 `tmdb.py`、`media.py`、`search.py` 核心文件
- 注入前端剧照/灯箱脚本 (`stills-inject.js`)
- 禁用 nginx 对 JS/CSS 的激进缓存（解决前端补丁不生效问题）

**挂载**: `/mnt/nvme0n1p1/Configs/MoviePilot/patches/entrypoint.sh → /entrypoint.sh:ro`

---

### 2. `media_patched.py` → `media.py`

**作用**: ByteMuse 媒体详情 API 增强。

**改动内容**:
- 拦截非数字 tmdb_id（如 `MIHD-001`），从 ByteMuse API 获取详情
- 返回 `stills`（剧照列表，含图片代理）
- 返回 `recommendations`（同演员作品，通过 ByteMuse 搜索）
- 返回 `source: bytemuse` 标识来源

**挂载**: entrypoint.sh 中 `cp /config/media_patched.py /app/app/api/endpoints/media.py`

---

### 3. `tmdb_patched.py` → `tmdb.py`

**作用**: TMDB 端点补丁，支持 metatube_search 前缀。

**改动内容**:
- `detail` / `recommendations` / `similar` 端点识别 `metatube_search:CODE` 格式
- 将请求路由到内部 ByteMuse 详情 API
- 修改原生"推荐"和"类似" slider 的数据源

**挂载**: entrypoint.sh 中 `cp /config/tmdb_patched.py /app/app/api/endpoints/tmdb.py`

---

### 4. `search_patched.py` → `search.py`

**作用**: 搜索端点补丁。

**改动内容**:
- 支持 `search_type=adult` / `search_type=normal` / `search_type=all` 参数
- 成人搜索时同时请求普通 + adult 分类

**挂载**: entrypoint.sh 中 `cp /config/search_patched.py /app/app/api/endpoints/search.py`

---

### 5. `chain_search.py` → `chain/search.py`

**作用**: 搜索链路补丁。

**改动内容**:
- 新增 `search_type` 参数支持（normal/adult/all/auto）
- 成人内容搜索支持（mTeam + NexusPHP 通用站点）

**挂载**: `docker-compose.yml` 中直接挂载到容器

---

### 6. `chain_init.py` → `chain/__init__.py`

**作用**: 链路初始化补丁。

**改动内容**:
- 配合 search_type 参数的链路支持

**挂载**: `docker-compose.yml` 中直接挂载到容器

---

### 7. `indexer_init.py` → `modules/indexer/__init__.py`

**作用**: 索引器初始化补丁。

**改动内容**:
- 成人搜索相关初始化逻辑

**挂载**: `docker-compose.yml` 中直接挂载到容器

---

### 8. `spider_init.py` → `modules/indexer/spider/__init__.py`

**作用**: 爬虫模块初始化补丁。

**改动内容**:
- mTeam 站点支持 adult 模式搜索（`mode=adult`）
- NexusPHP 通用站点强制 `allsec=1`（包含成人内容）

**挂载**: `docker-compose.yml` 中直接挂载到容器

---

### 9. `mtorrent.py` → `modules/indexer/spider/mtorrent.py`

**作用**: mTorrent 爬虫补丁。

**改动内容**:
- 搜索时同时请求普通 + adult 分类（`mode=adult`）
- 成人分类 ID 映射

**挂载**: `docker-compose.yml` 中直接挂载到容器

---

### 10. `nginx_common_patched.conf` → `/etc/nginx/common.conf`

**作用**: 禁用 nginx 对静态资源的激进缓存。

**改动内容**:
- 前端 JS/CSS 不再被浏览器长期缓存
- 确保前端补丁更新后用户能立即看到变化

**挂载**: entrypoint.sh 中 `cp /config/nginx_common_patched.conf /etc/nginx/common.conf`

---

### 11. `stills-inject.js` — 前端注入脚本 (v3)

**作用**: ByteMuse 详情页增强。

**功能**:
- **剧照 slider**: 横向滚动展示剧照，点击弹出灯箱（◀▶ 按钮 + 键盘左右 + 触摸滑动 + 底部缩略图条）
- **类似作品 slider**: 从 ByteMuse discover API 获取今日上新，横向滚动
- 自动隐藏原生空的"类似"slider

**注入方式**: entrypoint.sh 通过 `inject_stills.py` 注入到 `/public/index.html`

---

### 12. `inject_stills.py` — 注入辅助脚本

**作用**: 将 `stills-inject.js` 安全注入到 index.html。

**实现**: 使用 Python + regex 替代 sed（避免特殊字符转义问题）

**挂载**: entrypoint.sh 中 `python3 /config/inject_stills.py`

---

## 重新部署步骤

### 前置条件

- MoviePilot v2.10.2 Docker 镜像
- ByteMuse 服务运行在 `10.0.0.1:3750`
- MoviePilot 配置目录: `/mnt/nvme0n1p1/Configs/MoviePilot`

### 部署步骤

1. **复制补丁文件到配置目录**:
   ```bash
   cp patches/moviepilot-core/* /mnt/nvme0n1p1/Configs/MoviePilot/
   # entrypoint.sh 放到 patches 子目录
   mkdir -p /mnt/nvme0n1p1/Configs/MoviePilot/patches
   cp patches/moviepilot-core/entrypoint.sh /mnt/nvme0n1p1/Configs/MoviePilot/patches/
   ```

2. **复制插件到配置目录**:
   ```bash
   cp -r plugins.v2/bytemusediscover /mnt/nvme0n1p1/Configs/MoviePilot/plugins/v2/
   cp -r plugins.v2/metatubesource /mnt/nvme0n1p1/Configs/MoviePilot/plugins/v2/
   ```

3. **确保 docker-compose.yml 包含正确的挂载**:
   ```yaml
   volumes:
     - /mnt/nvme0n1p1/Configs/MoviePilot:/config
     - /mnt/nvme0n1p1/Configs/MoviePilot/cache:/moviepilot/.cache
     - /mnt/nvme0n1p1/Configs/MoviePilot/mtorrent.py:/app/app/modules/indexer/spider/mtorrent.py:ro
     - /mnt/nvme0n1p1/Configs/MoviePilot/spider_init.py:/app/app/modules/indexer/spider/__init__.py:ro
     - /mnt/nvme0n1p1/Configs/MoviePilot/indexer_init.py:/app/app/modules/indexer/__init__.py:ro
     - /mnt/nvme0n1p1/Configs/MoviePilot/chain_init.py:/app/app/chain/__init__.py:ro
     - /mnt/nvme0n1p1/Configs/MoviePilot/chain_search.py:/app/app/chain/search.py:ro
     - /mnt/nvme0n1p1/Configs/MoviePilot/patches/entrypoint.sh:/entrypoint.sh:ro
     - PLUGIN_LOCAL_REPO_PATHS=/config/plugins
   ```

4. **启动容器**:
   ```bash
   docker compose up -d MoviePilot
   ```

5. **验证**:
   - 浏览器访问 MoviePilot → ByteMuse 探索 → 点击任意媒体
   - 确认剧照 slider 显示
   - 确认推荐 slider 显示同演员作品
   - 确认类似 slider 显示今日上新
   - 点击剧照确认灯箱正常（支持左右切换）

### 注意事项

- `media_patched.py` 等核心补丁文件是从 `MoviePilot v2.10.2` 原始文件修改而来，如果 MoviePilot 更新大版本，需要重新 diff 合并
- `chain_*.py`、`indexer_*.py`、`spider_*.py`、`mtorrent.py` 通过 docker-compose 直接挂载（`ro`），容器更新后不受影响
- `tmdb_patched.py`、`media_patched.py`、`search_patched.py` 通过 entrypoint.sh 在容器启动时复制（容器更新后会被还原，entrypoint 会重新打补丁）
- `stills-inject.js` 注入到 `/public/index.html`（容器更新后会被还原，entrypoint 会重新注入）
