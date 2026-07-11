import argparse
import json
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


DATE_FILE_RE = re.compile(r'^hot-question-(\d{4}-\d{2}-\d{2})\.json$')


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def parse_heat_value(text):
    if not text:
        return None

    match = re.search(r'(\d+(?:\.\d+)?)\s*([万亿]?)', str(text).replace(',', ''))
    if not match:
        return None

    try:
        value = Decimal(match.group(1))
    except InvalidOperation:
        return None

    unit = match.group(2)
    if unit == '万':
        value *= Decimal(10000)
    elif unit == '亿':
        value *= Decimal(100000000)
    return int(value)


def extract_legacy_item(raw_item, rank, observed_at):
    target = raw_item.get('target') or {}
    title_area = target.get('title_area') or {}
    link = target.get('link') or {}
    metrics_area = target.get('metrics_area') or {}
    title = title_area.get('text') or '无标题'
    url = link.get('url') or '#'
    heat_text = metrics_area.get('text') or ''
    heat_value = parse_heat_value(heat_text)

    return {
        'key': raw_item.get('card_id') or url or title,
        'title': title,
        'url': url,
        'first_seen': observed_at,
        'last_seen': observed_at,
        'first_rank': rank,
        'latest_rank': rank,
        'latest_heat_text': heat_text,
        'latest_heat_value': heat_value,
        'history': [{
            'observed_at': observed_at,
            'rank': rank,
            'heat_text': heat_text,
            'heat_value': heat_value,
            'legacy_import': True,
        }],
    }


def normalize_hot_question_data(data, date):
    if isinstance(data, dict) and data.get('version') == 2 and isinstance(data.get('items'), list):
        return {
            'version': 2,
            'updated_at': data.get('updated_at') or '',
            'items': data.get('items') or [],
        }

    if isinstance(data, dict) and isinstance(data.get('data'), list):
        observed_at = data.get('updated_at') or '{} 00:00:00 +0800'.format(date)
        return {
            'version': 1,
            'updated_at': data.get('updated_at') or '',
            'items': [
                extract_legacy_item(item, index + 1, observed_at)
                for index, item in enumerate(data.get('data') or [])
            ],
        }

    return None


def load_hot_question_file(path, date):
    try:
        data = load_json(path)
    except (json.JSONDecodeError, OSError):
        return None
    return normalize_hot_question_data(data, date)


def inspect_hot_question_file(path):
    match = DATE_FILE_RE.match(Path(path).name)
    date = match.group(1) if match else ''
    data = load_hot_question_file(path, date)
    if not data:
        return None
    return {
        'version': data['version'],
        'updated_at': data['updated_at'],
        'item_count': len(data['items']),
    }


def iter_hot_question_files(raw_dir):
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        return

    for file in raw_path.iterdir():
        match = DATE_FILE_RE.match(file.name)
        if not match:
            continue
        yield match.group(1), file


def build_index(raw_dir, output_dir):
    dates = []

    for date, file in iter_hot_question_files(raw_dir):
        info = inspect_hot_question_file(file)
        if not info:
            continue

        dates.append({
            'date': date,
            'path': '../raw/{}'.format(file.name),
            'updated_at': info['updated_at'],
            'item_count': info['item_count'],
            'version': info['version'],
        })

    dates.sort(key=lambda item: item['date'], reverse=True)
    return {
        'generated_at': datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z'),
        'global_path': '../raw/hot-question-history.json',
        'dates': dates,
    }


def item_latest_heat_value(item):
    value = item.get('latest_heat_value')
    if value is not None:
        return value
    return parse_heat_value(item.get('latest_heat_text'))


def point_heat_value(point):
    value = point.get('heat_value')
    if value is not None:
        return value
    return parse_heat_value(point.get('heat_text'))


def item_history(item):
    history = item.get('history')
    if isinstance(history, list) and history:
        return history

    heat_text = item.get('latest_heat_text') or ''
    return [{
        'observed_at': item.get('last_seen') or item.get('first_seen') or '',
        'rank': item.get('latest_rank'),
        'heat_text': heat_text,
        'heat_value': item_latest_heat_value(item),
    }]


def build_dashboard_stats(raw_dir):
    dates = []
    unique_keys = set()
    top_points = []
    totals = {
        'day_count': 0,
        'topic_record_count': 0,
        'unique_topic_count': 0,
        'history_point_count': 0,
        'v2_file_count': 0,
        'legacy_file_count': 0,
    }

    for date, file in iter_hot_question_files(raw_dir):
        data = load_hot_question_file(file, date)
        if not data:
            continue

        items = data['items']
        totals['day_count'] += 1
        totals['topic_record_count'] += len(items)
        if data['version'] == 2:
            totals['v2_file_count'] += 1
        else:
            totals['legacy_file_count'] += 1

        daily_total = 0
        daily_max = 0
        daily_top_title = ''
        daily_top_url = ''
        daily_history_points = 0

        for item in items:
            key = item.get('key') or item.get('url') or item.get('title')
            if key:
                unique_keys.add(key)

            heat_value = item_latest_heat_value(item)
            if heat_value is not None:
                daily_total += heat_value
                if heat_value > daily_max:
                    daily_max = heat_value
                    daily_top_title = item.get('title') or ''
                    daily_top_url = item.get('url') or ''

            history = item_history(item)
            daily_history_points += len(history)
            for point in history:
                point_value = point_heat_value(point)
                if point_value is None:
                    continue
                top_points.append({
                    'date': date,
                    'title': item.get('title') or '',
                    'url': item.get('url') or '',
                    'key': key or '',
                    'rank': point.get('rank'),
                    'observed_at': point.get('observed_at') or '',
                    'heat_text': point.get('heat_text') or '',
                    'heat_value': point_value,
                })

        totals['history_point_count'] += daily_history_points
        dates.append({
            'date': date,
            'total_heat_value': daily_total,
            'max_heat_value': daily_max,
            'topic_count': len(items),
            'history_point_count': daily_history_points,
            'top_topic_title': daily_top_title,
            'top_topic_url': daily_top_url,
        })

    totals['unique_topic_count'] = len(unique_keys)
    dates.sort(key=lambda item: item['date'])
    top_points.sort(key=lambda item: item['heat_value'], reverse=True)

    return {
        'generated_at': datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z'),
        'totals': totals,
        'top_heat_points': top_points[:10],
        'daily_series': dates,
    }


def write_index(index, output_file):
    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, mode='w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description='Build visualize static data files')
    parser.add_argument('--raw-dir', default=os.path.join(root, 'raw'))
    parser.add_argument('--output', default=os.path.join(root, 'visualize', 'data-index.json'))
    parser.add_argument('--dashboard-output', default=os.path.join(root, 'visualize', 'dashboard-stats.json'))
    args = parser.parse_args()

    index = build_index(args.raw_dir, Path(args.output).parent)
    write_index(index, args.output)
    dashboard_stats = build_dashboard_stats(args.raw_dir)
    write_index(dashboard_stats, args.dashboard_output)


if __name__ == '__main__':
    main()
