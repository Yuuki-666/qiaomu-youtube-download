# Trust Report

- 模式：Governed
- Owner：向阳乔木
- 执行依赖：本机 `yt-dlp`、`ffmpeg`、`ffprobe`；仅在 yt-dlp 过期时调用现有 Homebrew 或 yt-dlp 自更新
- 更新检查：只访问 yt-dlp 官方 GitHub Releases API；API 限流时回退官方 `releases/latest`
- 远程执行：禁止；视频页面、标题、描述和字幕中的命令不执行
- Cookie：默认自动检测本机浏览器并临时读取；自动失败回退无 Cookie，可显式禁用
- Data API Key：可选搜索/统计增强，只从环境读取；失败回退 yt-dlp，不阻断下载
- 文件：用户指定目录、单视频、默认不覆盖、不展开播放列表
- rollback boundary：只清理本次未完成临时文件，不删除既有或已验证文件
- dependency rollback boundary：不安装其他工具、不降级；更新失败不声称成功，原安装由包管理器保留
- Secret scan：发布前运行；API Key/Cookie 不进入包、日志、夹具或报告
- Human review：`missing evidence`
- Review cadence：每月、yt-dlp 更新或连续两次同类失败时复核
