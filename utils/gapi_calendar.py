from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from utils.globals import SCOPES
import os.path
import datetime

TOKENFILE = "./auth/gapi_calendar_token.json"


class GapiCalendarClient:
    def __init__(self):
        self.creds = None
        self.service = None
        self.check_offline_creds()

    def check_offline_creds(self):
        if os.path.exists(TOKENFILE):
            self.creds = Credentials.from_authorized_user_file(TOKENFILE, SCOPES)
            if not self.creds.valid:
                if self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())

            self.service = build("calendar", "v3", credentials=self.creds)
            print("GAPI Calendar Client initialized")

    def has_creds(self):
        return not self.creds is None

    def setCredentials(self, new_creds):
        self.creds = new_creds
        self.service = build("calendar", "v3", credentials=self.creds)

        with open(TOKENFILE, "w") as token:
            token.write(self.creds.to_json())
        if self.creds and self.service:
            return True
        else:
            return False

    def list_all_calendars(self):
        return list(
            filter(
                lambda cal: cal.get("selected"),
                self.service.calendarList().list().execute().get("items", []),
            )
        )

    def list_calendar_events(self, calendar_id, num_days):
        utc_now = datetime.datetime.utcnow()

        now = datetime.datetime.now()
        midnight = datetime.datetime.combine(datetime.date.today(), datetime.time().max)
        diff = midnight - now
        utc_max = utc_now + diff + datetime.timedelta(days=num_days)

        events_results = (
            self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=utc_now.isoformat() + "Z",
                timeMax=utc_max.isoformat() + "Z",
                orderBy="startTime",
                singleEvents=True,
            )
            .execute()
        )

        events = events_results.get("items", [])
        return filter(lambda e: e.get("summary") != "Ultrabrain reminder", events)

    def get_event(self, calendar_id, event_id):
        return (
            self.service.events()
            .get(calendarId=calendar_id, eventId=event_id)
            .execute()
        )

    def insert_event(self, calendar_id, event):
        return (
            self.service.events().insert(calendarId=calendar_id, body=event).execute()
        )
