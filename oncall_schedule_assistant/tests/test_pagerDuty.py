import pytz
import datetime
from unittest import mock
from unittest import TestCase
from pagerduty import PagerDutySchedule


class TestPagerDuty(TestCase):
    def setUp(self):
        with mock.patch.object(PagerDutySchedule, "__init__", lambda x, y, z: None):
            self.pd = PagerDutySchedule(None, 'Europe/London')
            self.pd.token = 'TOKEN'
            self.pd.schedule_id = None
            self.pd.timezone = pytz.timezone('Europe/London')
            self.pd.api_url = 'https://api.pagerduty.com'
            self.pd.api_version = 2

    @mock.patch('requests.Session')
    def test__pagerduty_session_get(self, session_mock):
        class FakeResponse(object):
            status_code = 200
            content = 'response'

        fake_response = FakeResponse()
        session_mock.return_value.get.return_value = fake_response

        url = 'some_url'
        options = 'some_options'
        response = self.pd._pagerduty_session_get(url, options)

        self.assertEqual(response.status_code, fake_response.status_code)
        self.assertEqual(response.content, fake_response.content)


    def test__convert_timestamp(self):
        timestamp = '2018-06-27T18:00:00+01:00'
        expected_out = '2018-06-27T18:00:00+0100'
        response = self.pd._convert_timestamp(timestamp)

        self.assertEquals(response, expected_out)

    @mock.patch('pagerduty.datetime')
    def test__return_next_shift(self, mock_datetime):
        overrides = {
            'total': 1, 'overrides': [
                {'start': '2018-05-20T18:00:00+01:00',
                 'end': '2018-05-22T18:00:00+01:00',
                 'user': {
                     'id': 'UUUUUU',
                     'type': 'user_reference',
                     'summary': 'User Name'}
                 }
            ]
        }

        mocked_today = datetime.datetime(2018, 5, 15, tzinfo=pytz.utc)
        mock_datetime.now.return_value = mocked_today
        timestamp_list = ['2018-05-20T18:00:00+0100', '2018-05-25T18:00:00+0100', '2018-05-26T18:00:00+0100']
        expected_out = ('User Name', '2018-05-20T18:00:00+01:00', '2018-05-22T18:00:00+01:00')
        response = self.pd._return_next_shift(overrides, timestamp_list)

        self.assertEquals(response, expected_out)


    @mock.patch('pagerduty.PagerDutySchedule._pagerduty_session_get')
    def test__pd_schedule_pull(self, mock_session_get):
        expected_out = {'total': 1, 'overrides': [{'start': 'time', 'end': 'time'}]}
        mock_session_get.return_value.json.return_value = expected_out
        response = self.pd._pd_schedule_pull(1, 'users')

        self.assertEqual(response, expected_out)

    @mock.patch('pagerduty.PagerDutySchedule._pagerduty_session_get')
    def test_set_schedule(self, mock_session_get):
        expected_out = 'XXXXXXX'
        mock_session_get.return_value.json.return_value = {
            'schedules': [
                {'id': 'XXXXXXX',
                 'type': 'schedule',
                 'summary': 'Test Schedule'
                 }
            ]
        }

        self.pd.set_schedule('Test Schedule')
        self.assertEqual(self.pd.schedule_id, expected_out)

    @mock.patch('pagerduty.PagerDutySchedule._pd_schedule_pull')
    def test_who_is_on_call_now(self, mock_pd_schedule_pull):
        expected_out = 'Linus Torvalds'
        mock_pd_schedule_pull.return_value = {'users': [{'name': 'Linus Torvalds'}]}
        response = self.pd.who_is_on_call_now()

        self.assertEqual(response, expected_out)

    @mock.patch('pagerduty.PagerDutySchedule._pd_schedule_pull')
    @mock.patch('pagerduty.PagerDutySchedule._convert_timestamp')
    @mock.patch('pagerduty.PagerDutySchedule._return_next_shift')
    def test_next_on_call(self, mock_next_shift, mock_convert_ts, mock_schedule_pull):
        expected_out = ('Linus Torvalds', '2018-05-20T18:00:00+01:00', '2018-05-22T18:00:00+01:00')
        mock_schedule_pull.return_value = {
            'total': 1, 'overrides': [
                {'start': '2018-05-20T18:00:00+01:00',
                 'end': '2018-05-22T18:00:00+01:00',
                 'user': {'summary': 'Linus Torvalds'}
                 }
            ]
        }

        mock_convert_ts.return_value = '2018-05-20T18:00:00+0100'
        mock_next_shift.return_value = ('Linus Torvalds', '2018-05-20T18:00:00+01:00', '2018-05-22T18:00:00+01:00')
        response = self.pd.next_on_call()

        self.assertEqual(response, expected_out)

    @mock.patch('pagerduty.PagerDutySchedule._pd_schedule_pull')
    @mock.patch('pagerduty.PagerDutySchedule._convert_timestamp')
    @mock.patch('pagerduty.PagerDutySchedule._return_next_shift')
    def test_when_is_on_call(self, mock_next_shift, mock_convert_ts, mock_schedule_pull):
        expected_out = ('Bill Gates', '2018-05-25T18:00:00+01:00', '2018-05-30T18:00:00+01:00')
        mock_schedule_pull.return_value = {
            'total': 24, 'overrides': [
                {'start': '2018-05-20T18:00:00+01:00',
                 'end': '2018-05-25T18:00:00+01:00',
                 'user': {'summary': 'Linus Torvalds'}
                 },
                {'start': '2018-05-25T18:00:00+01:00',
                 'end': '2018-05-30T18:00:00+01:00',
                 'user': {'summary': 'Bill Gates'}
                 }
            ]
        }

        mock_convert_ts.return_value = '2018-05-20T18:00:00+0100'
        mock_next_shift.return_value = ('Bill Gates', '2018-05-25T18:00:00+01:00', '2018-05-30T18:00:00+01:00')
        response = self.pd.when_is_on_call('Bill Gates')

        self.assertEqual(response, expected_out)

    @mock.patch('pagerduty.PagerDutySchedule._pagerduty_session_get')
    def test_lookup_user_name(self, mock_session_get):
        expected_out = ('XXXXXXX', 'Linus Torvalds')
        mock_session_get.return_value.json.return_value = {'users': [{'name': 'Linus Torvalds', 'id': 'XXXXXXX'}]}

        response = self.pd.lookup_user_name('Linus Torvalds')
        self.assertEqual(response, expected_out)
