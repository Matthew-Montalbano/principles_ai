import json
from nltk.corpus import wordnet
from flask import Flask, jsonify
from flask_restful import Resource, Api, reqparse
import pandas as pd
import ast

# NLP related imports
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
EXPLAIN = True
# import nltk
# nltk.download('wordnet')
# from nltk.corpus import stopwords
# from nltk.tokenize import word_tokenize

app = Flask(__name__)
api = Api(app)

# learned from https://towardsdatascience.com/the-right-way-to-build-an-api-with-python-cd08ab285f8f


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
            #           Use WUP similarity algorithm here
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
#
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

# for idx, row in df.iterrows():
#     print(row['principle'])
# return top 5 principles/habits that matches the best with the event

# def find_principles(event, sp_pairs):
#     sorted_sp_paris = sorted([(check_2_sentence_similarities(event, senario), principle) for senario, principle in sp_pairs.items()])[::-1]
#     return [pair[1] for pair in sorted_sp_paris if pair[0]][:5]


def find_principles(event, sp_df):
    sorted_sp_paris = sorted([(check_2_sentence_similarities(
        event, row['scenario']), row['principle']) for idx, row in sp_df.iterrows()])[::-1]
    return [pair[1] for pair in sorted_sp_paris if pair[0]][:5]

# sp_pairs = {
#                 "Startup Meeting": "example principle for Startup Meeting: Always confirm avalibility and time",
#                 "Need to become confident": "example principle for Need to become confident: Power-poses boosts confidence",
#                 "eat breakfast": "example principle for eat breakfast",
#                 "excersize": "example principle for excersize",
#                 "angry": "example principle for angry",
#                 "software debugging": "example principle for software debugging",
#                 "Brainstorming Session": "example principle for Brainstorming Session"
#            }

# def find_principles(event, sp_pairs):
#     sorted_sp_paris = sorted([(check_2_sentence_similarities(event, senario), principle) for senario, principle in sp_pairs.items()])[::-1]
#     return [pair[1] for pair in sorted_sp_paris if pair[0]][:5]


# event = "weekly company call"
# event = "pair programming"
# event = "lunch with client"

# print(f'*** most recommended principles found for event \"{event}\" are {find_principles(event, sp_pairs)} ***')

# define Users class as an endpoint for our API, and so we can pass Resource in with the class definition.
class Users(Resource):
    def get(self):
        # data = pd.read_csv('users.csv')  # read CSV
        # data = data.to_dict()  # convert dataframe to dictionary

        # return {'data': data}, 200  # return data and 200 OK code
        response = jsonify({'hello': "world"})
        response.status_code = 200
        return response

    def post(self):
        parser = reqparse.RequestParser()  # initialize

        parser.add_argument('userId', required=True)  # add args
        parser.add_argument('event', required=True)
        # parser.add_argument('city', required=True)

        args = parser.parse_args()  # parse arguments to dictionary

        # create new dataframe containing new values
        # new_data = pd.DataFrame({
        #     'userId': args['userId'],
        #     'event': args['event'],
        #     'city': "waterloo",
        #     'locations': [[]]
        # })

        # import pdb; pdb.set_trace()
        # read our CSV
        # data = pd.read_csv('users.csv')
        # add the newly provided values
        # data = data.append(new_data, ignore_index=True)
        # save back to CSV
        # data.to_csv('users.csv', index=False)
        event = args['event']
        # print(f'*** most recommended principles found for event \"{event}\" are {find_principles(event, sp_pairs)} ***')
        # return data with 200 OK
        response = jsonify(
            {'event': event, 'principles': find_principles(event, sp_df)})
        response.status_code = 200
        return response
        # return {'data':f'{new_data['event'].tolist()}' }, 200  # return data with 200 OK
        # return {'data':f'{event}' }, 200


api.add_resource(Users, '/users')  # '/users' is our entry point

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # run our Flask app
