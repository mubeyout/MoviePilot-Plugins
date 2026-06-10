FROM jxxghp/moviepilot:latest


# ============ 后端 Python 补丁 ============

# ByteMuse 媒体详情 API（stills, recommendations, similar）
COPY patches/moviepilot-core/media_patched.py /app/app/api/endpoints/media.py

# TMDB 端点（metatube_search 前缀路由）
COPY patches/moviepilot-core/tmdb_patched.py /app/app/api/endpoints/tmdb.py

# 搜索端点（adult search_type）
COPY patches/moviepilot-core/search_patched.py /app/app/api/endpoints/search.py

# 搜索链路 + 索引器 + 爬虫
COPY patches/moviepilot-core/chain_search.py /app/app/chain/search.py
COPY patches/moviepilot-core/chain_init.py /app/app/chain/__init__.py
COPY patches/moviepilot-core/indexer_init.py /app/app/modules/indexer/__init__.py
COPY patches/moviepilot-core/spider_init.py /app/app/modules/indexer/spider/__init__.py
COPY patches/moviepilot-core/mtorrent.py /app/app/modules/indexer/spider/mtorrent.py

# MediaVerse 插件：移除过时的 self.register_route() 调用
COPY patches/moviepilot-core/mediaverse-fix/__init__.py /app/app/plugins/mediaverse/__init__.py

# 清除 pyc 缓存
RUN find /app/app -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ============ 前端 + 运行时补丁 ============

# 剧照注入脚本 + MediaVerse 探索页 + 注入工具
COPY patches/moviepilot-core/stills-inject.js /config/stills-inject.js
COPY patches/moviepilot-core/mediaverse-explore.js /config/mediaverse-explore.js
COPY patches/moviepilot-core/inject_stills.py /config/inject_stills.py
COPY patches/moviepilot-core/setup_mediaverse.py /config/setup_mediaverse.py

# nginx 缓存策略
COPY patches/moviepilot-core/nginx_common_patched.conf /config/nginx_common_patched.conf

# 入口脚本（插件安装 + 前端注入）
COPY patches/moviepilot-core/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
