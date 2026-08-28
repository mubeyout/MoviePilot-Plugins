# nginx 配置说明（2026-08-28）

## 文件说明
- `nginx_common_patched.conf`：当前生效版（基于旧上游结构 + 插件联邦修复）
- `nginx_common_patched.next.conf`：**未来重建镜像用**（基于上游 v2 新版 nginx.common.conf）

## 背景
旧上游 `location ~* /assets/` 正则会截胡 `/api/v1/plugin/file/<id>/dist/assets/*.js`，
导致所有 vue 渲染插件报「组件加载错误」。上游已在 v2 分支修复（assets 改普通前缀 +
js/css 正则加 `(?!api/v1)` 负向前瞻）。

## 重建 latest-patched 时的注意事项
1. 基础镜像若更新到新版上游，建议换用 `nginx_common_patched.next.conf`
   （重命名为 nginx_common_patched.conf 或改 Dockerfile COPY 行）
2. ⚠️ 其他 core patches（media/tmdb/search/chain 等整文件覆盖式补丁）
   基于旧版上游代码，基础镜像更新后需要逐一 diff rebase，否则会把上游新修复覆盖回旧版
