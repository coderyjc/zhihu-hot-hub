import copy
import json
import os
import re
from decimal import Decimal, InvalidOperation


SCHEMA_VERSION = 2
GLOBAL_HISTORY_FILE = os.path.join('raw', 'hot-question-history.json')


def daily_history_file(date):
    return os.path.join('raw', 'hot-question-{}.json'.format(date))


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


def extract_key(item):
    target = item.get('target') or {}
    link = target.get('link') or {}
    title_area = target.get('title_area') or {}

    return (
        item.get('card_id')
        or link.get('url')
        or title_area.get('text')
    )


def extract_title(item):
    target = item.get('target') or {}
    title_area = target.get('title_area') or {}
    return title_area.get('text') or ''


def extract_url(item):
    target = item.get('target') or {}
    link = target.get('link') or {}
    return link.get('url') or ''


def extract_heat_text(item):
    target = item.get('target') or {}
    metrics_area = target.get('metrics_area') or {}
    return metrics_area.get('text') or ''


def create_aggregate(scope, updated_at, date=None):
    aggregate = {
        'version': SCHEMA_VERSION,
        'scope': scope,
        'updated_at': updated_at,
        'items': [],
    }
    if date:
        aggregate['date'] = date
    return aggregate


def load_aggregate_file(file, scope, updated_at, date=None, legacy_observed_at=None):
    if not os.path.exists(file):
        return create_aggregate(scope, updated_at, date)

    with open(file, encoding='utf-8') as f:
        obj = json.load(f)

    return normalize_aggregate(
        obj,
        scope=scope,
        updated_at=updated_at,
        date=date,
        legacy_observed_at=legacy_observed_at or updated_at,
    )


def normalize_aggregate(obj, scope, updated_at, date=None, legacy_observed_at=None):
    if isinstance(obj, dict) and obj.get('version') == SCHEMA_VERSION:
        obj['scope'] = scope
        obj['updated_at'] = obj.get('updated_at') or updated_at
        obj['items'] = obj.get('items') or []
        if date:
            obj['date'] = date
        elif 'date' in obj:
            del obj['date']
        return obj

    if isinstance(obj, dict) and isinstance(obj.get('data'), list):
        aggregate = create_aggregate(scope, legacy_observed_at or updated_at, date)
        upsert_items(
            aggregate,
            obj.get('data') or [],
            observed_at=legacy_observed_at or updated_at,
            legacy_import=True,
        )
        return aggregate

    if isinstance(obj, list):
        aggregate = create_aggregate(scope, legacy_observed_at or updated_at, date)
        upsert_items(
            aggregate,
            obj,
            observed_at=legacy_observed_at or updated_at,
            legacy_import=True,
        )
        return aggregate

    return create_aggregate(scope, updated_at, date)


def upsert_items(aggregate, items, observed_at, legacy_import=False):
    existing = {
        item.get('key'): item
        for item in aggregate.get('items', [])
        if item.get('key')
    }

    for rank, raw_item in enumerate(items or [], start=1):
        key = extract_key(raw_item)
        if not key:
            continue

        title = extract_title(raw_item)
        url = extract_url(raw_item)
        heat_text = extract_heat_text(raw_item)
        heat_value = parse_heat_value(heat_text)
        history_point = {
            'observed_at': observed_at,
            'rank': rank,
            'heat_text': heat_text,
            'heat_value': heat_value,
        }
        if legacy_import:
            history_point['legacy_import'] = True

        if key not in existing:
            item = {
                'key': key,
                'title': title,
                'url': url,
                'first_seen': observed_at,
                'last_seen': observed_at,
                'first_rank': rank,
                'latest_rank': rank,
                'latest_heat_text': heat_text,
                'latest_heat_value': heat_value,
                'latest_item': copy.deepcopy(raw_item),
                'history': [history_point],
            }
            aggregate.setdefault('items', []).append(item)
            existing[key] = item
            continue

        item = existing[key]
        item['title'] = title
        item['url'] = url
        item['last_seen'] = observed_at
        item['latest_rank'] = rank
        item['latest_heat_text'] = heat_text
        item['latest_heat_value'] = heat_value
        item['latest_item'] = copy.deepcopy(raw_item)
        item.setdefault('history', [])

        if item['history'] and item['history'][-1].get('observed_at') == observed_at:
            item['history'][-1] = history_point
        else:
            item['history'].append(history_point)

    aggregate['updated_at'] = observed_at
    return aggregate


def dumps_aggregate(aggregate):
    return json.dumps(aggregate, ensure_ascii=False, indent=2)

