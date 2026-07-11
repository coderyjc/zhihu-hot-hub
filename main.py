import os

import hot_question_aggregate as aggregate
import util
from util import logger
from zhihu import Zhihu


def _legacy_observed_at(date):
    return '{} 00:00:00 +0800'.format(date)


def _history_text(history):
    if not history:
        return '暂无记录'

    fragments = []
    for point in history:
        observed_at = point.get('observed_at') or '未知时间'
        rank = point.get('rank')
        heat_text = point.get('heat_text') or '未知热度'
        rank_text = '#{}'.format(rank) if rank else '排名未知'
        legacy_text = '，旧格式导入' if point.get('legacy_import') else ''
        fragments.append('{}（{}，{}{}）'.format(
            observed_at,
            rank_text,
            heat_text,
            legacy_text,
        ))
    return ' → '.join(fragments)


def _question_md(items):
    def question(item):
        title = item.get('title') or '无标题'
        url = item.get('url') or '#'
        latest_heat_text = item.get('latest_heat_text') or '未知热度'
        latest_rank = item.get('latest_rank')
        rank_text = '#{}'.format(latest_rank) if latest_rank else '排名未知'
        return '\n'.join([
            '1. [{}]({})'.format(title, url),
            '   - 最新热度：{}；最新排名：{}'.format(latest_heat_text, rank_text),
            '   - 热度轨迹：{}'.format(_history_text(item.get('history') or [])),
        ])

    if not items:
        return '暂无数据'
    return '\n'.join([question(item) for item in items])


def generate_archive_md(daily_aggregate):
    """生成归档readme
    """
    md = ''
    file = os.path.join('template', 'archive.md')
    with open(file, encoding='utf-8') as f:
        md = f.read()

    now = daily_aggregate.get('updated_at') or util.current_time()
    questionMd = _question_md(daily_aggregate.get('items') or [])
    md = md.replace("{updateTime}", now)
    md = md.replace("{questions}", questionMd)

    return md


def generate_readme(daily_aggregate):
    """生成readme
    """
    readme = ''
    file = os.path.join('template', 'README.md')
    with open(file, encoding='utf-8') as f:
        readme = f.read()

    now = daily_aggregate.get('updated_at') or util.current_time()
    questionMd = _question_md(daily_aggregate.get('items') or [])
    readme = readme.replace("{updateTime}", now)
    readme = readme.replace("{questions}", questionMd)

    return readme


def saveReadme(md):
    logger.debug('today md:%s', md)
    util.write_text('README.md', md)


def saveArchiveMd(md):
    logger.debug('archive md:%s', md)
    name = util.current_date()+'.md'
    file = os.path.join('archives', name)
    util.write_text(file, md)


def loadDailyAggregate():
    today = util.current_date()
    now = util.current_time()
    return aggregate.load_aggregate_file(
        aggregate.daily_history_file(today),
        scope='daily',
        date=today,
        updated_at=now,
        legacy_observed_at=_legacy_observed_at(today),
    )


def saveHotQuestionAggregates(questions):
    today = util.current_date()
    now = util.current_time()
    daily_file = aggregate.daily_history_file(today)
    global_file = aggregate.GLOBAL_HISTORY_FILE

    daily_aggregate = aggregate.load_aggregate_file(
        daily_file,
        scope='daily',
        date=today,
        updated_at=now,
        legacy_observed_at=_legacy_observed_at(today),
    )
    global_aggregate = aggregate.load_aggregate_file(
        global_file,
        scope='global',
        updated_at=now,
        legacy_observed_at=now,
    )

    aggregate.upsert_items(daily_aggregate, questions, now)
    aggregate.upsert_items(global_aggregate, questions, now)

    util.write_text(daily_file, aggregate.dumps_aggregate(daily_aggregate))
    util.write_text(global_file, aggregate.dumps_aggregate(global_aggregate))
    return daily_aggregate


def run():
    zhihu = Zhihu()
    # 热门话题
    questions, resp = zhihu.get_hot_question()
    if resp:
        daily_aggregate = saveHotQuestionAggregates(questions)
    else:
        daily_aggregate = loadDailyAggregate()

    # 最新数据
    todayMd = generate_readme(daily_aggregate)
    saveReadme(todayMd)
    # 归档
    archiveMd = generate_archive_md(daily_aggregate)
    saveArchiveMd(archiveMd)


if __name__ == "__main__":
    run()
