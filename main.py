import os

import util
from util import logger
from zhihu import Zhihu


def generate_archive_md(questions):
    """生成归档readme
    """
    def question(item):
        target = item['target']
        title = target['title_area']['text']
        url = target['link']['url']
        return '1. [{}]({})'.format(title, url)

    questionMd = '暂无数据'
    if questions:
        questionMd = '\n'.join([question(item) for item in questions])

    md = ''
    file = os.path.join('template', 'archive.md')
    with open(file, encoding='utf-8') as f:
        md = f.read()

    now = util.current_time()
    md = md.replace("{updateTime}", now)
    md = md.replace("{questions}", questionMd)

    return md


def generate_readme(questions):
    """生成readme
    """
    def question(item):
        target = item['target']
        title = target['title_area']['text']
        url = target['link']['url']
        return '1. [{}]({})'.format(title, url)

    questionMd = '暂无数据'
    if questions:
        questionMd = '\n'.join([question(item) for item in questions])


    readme = ''
    file = os.path.join('template', 'README.md')
    with open(file, encoding='utf-8') as f:
        readme = f.read()

    now = util.current_time()
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

    # 最新数据
    todayMd = generate_readme(questions)
    saveReadme(todayMd)
    # 归档
    archiveMd = generate_archive_md(questions)
    saveArchiveMd(archiveMd)


if __name__ == "__main__":
    run()
