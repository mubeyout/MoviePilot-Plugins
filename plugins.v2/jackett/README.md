# Jackett 插件

通过 Jackett 聚合多个种子站点进行搜索，支持统一的 API 接口和索引器管理。

## 功能特性

- ✅ 聚合搜索多个种子站点
- ✅ RESTful API 接口
- ✅ 索引器管理
- ✅ 连接测试
- ✅ 分类搜索

## 安装

1. 确保已安装并运行 Jackett 服务
2. 将插件复制到 MoviePilot 插件目录
3. 重启 MoviePilot
4. 在插件设置中配置 Jackett 地址和 API Key

## 配置说明

### Jackett 服务

```bash
# Docker 方式运行
docker run -d \
  --name jackett \
  -p 9117:9117 \
  -v ./jackett-config:/config \
  linuxserver/jackett
```

### 插件配置

- **Jackett 地址**: `http://localhost:9117`（或你的实际地址）
- **API Key**: 在 Jackett 设置中获取

## API 使用

### 搜索种子

```bash
GET /api/plugin/jackett/search?query={keyword}&indexer={id}
```

### 获取索引器列表

```bash
GET /api/plugin/jackett/indexers
```

### 测试连接

```bash
GET /api/plugin/jackett/test
```

## 使用示例

详细使用说明请查看：`[[00.InBox/Jackett插件使用指南.md]]`

## 技术架构

- **API 封装**: `jackett_api.py`
- **插件主类**: `__init__.py`
- **依赖**: `requests>=2.31.0`

## 注意事项

1. Jackett 服务必须先运行并配置好索引器
2. API Key 需要在 Jackett 设置中生成
3. 建议配置的索引器数量不超过 50 个

## 故障排查

如遇问题，请查看：
1. Jackett 服务是否正常运行
2. API Key 是否正确
3. 网络连接是否正常
4. MoviePilot 日志中的错误信息

## 许可证

MIT License

## 作者

Claudian (基于 MoviePilot 插件模板开发)
