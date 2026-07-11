# zhihu-hot-hub

> LLM 快速理解：本仓库是一个知乎热榜采集与归档项目。它通过 GitHub Actions 定时运行 Python 脚本，调用知乎热榜接口，把热搜按稳定 key 聚合保存，并为已存在热搜维护“采集时间-热度值”的变化轨迹。

## 项目作用

`zhihu-hot-hub` 用来长期记录知乎热榜的变化，适合做热点回溯、舆情观察、时间序列样本收集，或作为大模型分析中文互联网热点议题的数据源。

当前 fork 版本只保留知乎热榜采集，不再维护知乎日报内容。

核心行为：

- 采集来源：知乎热榜 API `https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=30`
- 采集内容：热榜前 30 条条目，包含标题、链接、摘要、热度、回答数、图片等知乎返回字段
- 每日聚合：写入 `raw/hot-question-YYYY-MM-DD.json`
- 全局聚合：写入 `raw/hot-question-history.json`
- 阅读归档：写入 `archives/`，文件名形如 `YYYY-MM-DD.md`
- 最新展示：用 `template/README.md` 渲染并覆盖根目录 `README.md`，展示当天热度轨迹
- 自动更新：`.github/workflows/schedule-update.yml` 每 3 小时运行一次，也支持手动触发

## 运行方式

```bash
pip install -r requirements.txt
python main.py
```

## 热度可视化

```bash
python visualize/build_index.py
python -m http.server
```

然后访问 [http://localhost:8000/visualize/](http://localhost:8000/visualize/)，可以按日期浏览热榜、搜索话题，并查看单个话题的当天/全局热度轨迹。

可选环境变量：

- `ZHIHU_COOKIE`：知乎 Cookie。工作流会从 GitHub Secret `ZHIHU_COOKIE` 注入；本地不设置时会以空 Cookie 请求，是否可用取决于知乎接口当时的访问策略。
- `TZ`：工作流设置为 `Asia/Shanghai`，用于生成本地日期和更新时间。

## 数据流

```text
GitHub Actions / 本地执行
        |
        v
main.py
        |
        +-- Zhihu.get_hot_question() in zhihu.py
        |       |
        |       +-- GET 知乎热榜 API
        |
        +-- raw/hot-question-YYYY-MM-DD.json      每日聚合
        +-- raw/hot-question-history.json         全局聚合
        +-- archives/YYYY-MM-DD.md                当天热度轨迹
        +-- README.md                             当天热度轨迹
```

## 代码地图

- `main.py`：项目入口。负责调用抓取器、保存聚合数据、生成 README 和每日归档。
- `hot_question_aggregate.py`：热榜聚合逻辑。负责 key 提取、热度解析、旧格式迁移和 history 维护。
- `zhihu.py`：知乎接口客户端。配置请求头、重试策略，并调用热榜 API。
- `util.py`：时间、目录创建、UTF-8 写文件、JSON 中文安全序列化等工具函数。
- `template/README.md`：根 README 的生成模板。若要长期修改项目说明，优先改这个文件。
- `template/archive.md`：每日归档 Markdown 的生成模板。
- `raw/`：聚合后的 JSON 数据，适合程序化分析。
- `archives/`：按日期保存的 Markdown 热榜和热度轨迹快照，适合人工阅读。
- `.github/workflows/schedule-update.yml`：定时采集、提交并推送更新的 GitHub Actions 工作流。

## 数据格式提示

`raw/` 中的新数据使用 v2 聚合格式，主要字段为：

- `version`：固定为 `2`
- `scope`：`daily` 或 `global`
- `updated_at`：最近一次采集时间
- `items`：聚合后的热搜列表

每个热搜 item 使用 `card_id`、链接或标题作为去重 key，并保存 `latest_heat_text`、`latest_heat_value`、`latest_item` 和 `history`。`history` 中每个点包含 `observed_at`、`rank`、`heat_text`、`heat_value`；旧格式导入的点会带 `legacy_import: true`。

## 维护说明

- 根目录 `README.md` 是生成物，每次运行 `python main.py` 都会被 `template/README.md` 覆盖。
- 想让 README 的说明长期保留，应修改 `template/README.md`，再运行脚本刷新根 README。
- `archives/` 和 `raw/` 是历史数据产物，通常不需要手工编辑。
- 旧格式 `{"data": [...]}` 会在当天文件首次再次采集时迁移为 v2 聚合格式；历史旧文件不会全量回填。
- 工作流会执行 `git add .`、`git commit -m "auto update"`、`git push -u origin main`，因此采集结果会直接回写仓库。

## 当前热榜及当天热度轨迹

`更新时间：{updateTime}`

{questions}

## 历史归档

- Markdown 归档：[archives](archives)
- 原始 JSON：[raw](raw)

## 相关项目

- [微博热榜](https://github.com/lonnyzhang423/weibo-hot-hub)
- [头条热榜](https://github.com/lonnyzhang423/toutiao-hot-hub)
- [抖音热榜](https://github.com/lonnyzhang423/douyin-hot-hub)
- [GitHub 热榜](https://github.com/lonnyzhang423/github-hot-hub)
- [v2ex 热榜](https://github.com/lonnyzhang423/v2ex-hot-hub)

## License

See the [LICENSE](LICENSE) file for license rights and limitations (MIT).
