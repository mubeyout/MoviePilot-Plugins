#!/bin/bash
# V3 自有插件部署器（替代 V2 entrypoint _install_plugin 段）
# 由 MP_V3_PRESTART 包装：在 backend.sh 前把 /config/plugins/v2/* 拷入 /app/app/plugins/
set -u
SRC=/config/plugins/v2
DST=/app/app/plugins

for p in metatubesource bytemusediscover javbusextend anistrmpro mubeyclashrp; do
    if [ -d "$SRC/$p" ]; then
        rm -rf "$DST/$p"
        cp -a "$SRC/$p" "$DST/$p"
        rm -rf "$DST/$p/__pycache__"
        echo "[v3-plugins] deployed $p"
    fi
done

# stills 前端注入（镜像 index.html 每次启动为原始文件）
if [ -f /config/inject_stills.py ] && [ -f /config/stills-inject.js ]; then
    /opt/venv/bin/python3 /config/inject_stills.py && echo "[v3-plugins] stills injected"
fi

exec /bin/bash "$@"
