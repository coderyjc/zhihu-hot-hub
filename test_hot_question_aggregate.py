import json
import os
import tempfile
import unittest

import hot_question_aggregate as aggregate


def make_item(card_id='Q_1', title='问题一', url='https://www.zhihu.com/question/1',
              heat='606 万热度'):
    return {
        'card_id': card_id,
        'target': {
            'title_area': {'text': title},
            'link': {'url': url},
            'metrics_area': {'text': heat},
        },
    }


class HotQuestionAggregateTest(unittest.TestCase):

    def test_first_collection_creates_v2_aggregate(self):
        daily = aggregate.create_aggregate('daily', '2026-07-10 10:00:00 +0800', '2026-07-10')

        aggregate.upsert_items(
            daily,
            [make_item('Q_1'), make_item('Q_2', '问题二', 'https://www.zhihu.com/question/2', '10 万热度')],
            '2026-07-10 10:00:00 +0800',
        )

        self.assertEqual(2, daily['version'])
        self.assertEqual('daily', daily['scope'])
        self.assertEqual('2026-07-10', daily['date'])
        self.assertEqual(2, len(daily['items']))
        self.assertEqual(6060000, daily['items'][0]['latest_heat_value'])

    def test_new_hot_item_is_appended(self):
        daily = aggregate.create_aggregate('daily', '2026-07-10 10:00:00 +0800', '2026-07-10')
        aggregate.upsert_items(daily, [make_item('Q_1')], '2026-07-10 10:00:00 +0800')

        aggregate.upsert_items(
            daily,
            [make_item('Q_1', heat='700 万热度'), make_item('Q_2', '问题二', 'https://www.zhihu.com/question/2')],
            '2026-07-10 13:00:00 +0800',
        )

        self.assertEqual(['Q_1', 'Q_2'], [item['key'] for item in daily['items']])

    def test_existing_hot_item_appends_history_only(self):
        daily = aggregate.create_aggregate('daily', '2026-07-10 10:00:00 +0800', '2026-07-10')
        aggregate.upsert_items(daily, [make_item('Q_1', heat='606 万热度')], '2026-07-10 10:00:00 +0800')

        aggregate.upsert_items(daily, [make_item('Q_1', heat='700 万热度')], '2026-07-10 13:00:00 +0800')

        self.assertEqual(1, len(daily['items']))
        self.assertEqual(2, len(daily['items'][0]['history']))
        self.assertEqual('700 万热度', daily['items'][0]['latest_heat_text'])

    def test_same_observed_at_updates_last_history_point(self):
        daily = aggregate.create_aggregate('daily', '2026-07-10 10:00:00 +0800', '2026-07-10')
        observed_at = '2026-07-10 10:00:00 +0800'

        aggregate.upsert_items(daily, [make_item('Q_1', heat='606 万热度')], observed_at)
        aggregate.upsert_items(daily, [make_item('Q_1', heat='700 万热度')], observed_at)

        self.assertEqual(1, len(daily['items'][0]['history']))
        self.assertEqual('700 万热度', daily['items'][0]['history'][0]['heat_text'])

    def test_parse_heat_value(self):
        self.assertEqual(6060000, aggregate.parse_heat_value('606 万热度'))
        self.assertEqual(120000000, aggregate.parse_heat_value('1.2 亿热度'))
        self.assertEqual(1234, aggregate.parse_heat_value('1234 热度'))
        self.assertIsNone(aggregate.parse_heat_value('热度未知'))

    def test_legacy_data_format_is_converted(self):
        legacy = {'data': [make_item('Q_1', heat='606 万热度')]}

        daily = aggregate.normalize_aggregate(
            legacy,
            scope='daily',
            updated_at='2026-07-10 13:00:00 +0800',
            date='2026-07-10',
            legacy_observed_at='2026-07-10 00:00:00 +0800',
        )

        self.assertEqual(2, daily['version'])
        self.assertEqual(1, len(daily['items']))
        self.assertTrue(daily['items'][0]['history'][0]['legacy_import'])

    def test_converted_legacy_data_can_continue_merging(self):
        legacy = {'data': [make_item('Q_1', heat='606 万热度')]}
        daily = aggregate.normalize_aggregate(
            legacy,
            scope='daily',
            updated_at='2026-07-10 13:00:00 +0800',
            date='2026-07-10',
            legacy_observed_at='2026-07-10 00:00:00 +0800',
        )

        aggregate.upsert_items(
            daily,
            [make_item('Q_1', heat='700 万热度')],
            '2026-07-10 13:00:00 +0800',
        )

        self.assertEqual(1, len(daily['items']))
        self.assertEqual(2, len(daily['items'][0]['history']))
        self.assertEqual('700 万热度', daily['items'][0]['latest_heat_text'])

    def test_load_missing_file_returns_empty_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = os.path.join(tmp, 'missing.json')
            daily = aggregate.load_aggregate_file(
                file,
                scope='daily',
                date='2026-07-10',
                updated_at='2026-07-10 13:00:00 +0800',
            )

        self.assertEqual(2, daily['version'])
        self.assertEqual([], daily['items'])

    def test_load_legacy_file_converts_to_v2(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = os.path.join(tmp, 'legacy.json')
            with open(file, mode='w', encoding='utf-8') as f:
                json.dump({'data': [make_item('Q_1')]}, f, ensure_ascii=False)

            daily = aggregate.load_aggregate_file(
                file,
                scope='daily',
                date='2026-07-10',
                updated_at='2026-07-10 13:00:00 +0800',
                legacy_observed_at='2026-07-10 00:00:00 +0800',
            )

        self.assertEqual(1, len(daily['items']))
        self.assertTrue(daily['items'][0]['history'][0]['legacy_import'])


if __name__ == '__main__':
    unittest.main()
