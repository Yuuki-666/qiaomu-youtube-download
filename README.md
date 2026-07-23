# qiaomu-youtube-download

> 把 YouTube、Shorts 或直播链接交给 Agent，直接得到经过验证的视频、MP3、字幕或元数据。

[![Last commit](https://img.shields.io/github/last-commit/joeseesun/qiaomu-youtube-download?style=flat-square)](https://github.com/joeseesun/qiaomu-youtube-download/commits/main)
[![License](https://img.shields.io/github/license/joeseesun/qiaomu-youtube-download?style=flat-square)](LICENSE)

```bash
npx skills add joeseesun/qiaomu-youtube-download
```

## 为什么值得用

旧版 `yt-search-download` 把 YouTube Data API Key 错误地设成所有命令的前置条件，导致普通下载也可能直接退出；它还会自动尝试浏览器 Cookie，却不返回实际文件路径和媒体验证结果。

`qiaomu-youtube-download` 将 URL 下载与搜索解耦：下载不要求 API Key；配置 Key 时，搜索与统计信息优先使用 YouTube Data API v3。每次下载任务先对照 yt-dlp 官方稳定版检查并按需升级。下载默认自动读取本机浏览器 Cookie 以提高稳定性，Cookie 读取失败时自动回退公开无 Cookie 路径。下载后使用 `ffprobe` 验证，并返回真实绝对路径。

## 安装

```bash
npx skills add joeseesun/qiaomu-youtube-download
```

本地验证：

```bash
python3 ~/.agents/skills/qiaomu-youtube-download/scripts/validate_skill.py ~/.agents/skills/qiaomu-youtube-download
python3 ~/.agents/skills/qiaomu-youtube-download/scripts/trigger_eval.py ~/.agents/skills/qiaomu-youtube-download
python3 ~/.agents/skills/qiaomu-youtube-download/scripts/test_youtube.py
python3 ~/.agents/skills/qiaomu-youtube-download/scripts/youtube.py doctor
```

## 你可以直接这样说

- “下载这个 Shorts：https://www.youtube.com/shorts/xxxx”
- “把这个 YouTube 视频保存到当前目录，最高画质”
- “这期播客只要 MP3：https://youtu.be/xxxx”
- “下载这个视频的中英文字幕，给我 SRT 和 TXT”
- “查一下这个 YouTube 视频的标题、时长和分辨率”
- “在 YouTube 搜索最近的 AI Agent 视频”

## 它会做什么

1. 对照 yt-dlp 官方 GitHub 最新稳定版检查本机版本，只在过期时按当前安装方式升级并复验。
2. 严格校验 YouTube URL，不接受链接内凭据、自定义端口或其他域名。
3. 默认自动检测本机浏览器 Cookie；读取失败时回退无 Cookie 下载单个视频。
4. 支持最佳画质、1080p、720p、480p、MP3、字幕及基础搜索。
5. 使用包含视频 ID 的文件名，避免不同视频重名；不覆盖既有文件。
6. 用 `ffprobe` 检查音视频流、分辨率、编码、时长和大小。
7. 返回机器可读 JSON，供 Agent 准确交付文件。

## 前置条件

- [ ] Python 3：`python3 --version`
- [ ] yt-dlp：`yt-dlp --version`
- [ ] FFmpeg/ffprobe：`ffmpeg -version`、`ffprobe -version`
- [ ] 可选搜索增强：`YT_BROWSE_API_KEY` 或 `YOUTUBE_API_KEY`
- [ ] 用户有权访问并保存目标内容

下载不需要 YouTube Data API Key；Key 只增强搜索、发布时间和播放/点赞统计。

## 命令示例

```bash
# 检查并按需升级 yt-dlp（Agent 下载前默认执行）
python3 scripts/youtube.py doctor --upgrade

# 查看信息
python3 scripts/youtube.py info 'https://www.youtube.com/shorts/VIDEO_ID'

# 下载最佳画质
python3 scripts/youtube.py download 'VIDEO_URL' --dir ~/Downloads

# 限制到 1080p
python3 scripts/youtube.py download 'VIDEO_URL' --quality 1080p --dir ~/Downloads

# 提取 MP3
python3 scripts/youtube.py audio 'VIDEO_URL' --dir ~/Downloads

# 字幕：SRT + TXT
python3 scripts/youtube.py subtitles 'VIDEO_URL' --langs 'en,zh-Hans' --dir ~/Downloads

# 基础搜索
python3 scripts/youtube.py search 'AI agents' --max 10

# 禁用自动浏览器 Cookie
python3 scripts/youtube.py download 'VIDEO_URL' --cookies-from-browser none
```

## 输出示例

```json
{
  "ok": true,
  "command": "download",
  "id": "VIDEO_ID",
  "title": "Video title",
  "files": [
    {
      "path": "/Users/example/Downloads/Video title [VIDEO_ID].mp4",
      "bytes": 12345678,
      "video_codec": "h264",
      "width": 1080,
      "height": 1920,
      "duration_seconds": 49.0
    }
  ],
  "cookies_from_browser": "chrome",
  "data_api_used": true
}
```

## API、Cookie 与隐私

如果设置了 `YT_BROWSE_API_KEY` 或 `YOUTUBE_API_KEY`，搜索和统计优先使用 YouTube Data API v3；Key 不会进入命令输出或报告。没有 Key 或 API 暂时失败时自动使用 yt-dlp 搜索。

下载默认使用 `--cookies-from-browser auto`，按 Chrome、Edge、Firefox、Safari 检测本机浏览器；自动读取失败时回退无 Cookie。可明确指定或禁用：

```bash
python3 scripts/youtube.py download 'VIDEO_URL' --cookies-from-browser chrome
python3 scripts/youtube.py download 'VIDEO_URL' --cookies-from-browser none
```

Cookie 仅由本机 `yt-dlp` 临时读取，不复制到 Skill、不打印、不写入报告。

## yt-dlp 更新策略

`doctor` 只查询 [yt-dlp 官方 GitHub Releases](https://github.com/yt-dlp/yt-dlp/releases/latest)，API 限流时回退同一官方仓库的 latest 重定向。加 `--upgrade` 后，只有稳定版确实较新才执行更新：Homebrew 安装使用 `brew upgrade yt-dlp`，其他安装使用当前 yt-dlp 的 `-U`。更新后会重新读取版本；GitHub 暂不可达时只返回 warning，不阻断下载。

这个步骤会在必要时修改本机 yt-dlp 安装，但不会安装其他依赖、降级或执行来自视频页面的命令。

## Troubleshooting

| 症状 | 原因 | 处理 |
|---|---|---|
| `yt-dlp not found` | 未安装依赖 | `brew install yt-dlp` |
| yt-dlp 检查显示 `outdated: true` | 只运行了 `doctor`，未允许升级 | 运行 `python3 scripts/youtube.py doctor --upgrade` |
| `update-check` warning | GitHub API 暂时不可达或限流 | 继续使用现有版本下载，稍后重试 `doctor --upgrade` |
| `upgrade` 失败 | 包管理器权限、锁或安装方式不支持自更新 | 按 JSON 中的 manager 检查 Homebrew/yt-dlp，再重试 |
| 只能得到低清视频 | 缺少 ffmpeg，无法合并最佳视频与音频 | `brew install ffmpeg` |
| Data API 配额、Key 或网络错误 | 官方搜索增强不可用 | 自动回退 yt-dlp 搜索；下载不受影响 |
| 提示登录、年龄或地区限制 | 浏览器 Cookie 不存在、已过期或账号无权限 | 登录浏览器后重试，或显式指定其他浏览器 |
| 浏览器 Cookie 读取失败 | 浏览器数据库被锁、Keychain 未授权或浏览器不受支持 | 关闭相关浏览器重试，或不使用 Cookie |
| 没有字幕文件 | 视频没有所选语言的人工/自动字幕 | 调整 `--langs`，或另走 ASR 转录 Skill |
| 已存在同名文件 | 默认禁止覆盖 | 保留既有文件；新视频用 ID 区分 |

## 风险与边界

- 只下载用户有权访问和保存的内容。
- 不绕过付费、登录、地域、年龄、版权或 DRM 限制。
- 默认会在本机自动读取检测到的浏览器 Cookie，可用 `--cookies-from-browser none` 禁用；Cookie 不复制、不打印、不写入报告。
- 默认单视频，不无限批量抓取频道或播放列表。
- `doctor --upgrade` 会在检测到官方稳定新版时修改现有 yt-dlp 安装；不会升级其他 Homebrew 公式。
- 不负责重新上传、转载或规避平台政策。

## 致谢

- 下载与元数据：[yt-dlp](https://github.com/yt-dlp/yt-dlp)
- 媒体检查：[FFmpeg](https://ffmpeg.org/)
- 技能工程：`qiaomu-meta-skill`，受 [yaojingang/yao-meta-skill](https://github.com/yaojingang/yao-meta-skill) 启发

<!-- qiaomu-profile:start -->
## 关于向阳乔木

向阳乔木（乔向阳 / Joe）是一位实践型 AI 产品与内容创作者，长期把前沿 AI 变化转译成可复用的工作流、产品判断、AI 编程实践、AI 搜索实践和 GEO/AI 营销方法。

- 个人网站: https://qiaomu.ai
- 博客: https://blog.qiaomu.ai
- X: https://x.com/vista8
- GitHub: https://github.com/joeseesun/
- 微信公众号: 向阳乔木推荐看

### 支持与关注

| 打赏支持 | 微信公众号 |
|---|---|
| <img src="assets/qiaomu-profile/qiaomu_reward_qr.png" alt="向阳乔木打赏二维码" width="180" /> | <img src="assets/qiaomu-profile/qiaomu_wechat_public_account_qr.jpg" alt="向阳乔木推荐看公众号二维码" width="180" /> |
| 感谢支持乔木持续分享 AI 实践 | 扫码关注「向阳乔木推荐看」 |

<!-- qiaomu-profile:end -->

## License

MIT

Copyright (c) 向阳乔木 · [X](https://x.com/vista8) · [GitHub](https://github.com/joeseesun/)
