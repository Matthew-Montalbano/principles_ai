from flask import Flask, jsonify, request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import datetime
from pymongo import MongoClient
from decouple import config

from nlp import UpNlpClient
from security import SecurityClient

app = Flask(__name__)

flow = Flow.from_client_secrets_file(
    './auth/desktop-google-oauth.json',
    scopes=['https://www.googleapis.com/auth/calendar.app.created', 'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email', 'openid', 'https://www.googleapis.com/auth/calendar.events'],
    redirect_uri='postmessage',
)

ml_client = UpNlpClient('principles.csv')
db_client = MongoClient(port=27017)
db = db_client.admin.up_database_test

result = db.insert_one({'user': 'h.tony.deng@gmail.com', 'code': 'cododooo'})
print(result)

crypt = SecurityClient(config('SECRET_KEY'), config('SECRET_PASSWORD'))
print(crypt.encryptPayload({'hello': 'world'}))


@app.route('/principleFromEvent', methods=['GET', 'POST'])
def principle_from_event():
    if request.method == 'GET':
        return jsonify({'hello': "world"}), 200
    else:
        body = request.json
        event = body['event']
        return jsonify({'event': event, 'principles': ml_client.find_principles(event)}), 200


@app.route('/verifyGoogleAuthCode', methods=['POST'])
def verify_google_auth_code():
    body = request.get_json()
    print(f'Request body {body}')
    flow.fetch_token(code=body['code'])
    print(f'Creds {flow.credentials}')

    service = build('calendar', 'v3', credentials=flow.credentials)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])

    return '', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # run our Flask app
