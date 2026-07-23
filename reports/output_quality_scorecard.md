# Output Quality Scorecard

## 当前证据

- `file-backed fixture`：`evals/output/cases.json`，`input_files` 为空，使用脱敏示例 URL。
- 旧版基线已复现：未设置 YouTube API Key 时，`download` 在运行 yt-dlp 前直接退出。
- 2026-07-23 已通过 Homebrew 将 `yt-dlp` 从 `2026.03.17` 升级至官方稳定版 `2026.07.04`；FFmpeg 与 ffprobe 均为 8.1.2。
- `doctor --upgrade` 联网实测通过：GitHub API 遇到 403 限流时成功回退官方 `releases/latest`，确认本机与官方稳定版同为 `2026.07.04`，未触发不必要升级。
- 版本比较与过期升级分支已有单元测试；模拟 `2026.07.04 → 2026.07.23` 时仅调用一次 Homebrew 升级并复验新版本。
- Provider-backed Shorts 验证：自动检测并读取 Chrome Cookie，无警告；可选 Data API 实际返回发布时间、播放量与点赞数。
- 新脚本端到端下载成功：MP4 7,239,249 bytes，AV1 + AAC，1080×1920，48.855 秒，`ffprobe` 通过。
- 可选性验证：临时移除两个 API Key 后，元数据仍成功且 `data_api_used: false`；搜索自动回退 `yt-dlp-search`。恢复 Key 后，搜索使用 `youtube-data-api-v3` 并返回时长、播放量与点赞数。
- 单元测试 4/4、路由回归 13/13 通过；结构、Python、JSON、Meta Skill 校验均通过。
- 实际安装目录已复验：`cookies_from_browser: chrome`、`data_api_used: true`、无警告；既有视频被识别为 `created: false` 并重新通过 ffprobe，没有覆盖文件。

## missing evidence

- 普通长视频、MP3 与字幕的 provider-backed 端到端验证。
- 需要登录、年龄或地区验证内容的显式 Cookie 路径。
- Windows/Linux 实机运行。
- 播放列表边界、限流与独立人工安全审计。

在证据补齐前，不得声称“支持所有 YouTube 视频”“绕过地区/年龄限制”或“全平台生产验证”。
