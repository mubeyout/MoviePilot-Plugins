import os
import time
from datetime import datetime, timedelta
from urllib.parse import quote

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.utils.http import RequestUtils
from app.core.config import settings
from app.plugins import _PluginBase
from typing import Any, List, Dict, Tuple, Optional
from app.log import logger
import xml.dom.minidom
from app.utils.dom import DomUtils


def retry(ExceptionToCheck: Any,
          tries: int = 3, delay: int = 3, backoff: int = 1, logger: Any = None, ret: Any = None):
    """
    :param ExceptionToCheck: 需要捕获的异常
    :param tries: 重试次数
    :param delay: 延迟时间
    :param backoff: 延迟倍数
    :param logger: 日志对象
    :param ret: 默认返回
    """

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 0:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = f"未获取到文件信息，{mdelay}秒后重试 ..."
                    if logger:
                        logger.warn(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if logger:
                logger.warn('请确保当前季度番剧文件夹存在或检查网络问题')
            return ret

        return f_retry

    return deco_retry


class ANiStrm(_PluginBase):
    # 插件名称
    plugin_name = "ANiStrm"
    # 插件描述
    plugin_desc = "自动获取当季所有番剧，免去下载，轻松拥有一个番剧媒体库"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/mubeyout/MoviePilot-Plugins/main/icons/anistrm.png"
    # 插件版本
    plugin_version = "2.7.0"
    # 插件作者
    plugin_author = "MUBEY"
    # 作者主页
    author_url = "https://github.com/mubeyout"
    # 插件配置项ID前缀
    plugin_config_prefix = "anistrm_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enabled = False
    # 任务执行间隔
    _cron = None
    _onlyonce = False
    _storageplace = None
    # 同步模式: latest(只更最新) / selected(指定季度) / all(全部季度)
    _sync_mode = "latest"
    # 已选择的季度列表
    _selected_seasons: List[str] = []
    # 缓存的可用季度列表
    _available_seasons: List[str] = []
    # 存储模式: flat(扁平模式) / season_folder(季度文件夹模式)
    _storage_mode = "flat"

    # ANi API 请求头（使用 JSON 格式）
    _ani_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://openani.an-i.workers.dev',
        'Referer': 'https://openani.an-i.workers.dev/',
    }

    # 定时器
    _scheduler: Optional[BackgroundScheduler] = None

    def init_plugin(self, config: dict = None):
        # 停止现有任务
        self.stop_service()

        if config:
            self._enabled = config.get("enabled")
            self._cron = config.get("cron")
            self._onlyonce = config.get("onlyonce")
            self._sync_mode = config.get("sync_mode", "latest")
            self._selected_seasons = config.get("selected_seasons") or []
            self._storageplace = config.get("storageplace")
            self._storage_mode = config.get("storage_mode", "flat")
            # 兼容旧配置：如果存在 fulladd=True，转换为 sync_mode="all"
            if config.get("fulladd"):
                self._sync_mode = "all"
            # 加载模块
        if self._enabled or self._onlyonce:
            # 定时服务
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)

            if self._enabled and self._cron:
                try:
                    self._scheduler.add_job(func=self.__task,
                                            trigger=CronTrigger.from_crontab(self._cron),
                                            name="ANiStrm文件创建")
                    logger.info(f'ANi-Strm定时任务创建成功：{self._cron}')
                except Exception as err:
                    logger.error(f"定时任务配置错误：{str(err)}")

            if self._onlyonce:
                logger.info(f"ANi-Strm服务启动，立即运行一次，模式：{self._sync_mode}")
                self._scheduler.add_job(func=self.__task, trigger='date',
                                        run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                                        name="ANiStrm文件创建")
                # 关闭一次性开关
                self._onlyonce = False
            self.__update_config()

            # 启动任务
            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()

    def __get_ani_season(self, idx_month: int = None) -> str:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = idx_month if idx_month else current_date.month
        for month in range(current_month, 0, -1):
            if month in [10, 7, 4, 1]:
                self._date = f'{current_year}-{month}'
                return f'{current_year}-{month}'

    @retry(Exception, tries=3, logger=logger, ret=[])
    def get_current_season_list(self) -> List:
        url = f'https://openani.an-i.workers.dev/{self.__get_ani_season()}/'

        rep = RequestUtils(ua=settings.USER_AGENT if settings.USER_AGENT else None,
                           proxies=settings.PROXY if settings.PROXY else None,
                           headers=self._ani_headers).post(url=url, json={'password': ''})
        logger.debug(rep.text)
        files_json = rep.json()['files']
        return [file['name'] for file in files_json]

    @retry(Exception, tries=3, logger=logger, ret=[])
    def get_season_list(self, season: str) -> Tuple[List, str]:
        """
        获取指定季度的番剧列表（仅返回番剧文件夹名）
        :param season: 季度字符串，如 "2024-1"
        :return: (番剧文件夹列表, 季度)
        """
        url = f'https://openani.an-i.workers.dev/{season}/'
        rep = RequestUtils(ua=settings.USER_AGENT if settings.USER_AGENT else None,
                           proxies=settings.PROXY if settings.PROXY else None,
                           headers=self._ani_headers).post(url=url, json={'password': ''})
        logger.debug(rep.text)
        files_json = rep.json()['files']
        # 只返回文件夹类型（番剧名称）
        anime_folders = [file['name'] for file in files_json if 'folder' in file.get('mimeType', '')]
        return anime_folders, season

    @retry(Exception, tries=3, logger=logger, ret=[])
    def get_anime_episodes(self, season: str, anime_name: str) -> List[str]:
        """
        获取指定番剧的所有视频文件
        :param season: 季度字符串，如 "2024-1"
        :param anime_name: 番剧文件夹名称
        :return: 视频文件名列表（包含扩展名）
        """
        from urllib.parse import quote
        # URL编码番剧名称
        encoded_anime = quote(anime_name, safe='')
        url = f'https://openani.an-i.workers.dev/{season}/{encoded_anime}/'
        rep = RequestUtils(ua=settings.USER_AGENT if settings.USER_AGENT else None,
                           proxies=settings.PROXY if settings.PROXY else None,
                           headers=self._ani_headers).post(url=url, json={'password': ''})
        logger.debug(f"获取番剧 {anime_name} 的视频列表: {url}")
        files_json = rep.json()['files']

        # 常见视频格式扩展名
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.rmvb']

        # 过滤出视频文件（排除 .ssa 等字幕文件）
        video_files = []
        for file in files_json:
            name = file.get('name', '')
            # 检查是否是视频文件
            is_video = False
            for ext in video_extensions:
                if name.lower().endswith(ext):
                    is_video = True
                    break

            if is_video:
                # 返回完整的文件名（包含扩展名）
                video_files.append(name)

        logger.info(f'番剧 {anime_name} 共 {len(video_files)} 个视频文件')
        return video_files

    def __infer_season_number(self, season_str: str, anime_name: str) -> int:
        """
        推断番剧的季度号
        :param season_str: 季度字符串，如 "2024-1"
        :param anime_name: 番剧名称
        :return: 季度号 (1, 2, 3...)
        """
        # 常见的多季度番剧映射表（手动维护）
        # 格式: "番剧关键词": {起始季度: 季度号}
        multi_season_anime = {
            "Dr.STONE": {"2019-7": 1, "2020-1": 2},
            "转生王女与天才千金的魔法革命": {"2023-4": 1, "2025-1": 2},
            # 可以根据需要添加更多
        }

        # 检查是否在映射表中
        for keyword, season_map in multi_season_anime.items():
            if keyword in anime_name:
                if season_str in season_map:
                    return season_map[season_str]

        # 默认逻辑：假设第一个出现的季度是第1季
        # 后续季度按出现顺序递增
        if not hasattr(self, '_anime_season_cache'):
            self._anime_season_cache = {}

        # 使用番剧名和季度作为唯一标识
        cache_key = f"{anime_name}_{season_str}"

        if cache_key in self._anime_season_cache:
            return self._anime_season_cache[cache_key]

        # 简单的逻辑：按季度顺序推断
        # 提取年份和月份
        try:
            year, month = map(int, season_str.split('-'))

            # 查找该番剧是否已有记录
        existing_seasons = [k for k in self._anime_season_cache.keys() if k.split('_')[0] == anime_name]

        if not existing_seasons:
            # 第一次出现，默认为第1季
            season_num = 1
        else:
            # 按季度排序，取最大的季度号+1
            season_nums = [self._anime_season_cache[k] for k in existing_seasons]
            season_num = max(season_nums) + 1

        self._anime_season_cache[cache_key] = season_num
        return season_num

        except Exception:
            logger.debug(f"无法解析季度 {season_str}，默认为第1季")
            return 1

    def __extract_episode_number(self, filename: str) -> int:
        """
        从文件名中提取集数
        :param filename: 文件名，如 "[ANi]Dr.STONE 新石紀[01][1080P]..."
        :return: 集数
        """
        import re

        # 尝试多种模式匹配集数
        patterns = [
            r'\[(\d+)\]',           # [01] 格式
            r'EP?(\d+)',            # EP01 或 E01 格式
            r'第(\d+)集',            # 第01集 格式
            r' - (\d+)',            # - 01 格式
            r'S\d+E(\d+)',          # S01E01 格式
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        # 无法提取，返回0
        logger.debug(f"无法从文件名提取集数: {filename}")
        return 0

    def __generate_standard_filename(self, anime_name: str, episode_num: int, season_num: int, original_filename: str) -> str:
        """
        生成标准媒体库文件名
        :param anime_name: 番剧名称
        :param episode_num: 集数
        :param season_num: 季度号
        :param original_filename: 原始文件名（用于提取扩展名）
        :return: 标准文件名，如 "番剧名 S01E01.mp4"
        """
        # 获取扩展名
        import os
        _, ext = os.path.splitext(original_filename)

        # 标准格式：番剧名 S01E01.mp4
        # 集数和季度号补零
        season_str = f"{season_num:02d}"
        episode_str = f"{episode_num:02d}"

        standard_name = f"{anime_name} S{season_str}E{episode_str}{ext}"

        return standard_name


    @retry(Exception, tries=3, logger=logger, ret=[])
    def get_available_seasons_from_api(self) -> List[str]:
        """
        从 openani.an-i.workers.dev 获取所有可用的季度列表
        """
        url = 'https://openani.an-i.workers.dev/'
        rep = RequestUtils(ua=settings.USER_AGENT if settings.USER_AGENT else None,
                           proxies=settings.PROXY if settings.PROXY else None,
                           headers=self._ani_headers).post(url=url, json={'password': ''})
        logger.debug(rep.text)
        files_json = rep.json().get('files', [])

        # 过滤出目录（季度目录 + ANi 目录）
        seasons = []
        other_folders = []

        for file in files_json:
            name = file.get('name', '')
            mime_type = file.get('mimeType', '')

            # 只处理文件夹类型
            if 'folder' not in mime_type:
                continue

            # 季度目录格式: YYYY-M 其中 M 为 1, 4, 7, 10
            if name and '-' in name:
                try:
                    year, month = name.split('-')
                    if year.isdigit() and month.isdigit() and int(month) in [1, 4, 7, 10]:
                        seasons.append(name)
                        continue
                except ValueError:
                    pass

            # 其他文件夹（如 ANi）
            if name and name not in ['sw.js']:
                other_folders.append(name)

        # 季度按时间倒序排列（最新的在前）
        seasons.sort(key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1])), reverse=True)

        # 合并：季度目录 + 其他目录
        all_folders = seasons + other_folders
        self._available_seasons = all_folders
        logger.info(f'从API获取到 {len(all_folders)} 个可用目录: {all_folders}')
        return all_folders

    def get_available_seasons(self) -> List[str]:
        """
        获取所有可用的季度列表
        优先从API获取，失败则生成默认列表（从2019年到当前年份）
        """
        # 尝试从API获取
        try:
            seasons = self.get_available_seasons_from_api()
            if seasons:
                return seasons
        except Exception as e:
            logger.debug(f"从API获取季度列表失败: {str(e)}，使用默认生成")

        # 回退：生成默认季度列表
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        seasons = []
        # 从2019年开始到当前年份
        for year in range(2019, current_year + 1):
            for month in [1, 4, 7, 10]:
                # 跳过未来的季度
                if year == current_year and month > current_month:
                    continue
                seasons.append(f"{year}-{month}")

        # 按时间倒序排列（最新的在前）
        seasons.sort(key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1])), reverse=True)
        self._available_seasons = seasons
        logger.info(f'生成 {len(seasons)} 个可用季度')
        return seasons

    @retry(Exception, tries=3, logger=logger, ret=[])
    def get_latest_list(self) -> List:
        addr = 'https://api.ani.rip/ani-download.xml'
        ret = RequestUtils(ua=settings.USER_AGENT if settings.USER_AGENT else None,
                           proxies=settings.PROXY if settings.PROXY else None).get_res(addr)
        ret_xml = ret.text
        ret_array = []
        # 解析XML
        dom_tree = xml.dom.minidom.parseString(ret_xml)
        rootNode = dom_tree.documentElement
        items = rootNode.getElementsByTagName("item")
        for item in items:
            rss_info = {}
            # 标题
            title = DomUtils.tag_value(item, "title", default="")
            # 链接
            link = DomUtils.tag_value(item, "link", default="")
            rss_info['title'] = title
            rss_info['link'] = link.replace("resources.ani.rip", "openani.an-i.workers.dev")
            ret_array.append(rss_info)
        return ret_array

    def __touch_strm_file(self, file_name, file_url: str = None, season_num: int = None) -> bool:
        """
        创建strm文件
        :param file_name: 文件名，可以是 "视频名.扩展名" 或 "番剧名/视频名.扩展名" 格式
        :param file_url: 可选的播放链接
        :param season_num: 季度号（仅在 season_folder 模式下使用）
        :return: 是否成功创建
        """
        # 支持的视频格式
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.rmvb']

        # 解析文件名（支持子文件夹格式）
        if '/' in file_name:
            # 格式: 番剧名/视频名.扩展名
            anime_name, video_filename = file_name.split('/', 1)

            # 根据存储模式生成不同的文件路径
            if self._storage_mode == "season_folder" and season_num is not None:
                # 季度文件夹模式：番剧名/Season 01/番剧名 S01E01.strm
                season_folder = f"Season {season_num:02d}"

                # 提取集数并生成标准文件名
                episode_num = self.__extract_episode_number(video_filename)
                standard_filename = self.__generate_standard_filename(anime_name, episode_num, season_num, video_filename)

                file_path = f'{self._storageplace}/{anime_name}/{season_folder}/{standard_filename}.strm'
                video_name = video_filename  # 用于生成URL，保持原始文件名
                folder_name = anime_name
            else:
                # 扁平模式（默认）
                file_path = f'{self._storageplace}/{anime_name}/{video_filename}.strm'
                video_name = video_filename  # 保留扩展名
                folder_name = anime_name
        else:
            # 格式: 视频名.扩展名（根目录，用于latest模式）
            video_filename = file_name
            file_path = f'{self._storageplace}/{video_filename}.strm'
            video_name = video_filename  # 保留扩展名
            folder_name = None

        # 检查文件是否已存在
        if os.path.exists(file_path):
            logger.debug(f'{file_path} 文件已存在')
            return False

        # 生成播放URL
        if not file_url:
            # 季度API生成的URL，使用新格式
            encoded_video = quote(video_name, safe='')
            if folder_name:
                # 包含番剧文件夹: /季度/番剧名/视频.扩展名
                encoded_folder = quote(folder_name, safe='')
                src_url = f'https://openani.an-i.workers.dev/{self._date}/{encoded_folder}/{encoded_video}?d=true'
            else:
                # 根目录格式: /季度/视频.扩展名（用于latest模式）
                src_url = f'https://openani.an-i.workers.dev/{self._date}/{encoded_video}?d=true'
        else:
            # 检查API获取的URL格式是否符合要求
            if self._is_url_format_valid(file_url):
                # 格式符合要求，直接使用
                src_url = file_url
            else:
                # 格式不符合要求，进行转换
                src_url = self._convert_url_format(file_url)

        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.debug(f'创建目录: {dir_path}')
            except Exception as e:
                logger.error(f'创建目录失败：{str(e)}')
                return False

        # 创建strm文件
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(src_url)
                logger.debug(f'创建 {file_path} 文件成功')
                return True
        except Exception as e:
            logger.error('创建strm源文件失败：' + str(e))
            return False

    def _is_url_format_valid(self, url: str) -> bool:
        """检查URL格式是否符合要求（.mp4?d=true）"""
        return url.endswith('.mp4?d=true')

    def _convert_url_format(self, url: str) -> str:
        """将URL转换为符合要求的格式"""
        if '?d=mp4' in url:
            # 将 ?d=mp4 替换为 .mp4?d=true
            return url.replace('?d=mp4', '.mp4?d=true')
        elif url.endswith('.mp4'):
            # 如果已经以.mp4结尾，添加?d=true
            return f'{url}?d=true'
        else:
            # 其他情况，添加.mp4?d=true
            return f'{url}.mp4?d=true'

    def __task(self):
        """
        执行同步任务，根据 sync_mode 执行不同逻辑：
        - latest: 只更最新（从RSS获取增量更新）
        - selected: 指定季度（同步选中的季度）
        - all: 全部季度（同步所有可用季度）
        """
        cnt = 0
        need_switch_to_latest = False  # 标记是否需要切换到"只更最新"模式

        if self._sync_mode == "latest":
            # 增量模式：从 RSS 获取最新更新
            logger.info("执行模式：只更最新（增量更新）")
            rss_info_list = self.get_latest_list()
            logger.info(f'本次处理 {len(rss_info_list)} 个文件')
            for rss_info in rss_info_list:
                if self.__touch_strm_file(file_name=rss_info['title'], file_url=rss_info['link']):
                    cnt += 1

        elif self._sync_mode == "selected":
            # 指定季度模式：同步用户选择的季度
            logger.info(f"执行模式：指定季度，选中季度: {self._selected_seasons}")
            if not self._selected_seasons:
                logger.warn("未选择任何季度，跳过同步")
                return
            for season in self._selected_seasons:
                try:
                    # 步骤1: 获取该季度的番剧文件夹列表
                    anime_list, season_date = self.get_season_list(season)
                    logger.info(f'季度 {season} 共 {len(anime_list)} 部番剧')
                    self._date = season_date  # 设置当前处理的季度

                    # 步骤2: 遍历每部番剧，获取其所有视频文件
                    for anime_name in anime_list:
                        try:
                            # 推断季度号（用于 season_folder 模式）
                            season_num = self.__infer_season_number(season, anime_name) if self._storage_mode == "season_folder" else None
                            if season_num:
                                logger.info(f'  番剧 {anime_name} 识别为第 {season_num} 季')

                            episode_list = self.get_anime_episodes(season, anime_name)
                            # 步骤3: 为每个视频文件创建strm文件
                            for episode_name in episode_list:
                                # 文件名格式: 番剧名称/视频名称
                                file_name = f"{anime_name}/{episode_name}"
                                if self.__touch_strm_file(file_name=file_name, season_num=season_num):
                                    cnt += 1
                        except Exception as e:
                            logger.error(f'处理番剧 {anime_name} 失败: {str(e)}')
                except Exception as e:
                    logger.error(f'处理季度 {season} 失败: {str(e)}')
            # 指定季度完成后，自动切换到"只更最新"模式
            need_switch_to_latest = True

        elif self._sync_mode == "all":
            # 全部季度模式：获取所有可用季度并同步
            logger.info("执行模式：全部季度")
            seasons = self.get_available_seasons()
            if not seasons:
                logger.warn("未获取到可用季度列表")
                return
            logger.info(f'共发现 {len(seasons)} 个季度待同步')
            for season in seasons:
                try:
                    # 步骤1: 获取该季度的番剧文件夹列表
                    anime_list, season_date = self.get_season_list(season)
                    logger.info(f'季度 {season} 共 {len(anime_list)} 部番剧')
                    self._date = season_date  # 设置当前处理的季度

                    # 步骤2: 遍历每部番剧，获取其所有视频文件
                    for anime_name in anime_list:
                        try:
                            # 推断季度号（用于 season_folder 模式）
                            season_num = self.__infer_season_number(season, anime_name) if self._storage_mode == "season_folder" else None
                            if season_num:
                                logger.info(f'  番剧 {anime_name} 识别为第 {season_num} 季')

                            episode_list = self.get_anime_episodes(season, anime_name)
                            # 步骤3: 为每个视频文件创建strm文件
                            for episode_name in episode_list:
                                # 文件名格式: 番剧名称/视频名称
                                file_name = f"{anime_name}/{episode_name}"
                                if self.__touch_strm_file(file_name=file_name, season_num=season_num):
                                    cnt += 1
                        except Exception as e:
                            logger.error(f'处理番剧 {anime_name} 失败: {str(e)}')
                except Exception as e:
                    logger.error(f'处理季度 {season} 失败: {str(e)}')
            # 全部季度完成后，自动切换到"只更最新"模式
            need_switch_to_latest = True

        else:
            # 默认使用增量模式
            logger.info("执行模式：默认增量更新")
            rss_info_list = self.get_latest_list()
            logger.info(f'本次处理 {len(rss_info_list)} 个文件')
            for rss_info in rss_info_list:
                if self.__touch_strm_file(file_name=rss_info['title'], file_url=rss_info['link']):
                    cnt += 1

        logger.info(f'新创建了 {cnt} 个strm文件')

        # 任务完成后，如果是"指定季度"或"全部季度"模式，自动切换到"只更最新"
        if need_switch_to_latest:
            logger.info("任务完成，自动切换到「只更最新」模式")
            self._sync_mode = "latest"
            self.__update_config()

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        # 懒加载：只在非「只更最新」模式时才请求季度列表（避免打开插件慢）
        season_options = []
        if self._sync_mode != "latest":
            try:
                seasons = self.get_available_seasons()
                season_options = [{"title": s, "value": s} for s in seasons]
            except Exception as e:
                logger.debug(f"获取季度列表失败: {str(e)}")
                # 生成默认季度选项（最近3年的季度）
                current_year = datetime.now().year
                for year in range(current_year, current_year - 3, -1):
                    for month in [10, 7, 4, 1]:
                        season_options.append({"title": f"{year}-{month}", "value": f"{year}-{month}"})
        else:
            # 「只更最新」模式：使用缓存或生成简化列表（不请求API）
            if self._available_seasons:
                season_options = [{"title": s, "value": s} for s in self._available_seasons]
            else:
                # 生成默认季度选项（最近3年的季度）
                current_year = datetime.now().year
                for year in range(current_year, current_year - 3, -1):
                    for month in [10, 7, 4, 1]:
                        season_options.append({"title": f"{year}-{month}", "value": f"{year}-{month}"})

        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'sync_mode',
                                            'label': '同步模式',
                                            'items': [
                                                {'title': '只更最新', 'value': 'latest'},
                                                {'title': '指定季度', 'value': 'selected'},
                                                {'title': '全部季度', 'value': 'all'},
                                            ]
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'storage_mode',
                                            'label': '存储模式',
                                            'items': [
                                                {'title': '扁平模式（默认）', 'value': 'flat'},
                                                {'title': '季度文件夹模式（标准媒体库）', 'value': 'season_folder'},
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cron',
                                            'label': '执行周期',
                                            'placeholder': '0 0 ? ? ?'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'storageplace',
                                            'label': 'Strm存储地址',
                                            'placeholder': '/downloads/strm'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'selected_seasons',
                                            'label': '选择季度（指定季度模式生效）',
                                            'multiple': True,
                                            'chips': True,
                                            'clearable': True,
                                            'items': season_options
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '同步模式说明：\n'
                                                    '• 只更最新：从RSS获取最新番剧更新（增量模式，推荐日常使用）\n'
                                                    '• 指定季度：同步选中的历史季度番剧\n'
                                                    '• 全部季度：同步所有可用季度的番剧（首次使用推荐）',
                                            'style': 'white-space: pre-line;'
                                        }
                                    },
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '自动从open ANi抓取下载直链生成strm文件，免去人工订阅下载\n'
                                                    '配合目录监控使用，strm文件创建在/downloads/strm\n'
                                                    '通过目录监控转移到link媒体库文件夹 如/downloads/link/strm  mp会完成刮削',
                                            'style': 'white-space: pre-line;'
                                        }
                                    },
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'warning',
                                            'variant': 'tonal',
                                            'text': 'emby容器需要设置代理，docker的环境变量必须要有http_proxy代理变量，大小写敏感，具体见readme.\n'
                                                    'https://github.com/mubeyout/MoviePilot-Plugins',
                                            'style': 'white-space: pre-line;'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "sync_mode": "latest",
            "selected_seasons": [],
            "storageplace": '/downloads/strm',
            "storage_mode": "flat",
            "cron": "*/20 22,23,0,1 * * *",
        }

    def __update_config(self):
        self.update_config({
            "onlyonce": self._onlyonce,
            "cron": self._cron,
            "enabled": self._enabled,
            "sync_mode": self._sync_mode,
            "selected_seasons": self._selected_seasons,
            "storageplace": self._storageplace,
            "storage_mode": self._storage_mode,
        })

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("退出插件失败：%s" % str(e))


if __name__ == "__main__":
    anistrm = ANiStrm()
    name_list = anistrm.get_latest_list()
    print(name_list)
