import json
import os
import tempfile
import unittest

from visualize import build_index


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


if __name__ == '__main__':
    unittest.main()
