from flask import Flask, jsonify, request
from functools import wraps
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from decouple import config

from utils import SCOPES
from nlp import UpNlpClient
from gapi_calendar import GapiCalendarClient
from notion_client import NotionClient

app = Flask(__name__)
ml_client = UpNlpClient('principles.csv')
gc = GapiCalendarClient()
nc = NotionClient(notion_key=config('NOTION_KEY'),
                  notion_db=config('NOTION_MAIN_DB'))
flow = None

if not gc.has_creds():
    flow = Flow.from_client_secrets_file(
        './auth/desktop-google-oauth.json',
        scopes=SCOPES,
        redirect_uri='postmessage',
    )


def gapi_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not gc.has_creds():
            return 'Need to authenticate GAPI first', 401
        return f(*args, **kwargs)
    return decorated_function

# client facing function


@app.route('/principleFromEvent', methods=['GET', 'POST'])
def principle_from_event():
    if request.method == 'GET':
        return jsonify({'hello': "world"}), 200
    else:
        body = request.json
        # there's also a body['userId']
        events = body['events']
        print(events)
        return jsonify({'allPrinciples': list(map(lambda event: {'event': event, 'principles': ml_client.find_principles(event)}, events))}), 200


@app.route('/createGoogleCredentialsFromCode', methods=['POST'])
def create_google_credentials_from_code():
    body = request.get_json()
    flow.fetch_token(code=body['code'])
    if gc.setCredentials(flow.credentials) and gc.has_creds():
        return 'Credentials created', 200
    else:
        return 'Error', 500


@app.route('/listAllCalendars', methods=['GET'])
@gapi_auth_required
def list_all_calendars():
    return jsonify(gc.list_all_calendars()), 200


@app.route('/numEventsToNotion', methods=['POST'])
@gapi_auth_required
def num_events_to_notion():
    body = request.get_json()
    user_info = nc.get_user_info(calendar_id=body['calendarId'])

    if not user_info:
        return 'User not registered cannot continue', 500

    try:
        scenarios = nc.get_scenarios_table()
        events = gc.list_calendar_events(
            calendar_id=body['calendarId'], num_days=body['numDays'])
        for event in events:

            sub_event = {
                'event_title': event.get('summary'),
                'event_location': event.get('location', 'N/A'),
                'event_participants': 'N/A',
                'event_time': 'N/A',
                'event_duration': 'N/A'
            }

            # something like 'principles': ml_client.function_name(sub_event, scenarios)

            newEvent = {
                'calendar_id': body['calendarId'],
                'user_name': user_info['name'],
                'user_email': user_info['email'],
                'event_id': event.get('id'),
                'location': event.get('location', ''),
                'event_name': event.get('summary'),
                'event_description': event.get('description', ''),
                'principles': ml_client.find_principles(event.get('summary', [])),
            }
            if nc.create_page(newEvent):
                print(f"Added {newEvent['event_name']} to notion")
            else:
                print(f"Could not add {newEvent['event_name']} to notion")
        return 'Events successfully created', 200
    except:
        return 'Server error', 500


@app.route('/allUnaddedNotionEventsToCalendar', methods=['POST'])
@gapi_auth_required
def notion_events_to_calendar():
    calendar_id = request.get_json()['calendarId']
    events = nc.get_all_unadded_events_for_calendar(calendar_id)
    for event in events:
        base_event = gc.get_event(
            calendar_id, event['event_id'])
        new_event = {
            'summary': 'Ultrabrain reminder',
            'description': f"Your event: {event['event_name']}\nOur recommendations:\n{event['principles']}",
            'start': base_event['start'],
            'end': base_event['end'],
            'reminders': base_event['reminders']
        }
        gcal_event = gc.insert_event(
            calendar_id=calendar_id, event=new_event)
        if (gcal_event.get('htmlLink')):
            if (not nc.update_page(event['page_id'], {'Added?': {'checkbox': True}})):
                raise Exception
    return 'Done', 200


@app.route('/testNotion', methods=['GET'])
def test_notion():
    print(nc.get_scenarios_table())
    print(nc.get_principles_from_list(
        ['26d47288c7df43eea32bea38e8fa87b2', '8e3ee338b4eb40f29f76f61146c44fbc']))
    return 'nice', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # run our Flask app
