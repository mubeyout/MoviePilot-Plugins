# MoviePilot-Plugins

MoviePilot 插件集合，提供多种实用功能扩展。

## 插件列表

### 🎬 Alist2StrmPro

**版本**: 2.0.0 | **作者**: MUBEY | **标签**: 整理

从 Alist 生成音视频 strm 文件，支持视频、音频、其他文件（字幕、图片、NFO等）分类处理。

**核心功能**:
- 支持视频、音频、其他文件（字幕、图片、NFO）三种类型独立处理
- 视频/音频文件生成 .strm 文件
- 字幕文件自动下载到本地
- 其他文件（图片、NFO等）自动下载
- 支持广度优先/深度优先遍历模式
- 支持多种过滤模式（集合/磁盘/布隆过滤）
- 支持失效文件自动清理
- 可自定义各类型文件的后缀和保存目录

**默认后缀**:
- 视频: `.mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.ts,.rmvb,.iso`
- 音频: `.mp3,.flac,.wav,.aac,.ogg,.m4a,.wma,.ape,.opus,.alac,.dsd,.dsf`
- 其他: `.nfo,.jpg,.png,.jpeg,.gif,.bmp,.srt,.ass,.ssa,.sub,.idx,.txt`

---

### 🎌 ANiStrm

**版本**: 2.7.0 | **作者**: MUBEY | **标签**: 整理

自动获取当季所有番剧并生成 strm 文件，免去下载，轻松拥有一个番剧媒体库。

**核心功能**:
- 三种同步模式：只更最新（增量）、指定季度、全部季度
- 支持多种视频格式（mp4/mkv/avi/mov/wmv/flv/webm/m4v/ts/rmvb）
- 两种存储模式：
  - 扁平模式（默认）：保持原有文件结构
  - 季度文件夹模式（推荐）：按 Season 文件夹组织，符合媒体库标准
- 智能季度识别和集数提取
- 支持手动维护多季度番剧映射表
- 完成指定/全部季度同步后自动切换到增量模式

**季度文件夹模式优势**:
- Emby/Plex/Jellyfin 完美识别
- 自动季度识别和归档
- 自动集数提取并重命名为标准格式（番剧名 S01E01.mp4）

---

### 🔍 Metatube源

**版本**: 2.0.0 | **作者**: MUBEY | **标签**: 识别

通过 Metatube API、ThePornDB API、Byte-Muse API 识别番号媒体信息，支持日系/欧美系/中文系自动分类。

**核心功能**:
- 双重劫持机制（ChainBase + 模块系统）
- 自动分类识别：日系、欧美系、中文系、其他
- 内置 42 个排除关键字
- 支持 JSON 格式关键字配置文件（keywords.json）
- 关键字优先级：UI 自定义 > 内置核心 > keywords.json 文件
- 三级识别优先级：Metatube(核心) → ThePornDB(补充) → ByteMuse(备用)
- 新增 ThePornDB JAV 两步法 API 支持
- 支持失败自动下载控制

**分类识别流程**:
1. 获取标题（org_string → cn_name → en_name → name）
2. 关键词分类检测
3. 根据分类提取番号
4. 选择识别方式（欧美系优先使用 ThePornDB，其他使用 Metatube）
5. 固定分类（成人/日系、成人/欧美系、成人/中文系、成人/其他）

---

### 🗺️ 番号探索服务聚合

**版本**: 2.9.6 | **作者**: Mubey | **标签**: 探索,识别

统一管理和配置番号媒体探索数据源插件，整合 Byte-Muse（本地Docker）、ThePornDB（在线API）、MetaTube 三大数据源。

**核心功能**:
- 整合三大番号数据源（Byte-Muse、ThePornDB、MetaTube）
- 支持演员、上新、推荐、榜单、厂牌、搜索等探索服务
- 支持探索功能扩展
- 统一的数据源配置管理

---

### 🔧 Clash Rule Provider

**版本**: 2.1.2 | **作者**: wumode,mubey | **标签**: 代理,订阅

随时为 Clash 添加一些额外的规则。

**核心功能**:
- 规则管理和订阅处理
- 配置验证和错误处理
- 数据升级和性能优化

---

### 🧹 智能文件夹清理

**版本**: 1.0 | **作者**: mubey | **标签**: 工具,清理

遍历指定目录，删除符合自定义'空文件夹'定义的目录（无有效文件的目录）。

**核心功能**:
- 两种判定模式：按类型+大小判定（默认）、仅按大小判定
- 支持多路径监控、递归遍历
- 自定义文件类型和大小阈值（支持B/KB/MB/GB单位）
- **智能排除格式**：自动排除正在下载、临时文件等（内置29种格式，始终启用）
- 从最深层开始安全删除
- 自定义运行周期（支持 cron 表达式）
- 立即运行功能（手动触发清理）
- 完成后发送通知

**默认配置**:
- **视频** (27种): `.mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v,.ts,.mts,.m2ts,.rmvb,.rm,.3gp,.3g2,.asf,.divx,.xvid,.vob,.qt,.yuv,.f4v,.ogv,.dv,.mxm,.mpeg,.mpg,.mpe` (最小 100MB)
- **图片** (30种): `.jpg,.jpeg,.png,.gif,.bmp,.webp,.tiff,.tif,.svg,.ico,.psd,.raw,.cr2,.nef,.arw,.dng,.heic,.heif,.avif,.jxl,.jp2,.j2k,.exr,.pnm,.pbm,.pgm,.ppm,.sr` (最小 1MB)
- **音频** (32种): `.mp3,.flac,.wav,.aac,.ogg,.m4a,.wma,.ape,.opus,.alac,.ac3,.dts,.dtshd,.truehd,.aiff,.aif,.aifc,.amr,.au,.ra,.m4p,.m4b,.m4r,.mp2,.mp1,.mpc,.oma,.tak,.tta,.wv,.gsm,.caf` (最小 1MB)
- **其他** (12种): `.txt,.srt,.ass,.ssa,.sub,.idx,.vtt,.smi,.sup,.rt,.xml` (最小 0MB)
- **排除格式** (29种): `.part,.!ut,.ut!,.torrent,.aria2,.qB,.bc,.oput,.download,.temp,.tmp,.bak,.swp,.DS_Store,.Thumbs.db,.desktop,.ini,.lnk,.sync,.conf,.lock,.log,.cache` (始终启用，自动排除)
- 运行周期: 每天凌晨 2 点（`0 2 * * *`）

---

## 安装说明

1. 将插件目录放置在 MoviePilot 的 `plugins/v2/` 目录下
2. 重启 MoviePilot
3. 在插件市场中安装并配置插件

## 配置说明

每个插件都有独立的配置界面，可在 MoviePilot 插件市场点击"设置"按钮进行配置。

## 技术支持

- 插件开发基于 MoviePilot V2 插件系统
- 支持响应式配置界面
- 支持定时任务和 API 接口
- 完善的日志输出和错误处理

## 更新日志

查看各插件的 `package.v2.json` 文件中的 `history` 字段获取详细版本历史。
