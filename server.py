import json
from nltk.corpus import wordnet
from flask import Flask, jsonify, request
from flask_restful import Resource, Api, reqparse
import pandas as pd
import ast
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import datetime

# NLP related imports
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
EXPLAIN = True

app = Flask(__name__)
api = Api(app)

flow = Flow.from_client_secrets_file(
    './auth/desktop-google-oauth.json',
    scopes=['https://www.googleapis.com/auth/calendar.app.created', 'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email', 'openid', 'https://www.googleapis.com/auth/calendar.events'],
    redirect_uri='postmessage',
)

# compare all the synsets of each pair of a word in w1(event) and w2(scenario)


def word_similiarity(w1, w2):
    sl1 = wordnet.synsets(w1)
    sl2 = wordnet.synsets(w2)
    max_score = 0
    if EXPLAIN:
        best_matching_word = {
            'x': "",
            'y': "",
            'score': 0
        }
    for x in sl1:
        for y in sl2:
            # Use WUP similarity algorithm here
            score = x.wup_similarity(y)
            max_score = max(max_score, score if score else 0)
            if EXPLAIN and score == max_score:
                best_matching_word['x'] = x.name().split('.')[0]
                best_matching_word['y'] = y.name().split('.')[0]
                best_matching_word['score'] = score
    result = (max_score,)
    if EXPLAIN:
        result += (f'"{w1}" -> "' + best_matching_word['x'] + f'" < match with > "{w2}" -> "' +
                   best_matching_word['y'] + f'" | matching score = ' + str(best_matching_word['score']),)
    return result

# Return cosine similiarities between 2 sentences


def check_2_sentence_similarities(X, Y, USE_WORDNET_SIMILARITY=True):
    print(f'--- compare between event "{X}" and scenario "{Y}" ---')

    # tokenization and normalization
    X_list = [w.lower() for w in word_tokenize(X)]
    Y_list = [w.lower() for w in word_tokenize(Y)]

    # sw contains the list of stopwords
    sw = stopwords.words('english')
    l1 = []
    l2 = []

    # remove stop words from the string
    X_set = {w for w in X_list if not w in sw}
    Y_set = {w for w in Y_list if not w in sw}

    # form a set containing keywords of both strings
    rvector = X_set.union(Y_set)
    if EXPLAIN:
        print(f' axis names of the combined words\'s vector space: {rvector}')
    if USE_WORDNET_SIMILARITY:
        for w in rvector:
            X_set_match = max([word_similiarity(w, X_set_word)
                               for X_set_word in X_set])
            X_set_scores = X_set_match[0]
            if EXPLAIN:
                print(f' → word in event: "{w}", analysis | ', X_set_match[1])
            if X_set_scores:
                l1.append(X_set_scores)  # create a vector
            else:
                l1.append(0)

            Y_set_match = max([word_similiarity(w, Y_set_word)
                               for Y_set_word in Y_set])
            Y_set_scores = Y_set_match[0]
            if EXPLAIN:
                print(
                    f' → word in scenario: "{w}", analysis | ', Y_set_match[1])
            if Y_set_scores:
                l2.append(Y_set_scores)
            else:
                l2.append(0)
    else:
        for w in rvector:
            if w in X_set:
                l1.append(1)  # create a vector
            else:
                l1.append(0)
            if EXPLAIN:
                print(f' → word in event: "{w}", analysis | ', l1[-1])
            if w in Y_set:
                l2.append(1)
            else:
                l2.append(0)
            if EXPLAIN:
                print(f' → word in scenario: "{w}", analysis | ', l2[-1])
    if EXPLAIN:
        print(
            f' event {X_set} makes vector: {l1} and scenario {Y_set} makes vector: {l2}')
    c = 0

    # cosine formula
    for i in range(len(rvector)):
        c += l1[i]*l2[i]
    # use max(,0.001) is for the case where there is 0 match meaning between the 2 sentences
    cosine = c / max(float((sum(l1)*sum(l2))**0.5), 0.001)
    print(f' similarity between event "{X}" and scenario "{Y}": ',
          '\033[1m' + str(cosine) + '\033[0m')
    return cosine


sp_df = pd.read_csv('principles.csv')


def find_principles(event, sp_df):
    sorted_sp_paris = sorted([(check_2_sentence_similarities(
        event, row['scenario']), row['principle']) for idx, row in sp_df.iterrows()])[::-1]
    return [pair[1] for pair in sorted_sp_paris if pair[0]][:5]


# define Users class as an endpoint for our API, and so we can pass Resource in with the class definition.
class Users(Resource):
    def get(self):
        response = jsonify({'hello': "world"})
        response.status_code = 200
        return response

    def post(self):
        parser = reqparse.RequestParser()  # initialize

        parser.add_argument('userId', required=True)  # add args
        parser.add_argument('event', required=True)

        args = parser.parse_args()  # parse arguments to dictionary

        event = args['event']
        response = jsonify(
            {'event': event, 'principles': find_principles(event, sp_df)})
        response.status_code = 200
        return response


api.add_resource(Users, '/users')  # '/users' is our entry point


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
