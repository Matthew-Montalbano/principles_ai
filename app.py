from flask import Flask, jsonify, request, redirect, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from functools import wraps
from google_auth_oauthlib.flow import Flow
from decouple import config
import time
import requests
import json
import os
from oauthlib.oauth2 import WebApplicationClient

from user import User
from utils.globals import SCOPES
from utils.nlp import UpNlpClient
from utils.gapi_calendar import GapiCalendarClient
from utils.notion_client import NotionClient

app = Flask(__name__)
app.secret_key = config("FLASK_SECRET_KEY") or os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)

web_client = WebApplicationClient(config("GOOGLE_CLIENT_ID"))

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

ml_client = UpNlpClient("principles.csv")
nc = NotionClient(notion_key=config("NOTION_KEY"), notion_db=config("NOTION_MAIN_DB"))

gc = GapiCalendarClient()
flow = None
if not gc.has_creds():
    flow = Flow.from_client_secrets_file(
        "./auth/desktop-google-oauth.json",
        scopes=SCOPES,
        redirect_uri="postmessage",
    )

def gapi_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not gc.has_creds():
            return "Need to authenticate GAPI first", 401
        return f(*args, **kwargs)

    return decorated_function


@app.route("/principleFromEvent", methods=["GET", "POST"])
def principle_from_event():
    if request.method == "GET":
        return jsonify({"hello": "world"}), 200
    else:
        body = request.json
        # there's also a body['userId']
        events = body["events"]
        print(events)
        return (
            jsonify(
                {
                    "allPrinciples": list(
                        map(
                            lambda event: {
                                "event": event,
                                "principles": ml_client.find_principles(event),
                            },
                            events,
                        )
                    )
                }
            ),
            200,
        )


@app.route("/createGoogleCredentialsFromCode", methods=["POST"])
def create_google_credentials_from_code():
    body = request.get_json()
    flow.fetch_token(code=body["code"])
    if gc.setCredentials(flow.credentials) and gc.has_creds():
        return "Credentials created", 200
    else:
        return "Error", 500


@app.route("/listAllCalendars", methods=["GET"])
@gapi_auth_required
def list_all_calendars():
    return jsonify(gc.list_all_calendars()), 200


@app.route("/listAllEventsFromCalendar", methods=["POST"])
@gapi_auth_required
def list_all_events_from_calendar():
    body = request.get_json()
    events = gc.list_calendar_events(
        calendar_id=body["calendarId"], num_days=body["numDays"]
    )
    return jsonify(events), 200


@app.route("/numEventsToNotion", methods=["POST"])
@gapi_auth_required
def num_events_to_notion():
    body = request.get_json()
    print(f"Received request, processing {body['calendarId']}")
    
    #getting user information from https://www.notion.so/openprinciples/f14457c2d77b488d8d379c637cce6e76?v=1296c84bbe43498d9edb5fdd7697952d
    #a user needs a valid calendarId to continue
    user_info = nc.get_user_info(calendar_id=body["calendarId"])

    if not user_info:
        return "User not registered cannot continue", 500

    
    scenarios = nc.get_scenarios_table()
    events = gc.list_calendar_events(
        calendar_id=body["calendarId"], num_days=body["numDays"]
    )
    for event in events:
        time.sleep(3) #avoids hitting OpenAi rate limit
        num_attendees = event.get("attendees", [])
        sub_event = {
            "event_title": event.get("summary"),
            "event_location": event.get("location", "N/A"),
            "event_participants": len(num_attendees),
            "event_time": "N/A",
            "event_duration": "N/A",
        }

        (
            principle_scenario_pairs_df,
            openai_predictions,
        ) = ml_client.gpt3_find_matching_scenarios(sub_event, scenarios)
        principles_request_list = principle_scenario_pairs_df["principles"].tolist()
        print(f"principles_request_list: {principles_request_list}")
        principles_df = nc.get_principles_from_list(principles_request_list)
        print(principles_df)
        event_body = ml_client.format_principles(
            principles_df, principle_scenario_pairs_df
        )

        newEvent = {
            "calendar_id": body["calendarId"],
            "user_name": user_info["name"],
            "user_email": user_info["email"],
            "event_id": event.get("id"),
            "location": event.get("location", ""),
            "event_name": event.get("summary"),
            "event_description": event.get("description", ""),
            "openai_predictions": openai_predictions,
            "principles": event_body,
        }
        if nc.create_page(newEvent):
            print(f"Added {newEvent['event_name']} to notion")
        else:
            print(f"Could not add {newEvent['event_name']} to notion")
    return "Events successfully created", 200


@app.route("/allUnaddedNotionEventsToCalendar", methods=["POST"])
@gapi_auth_required
def notion_events_to_calendar():
    calendar_id = request.get_json()["calendarId"]
    print(f"Received request, processing {calendar_id}")
    events = nc.get_all_unadded_events_for_calendar(calendar_id)
    for event in events:
        base_event = gc.get_event(calendar_id, event["event_id"])
        new_event = {
            "summary": "Ultrabrain reminder",
            "description": f"Your event: {event['event_name']}\nOur recommendations:\n{event['principles']}",
            "start": base_event["start"],
            "end": base_event["end"],
            "reminders": base_event["reminders"],
        }
        gcal_event = gc.insert_event(calendar_id=calendar_id, event=new_event)
        if gcal_event.get("htmlLink"):
            if not nc.update_page(event["page_id"], {"Added?": {"checkbox": True}}):
                raise Exception
    return "Done", 200

@app.route("/")
def index():
    print(current_user)
    if current_user.is_authenticated:
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<a class="button" href="/logout">Logout</a>'.format(
                current_user.name, current_user.email
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'


@app.route("/login")
def login():
    auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    request_uri = web_client.prepare_request_uri(
        auth_endpoint, redirect_uri=request.base_url + "/callback", scope=SCOPES
    )
    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    code = request.args.get("code")
    token_endpoint = "https://oauth2.googleapis.com/token"

    token_url, headers, body = web_client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(config("GOOGLE_CLIENT_ID"), config("GOOGLE_CLIENT_SECRET")),
    )
    web_client.parse_request_body_response(json.dumps(token_response.json()))

    uri, headers, body = web_client.add_token(
        "https://openidconnect.googleapis.com/v1/userinfo"
    )
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400
    user = User(id_=unique_id, name=users_name, email=users_email)

    login_user(user)
    return redirect(url_for("index"))



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, ssl_context=("./server_keys/cert.pem", "./server_keys/key.pem"))
