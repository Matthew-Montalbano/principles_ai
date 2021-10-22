import requests as r
import json
from decouple import config
import pandas as pd


def notionPropertiesToObject(p):
    return {
        'page_id': p['id'],
        'event_id': p['properties']['Event ID']['title'][0]['plain_text'],
        'event_name': p['properties']['Event Name']['rich_text'][0]['plain_text'],
        'principles': p['properties']['Principles Handpicked']['rich_text'][0]['plain_text']
    }


NOTION_SCENARIOS = config('NOTION_SCENARIOS')
NOTION_PRINCIPLES = config('NOTION_PRINCIPLES')


class NotionClient:
    def __init__(self, notion_key, notion_db):
        self.notion_db = notion_db
        self.notion_key = notion_key
        self.headers = {
            'Authorization': 'Bearer ' + self.notion_key,
            'Content-Type': 'application/json',
            'Notion-Version': '2021-08-16'
        }

    def get_user_info(self, calendar_id):
        data = {
            'filter': {
                'property': 'calendarId',
                'text': {
                    'equals': calendar_id
                }
            }
        }
        res = r.post('https://api.notion.com/v1/databases/f14457c2d77b488d8d379c637cce6e76/query',
                     data=json.dumps(data), headers=self.headers)

        results = json.loads(res.text)['results']
        if not len(results) > 0:
            return None
        results = results[0]['properties']

        return {
            'email': results['Your Email']['title'][0]['plain_text'],
            'name': results['Your Name']['rich_text'][0]['plain_text'],
        }

    def create_page(self, event):
        print(f"Adding {event.get('event_name')} to Notion")
        print(event)
        new_page = {
            'parent': {
                'database_id': self.notion_db
            },
            'properties': {
                'Event ID': {
                    'title': [
                        {'text': {'content': event.get('event_id')}}
                    ]
                },
                'User Email': {
                    'email': event.get('user_email')
                },
                'User Name': {
                    'rich_text': [
                        {'text': {'content': event.get('user_name')}}
                    ]
                },
                'Event Name': {
                    'rich_text': [
                        {'text': {'content': event.get('event_name')}}
                    ]
                },
                'calendarId': {
                    'rich_text': [
                        {'text': {'content': event.get('calendar_id')}}
                    ]
                },
                'Event Description': {
                    'rich_text': [
                        {'text': {'content': event.get('event_description')}}
                    ]
                },
                'Location': {
                    'rich_text': [
                        {'text': {'content': event.get('location')}}
                    ]
                },
                'principlesAiPicked': {
                    'rich_text': [
                        {'text': {'content': '\n'.join(
                            event.get('principles'))}}
                    ]
                },
                'Principles Handpicked': {
                    'rich_text': [
                        {'text': {'content': '\n---\n'.join(
                            event.get('principles'))}}
                    ]
                },
                'openAiPredictions': {
                    'rich_text': [
                        {'text': {'content':
                                  event.get('openai_predictions')}}
                    ]
                },
                'Added?': {
                    'checkbox': False
                }
            },
            'children': []
        }
        res = r.post('https://api.notion.com/v1/pages',
                     data=json.dumps(new_page), headers=self.headers)
        print(res.text)
        if res.status_code == 200:
            return True
        else:
            return False

    def update_page(self, page_id, properties):
        res = r.patch(f"https://api.notion.com/v1/pages/{page_id}", data=json.dumps(
            {'properties': properties}), headers=self.headers)
        if res.status_code == 200:
            return True
        else:
            return False

    def get_all_unadded_events_for_calendar(self, calendar_id):
        # returns no more than 100 for now (can extend as needed)
        data = {
            'filter': {
                'and': [
                    {'property': 'Added?', 'checkbox': {'equals': False}},
                    {'property': 'calendarId', 'text': {
                        'equals': calendar_id}}
                ]
            }
        }

        res = r.post(
            f"https://api.notion.com/v1/databases/{self.notion_db}/query", data=json.dumps(data), headers=self.headers)

        if res.status_code == 200:
            results = json.loads(res.text)['results']
            return list(map(lambda e: notionPropertiesToObject(e), results))
        else:
            return None

    def get_scenarios_table(self):
        res = r.post(
            f"https://api.notion.com/v1/databases/{NOTION_SCENARIOS}/query", headers=self.headers)
        results = json.loads(res.text)['results']

        new_obj = {
            'scenarios_human': [],
            'scenarios': [],
            'tags': [],
            'principles': [],
        }

        for result in results:
            props = result['properties']
            new_obj['scenarios_human'].append(props.get('Scenario').get(
                'title')[0].get('plain_text'))
            new_obj['scenarios'].append(
                props.get('Scenario Classification').get('rich_text')[0].get('plain_text'))
            new_obj['tags'].append(
                list(map(lambda x: x.get('name'), props.get('Tags').get('multi_select'))))
            new_obj['principles'].append(
                list(map(lambda x: x.get('id'), props.get('Principles').get('relation'))))

        return pd.DataFrame(new_obj)

    def get_principles_from_list(self, principles):
        source_cache = {}

        new_obj = {
            'principle': [],
            'source': [],
            'notes': [],
            'id': []
        }

        for principle in principles:
            props = json.loads(r.get(
                f"https://api.notion.com/v1/pages/{principle}", headers=self.headers).text).get('properties')
            new_obj['id'].append(principle)
            new_obj['principle'].append(
                props.get('Principle (Work/Life Principles, Best Practices)').get('title')[0].get('plain_text'))
            if (len(props.get('Notes (detailed action items)').get(
                    'rich_text')) > 0):
                new_obj['notes'].append(props.get('Notes (detailed action items)').get(
                    'rich_text')[0].get('plain_text'))
            else:
                new_obj['notes'].append('')

            if (len(props.get('Sources').get('relation')) > 0):
                for source in props.get('Sources').get('relation'):
                    source_id = source.get('id')
                    if source_id in source_cache:
                        new_obj['source'].append(source_cache.get(source_id))
                    else:
                        new_source = json.loads(
                            r.get(f"https://api.notion.com/v1/pages/{source_id}", headers=self.headers).text).get('properties').get('Name, Author').get('title')[0].get('plain_text')
                        new_obj['source'].append(new_source)
                        source_cache[source_id] = new_source
            else:
                new_obj['source'].append('')

        return pd.DataFrame(new_obj)
