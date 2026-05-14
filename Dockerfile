FROM jxxghp/moviepilot:2.10.2

# ============ 后端 Python 补丁 ============

# ByteMuse 媒体详情 API（stills, recommendations, source 标识）
COPY patches/moviepilot-core/media_patched.py /app/app/api/endpoints/media.py

# TMDB 端点（metatube_search 前缀路由到 ByteMuse）
COPY patches/moviepilot-core/tmdb_patched.py /app/app/api/endpoints/tmdb.py

# 搜索端点（adult search_type 支持）
COPY patches/moviepilot-core/search_patched.py /app/app/api/endpoints/search.py

# 搜索链路（search_type 参数传递）
COPY patches/moviepilot-core/chain_search.py /app/app/chain/search.py
COPY patches/moviepilot-core/chain_init.py /app/app/chain/__init__.py

# 索引器初始化（成人搜索支持）
COPY patches/moviepilot-core/indexer_init.py /app/app/modules/indexer/__init__.py

# 爬虫模块（mTeam adult mode + NexusPHP allsec）
COPY patches/moviepilot-core/spider_init.py /app/app/modules/indexer/spider/__init__.py
COPY patches/moviepilot-core/mtorrent.py /app/app/modules/indexer/spider/mtorrent.py

# 清除 pyc 缓存，确保使用新文件
RUN find /app/app -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ============ 前端补丁 ============

# 剧照注入脚本 + 注入辅助工具
COPY patches/moviepilot-core/stills-inject.js /config/stills-inject.js
COPY patches/moviepilot-core/inject_stills.py /config/inject_stills.py

# nginx 缓存策略（禁用激进缓存）
COPY patches/moviepilot-core/nginx_common_patched.conf /config/nginx_common_patched.conf

# ============ 入口脚本 ============

# 自定义 entrypoint（FastAPI 降级 + 插件安装 + 前端注入）
COPY patches/moviepilot-core/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
