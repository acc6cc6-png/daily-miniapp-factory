# AI 自动造小程序系统

一个适合部署到 GitHub Pages 的静态站点项目。

它每天自动执行这条链路：

1. 抓取产品榜单、科技媒体、中文热点与用户讨论
2. 过滤噪声，提炼高商业价值信号
3. 生成一份《今日自动生成小程序方案》
4. 发布到静态页面，并归档历史快照

## 目录

- `config/sources.json`: 信号源与站点配置
- `scripts/daily_digest_v2.py`: 主构建脚本
- `scripts/miniapp_factory.py`: 小程序方向评分与方案生成引擎
- `docs/`: GitHub Pages 站点目录
- `.github/workflows/daily-digest.yml`: 定时构建与发布

## 页面

- `docs/index.html`: 今日小程序方案首页
- `docs/research.html`: 市场信号研究台
- `docs/monitor.html`: 原始抓取监控
- `docs/about.html`: 系统说明

## 本地运行

```bash
pip install -r requirements.txt
py scripts/daily_digest_v2.py
py -m http.server 4173 --directory docs
```

## GitHub Pages

把仓库推到 GitHub 后，在仓库的 `Settings -> Pages` 中启用 Pages。

Secrets 建议配置：

- `OPENAI_API_KEY`
- `OPENAI_MODEL`

没有密钥也能运行，系统会退回规则引擎模式。
