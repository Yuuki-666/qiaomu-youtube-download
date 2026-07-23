# Install Proof

日期：2026-07-23

## 已验证

- 公开仓库：`https://github.com/joeseesun/qiaomu-youtube-download`
- 发布流程：feature branch → PR #1 → squash merge 到 `main`
- `npx skills add joeseesun/qiaomu-youtube-download --list`：发现 1 个 skill，名称正确
- 从 GitHub `main` 安装到独立临时目录：成功生成 `.agents/skills/qiaomu-youtube-download`
- GitHub 干净安装复验：4/4 单测、包校验、`doctor --upgrade`、公开 Shorts 下载与 ffprobe 均通过
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
- 旧安装目录 `~/.agents/skills/qiaomu-youtube` 已在新目录验证后移除，避免重复路由
- v1.2.0 本地发布候选：10/10 单元测试、包校验和 Meta Skill 校验通过
- v1.2.0 长视频回归：复用 11 分 40 秒公开 MP4，持续进度可见；最终筛选只返回 1920×1080 AV1 + AAC MP4，没有把分离 M4A 当视频验证

## missing evidence

- Windows/Linux 实机安装
