from flask import Flask, jsonify, request
from functools import wraps
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from decouple import config
import time

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


@app.route('/listAllEventsFromCalendar', methods=['POST'])
@gapi_auth_required
def list_all_events_from_calendar():
    body = request.get_json()
    events = gc.list_calendar_events(
        calendar_id=body['calendarId'], num_days=body['numDays'])
    return jsonify(events), 200


@app.route('/numEventsToNotion', methods=['POST'])
@gapi_auth_required
def num_events_to_notion():
    body = request.get_json()
    print(f"Received request, processing {body['calendarId']}")
    user_info = nc.get_user_info(calendar_id=body['calendarId'])

    if not user_info:
        return 'User not registered cannot continue', 500

    # try:
    scenarios = nc.get_scenarios_table()
    events = gc.list_calendar_events(
        calendar_id=body['calendarId'], num_days=body['numDays'])
    for event in events:
        time.sleep(3)
        num_attendees = event.get('attendees', [])
        sub_event = {
            'event_title': event.get('summary'),
            'event_location': event.get('location', 'N/A'),
            'event_participants': len(num_attendees),
            'event_time': 'N/A',
            'event_duration': 'N/A'
        }

        (principle_scenario_pairs_df, openai_predictions) = ml_client.gpt3_find_matching_scenarios(
            sub_event, scenarios)
        principles_request_list = principle_scenario_pairs_df["principles"].tolist(
        )
        print(f'principles_request_list: {principles_request_list}')
        principles_df = nc.get_principles_from_list(principles_request_list)
        print(principles_df)
        event_body = ml_client.format_principles(
            principles_df, principle_scenario_pairs_df)

        newEvent = {
            'calendar_id': body['calendarId'],
            'user_name': user_info['name'],
            'user_email': user_info['email'],
            'event_id': event.get('id'),
            'location': event.get('location', ''),
            'event_name': event.get('summary'),
            'event_description': event.get('description', ''),
            'openai_predictions': openai_predictions,
            'principles': event_body,
        }
        if nc.create_page(newEvent):
            print(f"Added {newEvent['event_name']} to notion")
        else:
            print(f"Could not add {newEvent['event_name']} to notion")
    return 'Events successfully created', 200
# except:
    # return 'Server error', 500


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
    print(gc.list_calendar_events(
        calendar_id="openprinciples@gmail.com", num_days=1))
    '''
    scenarios_df = nc.get_scenarios_table()
    event = {
        "event_title": "Effective Altruism Social event",
        "event_location": "N/A",
        "event_participants": "N/A",
        "event_time": "2021, Sep 25, 9pm",
        "event_duration": "N/A"
    }

    principle_scenario_pairs_df = ml_client.gpt3_find_matching_scenarios(
        event, scenarios_df)
    principles_request_list = principle_scenario_pairs_df["principles"].tolist(
    )
    print(f'principles_request_list: {principles_request_list}')
    principles_df = nc.get_principles_from_list(principles_request_list)
    print(principles_df)
    event_body = ml_client.format_principles(
        principles_df, principle_scenario_pairs_df)
    print(f'event_body: {event_body}')
    '''

    return 'nice', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # run our Flask app
