# 下载工作流

## 状态机

`DEPENDENCY CHECK → VALIDATE → METADATA → DOWNLOAD → VERIFY → REPORT`

失败时报告阶段和错误，不把失败文件误报为交付物。

## 1. yt-dlp 版本检查与升级

每次下载任务先运行：

```bash
python3 scripts/youtube.py doctor --upgrade
```

脚本优先通过 yt-dlp 官方 GitHub Releases API 查询最新稳定版；API 限流时回退官方 `releases/latest` 重定向。只有已安装版本较旧时才升级：Homebrew 安装调用 `brew upgrade yt-dlp`，其他安装调用现有 `yt-dlp -U`，随后重新读取版本确认升级确实生效。两个官方入口都暂时失败时返回 warning，继续使用本机版本，不阻断下载。

## 2. URL 与范围

- 允许 `youtube.com/watch`、`youtube.com/shorts/<id>`、`youtube.com/live/<id>`、`youtube.com/embed/<id>`、`youtu.be/<id>`。
- 必须使用 HTTPS，拒绝用户名、密码、自定义端口和伪造子域名。
- 默认 `--no-playlist`，即使 URL 带播放列表参数也只处理单个视频。
- 频道或播放列表批量任务必须先明确范围与上限，不由本脚本隐式展开。

## 3. 元数据预检

运行：

```bash
python3 scripts/youtube.py info '<URL>'
```

元数据与下载不要求 YouTube Data API Key。配置 `YT_BROWSE_API_KEY` 或 `YOUTUBE_API_KEY` 时，脚本额外使用 YouTube Data API v3 补充发布时间、播放量和点赞数；API 失败不阻断 yt-dlp 下载。

## 4. 视频下载

默认：

```bash
python3 scripts/youtube.py download '<URL>' --quality best --dir '<目录>'
```

- 优先 MP4 视频与 M4A 音频，必要时回退其他公开格式。
- 允许 `best`、`1080p`、`720p`、`480p`。
- 输出模板包含 `[video_id]`，并启用 `--no-overwrites`。
- yt-dlp 使用自身 `.part` 临时文件机制；未完成文件不能进入交付清单。

## 5. 音频与字幕

音频：

```bash
python3 scripts/youtube.py audio '<URL>' --dir '<目录>'
```

输出最高质量 MP3，并验证存在音频流与有效时长。

字幕：

```bash
python3 scripts/youtube.py subtitles '<URL>' --langs 'en,zh-Hans' --dir '<目录>'
```

同时请求人工字幕与自动字幕，转换为 SRT，并为每份 SRT 生成保留时间戳的 TXT。没有字幕时报告 `download` 阶段失败，不生成虚假文本。

## 6. Cookie 与 API 回退

默认 `--cookies-from-browser auto`，按 Chrome、Edge、Firefox、Safari 检测本机浏览器。自动 Cookie 路径失败时，无 Cookie 重试；显式指定浏览器时失败则直接报告。可禁用：

```bash
python3 scripts/youtube.py download '<URL>' --cookies-from-browser chrome
python3 scripts/youtube.py download '<URL>' --cookies-from-browser none
```

不得把 Cookie 导出到文件、终端、日志、报告或问题单。

搜索优先使用可选 Data API Key；Key 缺失、配额耗尽或接口失败时回退 `ytsearchN:`。API Key 不得进入日志、错误消息、报告或测试夹具。

## 7. 验证和交付

- 视频：至少一个视频流，时长大于零；报告视频/音频编码、分辨率、容器和大小。
- 音频：至少一个音频流，时长大于零；报告编码、容器和大小。
- 字幕：SRT/TXT 均存在且非零。
- 返回绝对路径；`created: false` 表示复用了目标目录中已存在且通过验证的文件。

## 已知边界

- YouTube 可能改变播放器签名、客户端要求或公开格式。
- 某些格式需要登录、年龄/地区验证或特定客户端，不保证可下载。
- 字幕语言表达式由 yt-dlp 解释；自动字幕可能存在识别错误。
- 搜索有 Key 时支持 Data API 的相关度、日期、播放量与评分排序；无 Key 时回退 yt-dlp 相关度搜索。
