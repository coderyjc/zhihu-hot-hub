import os

import util
from util import logger
from zhihu import Zhihu


def generate_archive_md(questions, stories):
    """生成归档readme
    """
    def question(item):
        target = item['target']
        title = target['title_area']['text']
        url = target['link']['url']
        return '1. [{}]({})'.format(title, url)

    def story(item):
        title = item['title']
        url = item['url']
        hint = item.get('hint', '')
        return '1. [{}]({}) `{}`'.format(title, url, hint)

    questionMd = '暂无数据'
    if questions:
        questionMd = '\n'.join([question(item) for item in questions])

    dailyMd = '暂无数据'
    if stories:
        dailyMd = '\n'.join([story(item) for item in stories])

    md = ''
    file = os.path.join('template', 'archive.md')
    with open(file, encoding='utf-8') as f:
        md = f.read()

    now = util.current_time()
    md = md.replace("{updateTime}", now)
    md = md.replace("{questions}", questionMd)
    md = md.replace("{daily}", dailyMd)

    return md


def generate_readme(questions, stories):
    """生成readme
    """
    def question(item):
        target = item['target']
        title = target['title_area']['text']
        url = target['link']['url']
        return '1. [{}]({})'.format(title, url)

    def story(item):
        title = item['title']
        url = item['url']
        hint = item.get('hint', '')
        return '1. [{}]({}) `{}`'.format(title, url, hint)

    questionMd = '暂无数据'
    if questions:
        questionMd = '\n'.join([question(item) for item in questions])

    dailyMd = '暂无数据'
    if stories:
        dailyMd = '\n'.join([story(item) for item in stories])

    readme = ''
    file = os.path.join('template', 'README.md')
    with open(file, encoding='utf-8') as f:
        readme = f.read()

    now = util.current_time()
    readme = readme.replace("{updateTime}", now)
    readme = readme.replace("{questions}", questionMd)
    readme = readme.replace("{daily}", dailyMd)

    return readme


def saveReadme(md):
    logger.debug('today md:%s', md)
    util.write_text('README.md', md)


def saveArchiveMd(md):
    logger.debug('archive md:%s', md)
    name = util.current_date()+'.md'
    file = os.path.join('archives', name)
    util.write_text(file, md)


def saveRawContent(content: str, filePrefix: str, fileSuffix='json'):
    logger.debug('raw content:%s', content)
    name = '{}-{}.{}'.format(filePrefix, util.current_date(), fileSuffix)
    file = os.path.join('raw', name)
    util.write_text(file, content)


def run():
    zhihu = Zhihu()
    # 热门话题
    questions, resp = zhihu.get_hot_question()
    if resp:
        text = util.cnsafe_json(resp.text)
        saveRawContent(text, 'hot-question', 'json')
    # 知乎日报
    stories, resp = zhihu.get_daily_report()
    if resp:
        text = util.cnsafe_json(resp.text)
        saveRawContent(text, 'daily-report', 'json')

    # 最新数据
    todayMd = generate_readme(questions, stories)
    saveReadme(todayMd)
    # 归档
    archiveMd = generate_archive_md(questions, stories)
    saveArchiveMd(archiveMd)


if __name__ == "__main__":
    run()
