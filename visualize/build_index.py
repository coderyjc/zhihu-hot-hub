import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path


DATE_FILE_RE = re.compile(r'^hot-question-(\d{4}-\d{2}-\d{2})\.json$')


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def inspect_hot_question_file(path):
    try:
        data = load_json(path)
    except (json.JSONDecodeError, OSError):
        return None

    if isinstance(data, dict) and data.get('version') == 2 and isinstance(data.get('items'), list):
        return {
            'version': 2,
            'updated_at': data.get('updated_at') or '',
            'item_count': len(data.get('items') or []),
        }

    if isinstance(data, dict) and isinstance(data.get('data'), list):
        return {
            'version': 1,
            'updated_at': data.get('updated_at') or '',
            'item_count': len(data.get('data') or []),
        }

    return None


def build_index(raw_dir, output_dir):
    raw_path = Path(raw_dir)
    output_path = Path(output_dir)
    dates = []

    if raw_path.exists():
        for file in raw_path.iterdir():
            match = DATE_FILE_RE.match(file.name)
            if not match:
                continue

            info = inspect_hot_question_file(file)
            if not info:
                continue

            date = match.group(1)
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


def write_index(index, output_file):
    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, mode='w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description='Build visualize/data-index.json')
    parser.add_argument('--raw-dir', default=os.path.join(root, 'raw'))
    parser.add_argument('--output', default=os.path.join(root, 'visualize', 'data-index.json'))
    args = parser.parse_args()

    index = build_index(args.raw_dir, Path(args.output).parent)
    write_index(index, args.output)


if __name__ == '__main__':
    main()
