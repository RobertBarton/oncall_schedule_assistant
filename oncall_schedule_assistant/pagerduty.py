import requests
import re
import pytz
from datetime import datetime, timedelta


class PagerDutySchedule(object):
    """
    PagerDuty Connection Object

    Example:
        pd = PagerDuty(pd_token, timezone)
    Attributes:
        token: str, The API auth token required to connect to PagerDuty (Write enabled)
    """
    def __init__(self, token, timezone):
        self.api_url = 'https://api.pagerduty.com'
        self.api_version = 2
        self.schedule_id = None
        self.schedule_name = None
        self.timezone = pytz.timezone(timezone)
        self.token = token

    def _pagerduty_session_get(self, url, options):
        """
        Internal Method that handles PD API requests
        :param url: Url body after base url, e.g. schedules or users
        :type url: str
        :param options: Options to be used in the API request e.g. ?since=ts&until=ts or ?query=<search string>
        :type options: str
        :return: requests object
        :rtype: object
        """
        pagerduty_session = requests.Session()
        pagerduty_session.headers.update({
            'Authorization': 'Token token={}'.format(self.token),
            'Accept': 'application/vnd.pagerduty+json;version={}'.format(self.api_version)
        })

        response = pagerduty_session.get('{}/{}{}'.format(self.api_url, url, options))

        if response.status_code == 404:
            raise Exception('PagerDuty API not found')
        elif response.status_code == 401:
            raise Exception('Authentication to PagerDuty Failed')

        return response

    @staticmethod
    def _convert_timestamp(timestamp):
        """
        Parses Timestamp from PagerDuty API for pythonic consumption
        :param timestamp:
        :type timestamp: str
        :return: datetime timestamp, format: '%Y-%m-%dT%H:%M:%S%z'
        :rtype: datetime
        """
        extract_time = re.match('(.*?\+\d{2}):(.*)', timestamp)
        formated = datetime.strptime('{}{}'.format(extract_time.group(1), extract_time.group(2)),
                                     '%Y-%m-%dT%H:%M:%S%z').strftime('%Y-%m-%dT%H:%M:%S%z')
        return formated

    def _return_next_shift(self, overrides, timestamp_list):
        """
        Given the Overrides and the target timestamps, return the on call engineer, and their shift start
        and end timestamps
        :param overrides: requests return json object from the PD Overides API call
        :type overrides: dict
        :param timestamp_list: List of timestamps extracted
        :type timestamp_list: list
        :return: Engineer Name, datetime format shift start, datetime format shift end
        :rtype: tuple
        """
        # Ensure we get the right one, even if not in order
        now = datetime.now(tz=self.timezone).strftime('%Y-%m-%dT%H:%M:%S%z')
        next_shift_start = min(ts for ts in timestamp_list if ts > now)
        convert = re.match('(.*?\+\d{2})(.*)', next_shift_start)
        rebuild_ts = '{}:{}'.format(convert.group(1), convert.group(2))

        for override in overrides['overrides']:
            if override['start'] == rebuild_ts:
                return override['user']['summary'], override['start'], override['end']

        return None, None, None

    def _pd_schedule_pull(self, minutes, lookup):
        """
        Pull schedule data over the PagerDuty API
        :param minutes: number of minutes to include in lookup
        :type minutes: int
        :param lookup: what to lookup e.g. users, overrides
        :type lookup: str
        :return: Schedule Data
        :rtype: dict
        """
        time_since = datetime.now(tz=self.timezone)
        time_until = time_since + timedelta(minutes=minutes)
        time_since = time_since.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        time_until = time_until.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        url = 'schedules/{}/{}'.format(self.schedule_id, lookup)
        options = '?since={}&until={}'.format(time_since, time_until)
        response = self._pagerduty_session_get(url, options).json()

        return response

    def set_schedule(self, schedule_name):
        """
        Bakes the schedule ID into the object
        :param schedule_name: The name of the schedule
        :type schedule_name: str
        """
        url = 'schedules'
        options = '?query={}'.format(schedule_name.replace(' ', '%'))
        schedule_definition = self._pagerduty_session_get(url, options).json()

        if len(schedule_definition['schedules']) == 0:
            raise Exception('Schedule "{}" not found'.format(schedule))

        self.schedule_id = schedule_definition['schedules'][0]['id']

    def who_is_on_call_now(self):
        """
        This method returns the name of the engineer currently on call
        :return: Engineer name and shift time
        :rtype: str
        """
        response = self._pd_schedule_pull(1, 'users')

        if len(response['users']) == 0:
            return None

        return response['users'][0]['name']


    def next_on_call(self):
        """
        this method returns either the name of the next on call engineer, or the named engineers next shift.
        :param name: Given Engineer's name
        :type name: str
        :return: Engineer name, shift start datetime '%Y-%m-%dT%H:%M:%S%z', shift end datetime '%Y-%m-%dT%H:%M:%S%z'
        :rtype: tuple
        """
        response = self._pd_schedule_pull(144000, 'overrides')

        shift_starts = []
        for override in response['overrides']:
            format_time = self._convert_timestamp(override['start'])
            shift_starts.append(format_time)

        return self._return_next_shift(response, shift_starts)


    def when_is_on_call(self, engineer_name):
        """
        this method returns either the name of the next on call engineer, or the named engineers next shift.
        :param engineer_name: Given Engineer's name
        :type engineer_name: str
        :return: Engineer name, shift start datetime '%Y-%m-%dT%H:%M:%S%z', shift end datetime '%Y-%m-%dT%H:%M:%S%z'
        :rtype: tuple
        """
        response = self._pd_schedule_pull(144000, 'overrides')

        shift_starts = []
        for override in response['overrides']:
            if override['user']['summary'] == engineer_name:
                format_time = self._convert_timestamp(override['start'])
                shift_starts.append(format_time)

        if len(shift_starts) == 0:
            return None, None, None

        return self._return_next_shift(response, shift_starts)


    def lookup_user_name(self, user_email):
        """
        Given a user's email, fetch the associated username and user id from pagerduty
        :param user_email: The email address of a user
        :return: The user id, user name
        :rtype: tuple
        """

        url = 'users'
        options = '?query={}'.format(user_email.lower())
        response = self._pagerduty_session_get(url, options).json()

        if len(response['users'][0]) == 0:
            return None, None

        return response['users'][0]['id'], response['users'][0]['name']
