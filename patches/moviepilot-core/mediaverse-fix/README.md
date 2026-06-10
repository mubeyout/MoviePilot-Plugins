# MediaVerse 插件修复

## 问题
MoviePilot v2.10.2+ 的 `_PluginBase` 移除了 `self.register_route()` 方法，
改用抽象方法 `get_api()` 返回路由列表。

MediaVerse v1.0.0 仍然在 `__init__` 里调用 `self.register_route()`，
导致加载失败（`'MediaVerse' object has no attribute 'register_route'`），
表现为 `state:false`、`探索`页看不到。

## 修复
删除 `__init__` 中的 8 个 `self.register_route(...)` 调用，保留 `super().__init__()` 即可。
新插件的路由注册通过 `get_api()` 自动完成（MediaVerse 已有完整实现）。

## 部署
镜像内 `/app/app/plugins/mediaverse/__init__.py` 应被替换为此目录的文件。
在 `Dockerfile` 中加：
```dockerfile
COPY patches/moviepilot-core/mediaverse-fix/__init__.py /app/app/plugins/mediaverse/__init__.py
```
