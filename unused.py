"""
for future integrations
from pymongo import MongoClient
db_client = MongoClient(port=27017)
db = db_client.admin.up_database_test

result = db.insert_one({'user': 'h.tony.deng@gmail.com', 'code': 'cododooo'})

from security import SecurityClient
crypt = SecurityClient(config('SECRET_KEY'), config('SECRET_PASSWORD'))
print(crypt.encryptPayload({'hello': 'world'}))
"""


"""

@app.route("/testNotion", methods=["GET"])
def test_notion():
    print(nc.get_scenarios_table())
    print(gc.list_calendar_events(calendar_id="openprinciples@gmail.com", num_days=1))
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

    return "nice", 200
"""