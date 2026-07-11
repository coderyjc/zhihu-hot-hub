import json
import os
import tempfile
import unittest

from visualize import build_index


def v2_item(key='Q_1', title='话题一', heat_text='100 万热度', heat_value=1000000,
            rank=1, history=None):
    return {
        'key': key,
        'title': title,
        'url': 'https://www.zhihu.com/question/{}'.format(key),
        'latest_rank': rank,
        'latest_heat_text': heat_text,
        'latest_heat_value': heat_value,
        'first_seen': '2026-07-10 10:00:00 +0800',
        'last_seen': '2026-07-10 13:00:00 +0800',
        'history': history if history is not None else [{
            'observed_at': '2026-07-10 13:00:00 +0800',
            'rank': rank,
            'heat_text': heat_text,
            'heat_value': heat_value,
        }],
    }


def legacy_item(card_id='Q_legacy', title='旧话题', heat='50 万热度'):
    return {
        'card_id': card_id,
        'target': {
            'title_area': {'text': title},
            'link': {'url': 'https://www.zhihu.com/question/{}'.format(card_id)},
            'metrics_area': {'text': heat},
        },
    }


class VisualizeBuildIndexTest(unittest.TestCase):

    def write_json(self, directory, name, content):
        path = os.path.join(directory, name)
        with open(path, mode='w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False)
        return path

    def test_builds_index_from_v2_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, 'raw')
            os.makedirs(raw)
            self.write_json(raw, 'hot-question-2026-07-10.json', {
                'version': 2,
                'updated_at': '2026-07-10 10:00:00 +0800',
                'items': [{}, {}],
            })
            self.write_json(raw, 'hot-question-2026-07-11.json', {
                'version': 2,
                'updated_at': '2026-07-11 10:00:00 +0800',
                'items': [{}],
            })

            index = build_index.build_index(raw, os.path.join(tmp, 'visualize'))

        self.assertEqual(['2026-07-11', '2026-07-10'], [item['date'] for item in index['dates']])
        self.assertEqual(1, index['dates'][0]['item_count'])
        self.assertEqual(2, index['dates'][1]['item_count'])
        self.assertEqual('../raw/hot-question-history.json', index['global_path'])

    def test_counts_legacy_data_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, 'raw')
            os.makedirs(raw)
            self.write_json(raw, 'hot-question-2026-07-10.json', {
                'data': [{}, {}, {}],
            })

            index = build_index.build_index(raw, os.path.join(tmp, 'visualize'))

        self.assertEqual(1, len(index['dates']))
        self.assertEqual(1, index['dates'][0]['version'])
        self.assertEqual(3, index['dates'][0]['item_count'])

    def test_ignores_global_and_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, 'raw')
            os.makedirs(raw)
            self.write_json(raw, 'hot-question-history.json', {
                'version': 2,
                'items': [{}],
            })
            with open(os.path.join(raw, 'hot-question-2026-07-10.json'), mode='w', encoding='utf-8') as f:
                f.write('{bad json')

            index = build_index.build_index(raw, os.path.join(tmp, 'visualize'))

        self.assertEqual([], index['dates'])

    def test_builds_dashboard_stats_from_v2_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, 'raw')
            os.makedirs(raw)
            self.write_json(raw, 'hot-question-2026-07-10.json', {
                'version': 2,
                'updated_at': '2026-07-10 13:00:00 +0800',
                'items': [
                    v2_item('Q_1', '话题一', '100 万热度', 1000000, 1, [
                        {'observed_at': '2026-07-10 10:00:00 +0800', 'rank': 1, 'heat_text': '80 万热度', 'heat_value': 800000},
                        {'observed_at': '2026-07-10 13:00:00 +0800', 'rank': 1, 'heat_text': '100 万热度', 'heat_value': 1000000},
                    ]),
                    v2_item('Q_2', '话题二', '2 万热度', 20000, 2),
                ],
            })

            stats = build_index.build_dashboard_stats(raw)

        self.assertEqual(1, stats['totals']['day_count'])
        self.assertEqual(2, stats['totals']['topic_record_count'])
        self.assertEqual(2, stats['totals']['unique_topic_count'])
        self.assertEqual(3, stats['totals']['history_point_count'])
        self.assertEqual(1, stats['totals']['v2_file_count'])
        self.assertEqual(0, stats['totals']['legacy_file_count'])
        self.assertEqual(1020000, stats['daily_series'][0]['total_heat_value'])
        self.assertEqual(1000000, stats['top_heat_points'][0]['heat_value'])
        self.assertEqual('话题一', stats['top_heat_points'][0]['title'])

    def test_dashboard_stats_include_legacy_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, 'raw')
            os.makedirs(raw)
            self.write_json(raw, 'hot-question-2026-07-10.json', {
                'data': [
                    legacy_item('Q_1', '旧话题一', '50 万热度'),
                    legacy_item('Q_2', '旧话题二', '2 亿热度'),
                ],
            })

            stats = build_index.build_dashboard_stats(raw)

        self.assertEqual(1, stats['totals']['legacy_file_count'])
        self.assertEqual(2, stats['totals']['topic_record_count'])
        self.assertEqual(200500000, stats['daily_series'][0]['total_heat_value'])
        self.assertEqual('旧话题二', stats['top_heat_points'][0]['title'])

    def test_dashboard_stats_ignore_global_invalid_and_empty_heat(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, 'raw')
            os.makedirs(raw)
            self.write_json(raw, 'hot-question-history.json', {
                'version': 2,
                'items': [v2_item('GLOBAL')],
            })
            with open(os.path.join(raw, 'hot-question-2026-07-09.json'), mode='w', encoding='utf-8') as f:
                f.write('{bad json')
            self.write_json(raw, 'hot-question-2026-07-10.json', {
                'version': 2,
                'items': [
                    v2_item('Q_1', '无热度', '未知', None, 1, [
                        {'observed_at': '2026-07-10 10:00:00 +0800', 'rank': 1, 'heat_text': '未知', 'heat_value': None},
                    ]),
                    v2_item('Q_2', '有热度', '3 万热度', 30000, 2),
                ],
            })

            stats = build_index.build_dashboard_stats(raw)

        self.assertEqual(1, stats['totals']['day_count'])
        self.assertEqual(2, stats['totals']['topic_record_count'])
        self.assertEqual(2, stats['totals']['history_point_count'])
        self.assertEqual(1, len(stats['top_heat_points']))
        self.assertEqual('有热度', stats['top_heat_points'][0]['title'])

    def test_dashboard_top10_sorted_and_limited(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, 'raw')
            os.makedirs(raw)
            items = [
                v2_item('Q_{}'.format(index), '话题{}'.format(index), '{} 万热度'.format(index), index * 10000, index)
                for index in range(1, 13)
            ]
            self.write_json(raw, 'hot-question-2026-07-10.json', {
                'version': 2,
                'items': items,
            })

            stats = build_index.build_dashboard_stats(raw)

        self.assertEqual(10, len(stats['top_heat_points']))
        self.assertEqual(120000, stats['top_heat_points'][0]['heat_value'])
        self.assertEqual(30000, stats['top_heat_points'][-1]['heat_value'])


if __name__ == '__main__':
    unittest.main()
