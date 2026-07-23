# Install Proof

日期：2026-07-23

## 已验证

- 实际安装目录：`~/.agents/skills/qiaomu-youtube-download`
- 平台：macOS Apple Silicon
- Python：系统可执行环境通过语法与 CLI 帮助检查
- yt-dlp：Homebrew `2026.07.04`，与当日官方 stable Release 一致
- 版本门禁：`doctor --upgrade` 在 API 403 时回退官方 latest 页面，确认无需升级且无 warning
- FFmpeg/ffprobe：8.1.2
- 包验证、触发评估、Meta Skill 验证通过
- 实体文件同步：工作区与安装目录内容一致，`.git` 与缓存除外
- 路由同步：`qiaomu-toolbox`、`qiaomu-markdown-proxy`、NotebookLM 排除规则与发布示例均改为 `qiaomu-youtube-download`
- 实际安装目录复验：公开 Shorts 的 Chrome Cookie + Data API + 文件复用 + ffprobe 全部通过

## missing evidence

- GitHub `npx skills add` clean install
- Windows/Linux 实机安装
