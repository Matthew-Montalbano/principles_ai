# NLP related imports
import nltk
from nltk.corpus import wordnet
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import pandas as pd

EXPLAIN = True

# compare all the synsets of each pair of a word in w1(event) and w2(scenario)


class UpNlpClient:
    def __init__(self, principles):
        self.sp_df = pd.read_csv(principles)

    def word_similiarity(self, w1, w2):
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

    def check_2_sentence_similarities(self, X, Y, USE_WORDNET_SIMILARITY=True):
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
            print(
                f' axis names of the combined words\'s vector space: {rvector}')
        if USE_WORDNET_SIMILARITY:
            for w in rvector:
                X_set_match = max([self.word_similiarity(w, X_set_word)
                                   for X_set_word in X_set])
                X_set_scores = X_set_match[0]
                if EXPLAIN:
                    print(
                        f' → word in event: "{w}", analysis | ', X_set_match[1])
                if X_set_scores:
                    l1.append(X_set_scores)  # create a vector
                else:
                    l1.append(0)

                Y_set_match = max([self.word_similiarity(w, Y_set_word)
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

    def find_principles(self, event):
        sorted_sp_paris = sorted([(self.check_2_sentence_similarities(
            event, row['scenario']), row['principle']) for idx, row in self.sp_df.iterrows()])[::-1]
        return [pair[1] for pair in sorted_sp_paris if pair[0]][:5]
