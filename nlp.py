# NLP related imports
import nltk
from nltk.corpus import wordnet
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import pandas as pd
import openai
from decouple import config
from random import randint

EXPLAIN = False

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
        if EXPLAIN:
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
        if EXPLAIN:
            print(f' similarity between event "{X}" and scenario "{Y}": ',
                  '\033[1m' + str(cosine) + '\033[0m')
        return cosine

    def find_principles(self, event):
        # TODO: need to delete this code at the end
        sorted_sp_paris = sorted([(self.check_2_sentence_similarities(
            event, row['scenario']), row['principle']) for idx, row in self.sp_df.iterrows()])[::-1]
        results = [pair[1] for pair in sorted_sp_paris if pair[0]][:3]
        return results

    def gpt3_classify_event(self,
                            event_title,
                            event_location="N/A",
                            event_participants="N/A",
                            event_time="2021, Sep 25, 4pm",
                            event_duration=""):

        # TODO: add this to private key
        openai.api_key = config('OPENAI_KEY')

        for number_of_try in range(10):
            print(f"number { number_of_try} try for openAI api request")
            # prompt = f"Event: \"Daily Standup\"\nEvent Location: \"Room 203\"\nEvent Time: \"2021, Sep 20, 9am\"\nEvent Participants: \"robert@ibm.com; amy@ibm.com; \"\nresult: work,indoor,offline,participate in meeting\n###\nEvent: \"Submit project solution design for GM\"\nEvent Location: \"https://zoom.us/j/94854324867?pwd=L0NlaWpaQzhjSmk1WlVnK05QT1M5UT09\"\nEvent Time: \"2021, Sep 21, 4pm\"\nEvent Participants: \"bob@apple.com; sally@ibm.com; \"\nresult: work,indoor,online,submit project\n###\nEvent: \"Shang-Chi Movie Night\"\nEvent Location: \"Galaxy Cinemas Waterloo\"\nEvent Time: \"2021, Sep 22, 9pm\"\nEvent Participants: \"guoty3310@gmail.com; pp123@hotmail.com; \"\nresult: life,indoor,offline,watch movie\n###\nEvent: \"Lunch\"\nEvent Location: \"N/A\"\nEvent Time: \"2021, Sep 24, 12pm\"\nEvent Participants: \"N/A\"\nresult: life,unknown,offline,eat lunch\n###\nEvent: \"{event_title}\"\nEvent Location: \"{event_location}\"\nEvent Time: \"{event_time}\"\n{event_participants}: \"N/A\"\nresult: "
            # NOTE: in the prompt, there should be no spaces between tags
            response = openai.Completion.create(
                engine="davinci",
                prompt=f"Event: \"Daily Standup\"\nEvent Location: \"Room 203\"\nEvent Time: \"2021, Sep 20, 9am\"\nEvent Participants: \"robert@ibm.com; amy@ibm.com; \"\nresult:work,indoor,offline,participate in meeting\n###\nEvent: \"Submit project solution design for GM\"\nEvent Location: \"https://zoom.us/j/94854324867?pwd=L0NlaWpaQzhjSmk1WlVnK05QT1M5UT09\"\nEvent Time: \"2021, Sep 21, 4pm\"\nEvent Participants: \"bob@apple.com; sally@ibm.com; \"\nresult:work,indoor,online,submit project\n###\nEvent: \"Shang-Chi Movie Night\"\nEvent Location: \"Galaxy Cinemas Waterloo\"\nEvent Time: \"2021, Sep 22, 9pm\"\nEvent Participants: \"guoty3310@gmail.com; pp123@hotmail.com; \"\nresult:life,indoor,offline,watch movie\n###\nEvent: \"Lunch\"\nEvent Location: \"N/A\"\nEvent Time: \"2021, Sep 24, 12pm\"\nEvent Participants: \"N/A\"\nresult:life,unknown,offline,eat lunch\n###\nEvent: \"{event_title}\"\nEvent Location: \"{event_location}\"\nEvent Time: \"{event_time}\"\nEvent Participants: \"{event_participants}\"\nresult:",
                temperature=0,
                max_tokens=20,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stop=["###"]
            )
            # TODO: find out if there could ever be a response['choices'][0]['text']
            text = response['choices'][0]['text']
            if len(text) > 10:
                print(
                    f'OpenAI reurned text: \n ------begin------\n{text}\n------end------')
                end_idx = text.find('\n')
                comma_idx = text.find(",")
                start_idx = comma_idx-4  # TODO: improve this logic to include the cases not 4
                return text[start_idx:end_idx]

        return ""

    def gpt3_find_matching_scenarios(self, event, scenarios_df):


        # Get predictions
        event_values = [v for v in event.values()]
        predictions = self.gpt3_classify_event(event_values)
        # predictions = 'work,group,offline,go to team social' #TODO: delete this to use the real prediction
        if not predictions:
            return []
        prediction_list = predictions.split(',')
        event_summary = prediction_list[-1]
        event_tags = prediction_list[:-1]

        # count number of matching tags for all scenarios
        scenarios_df['matching_score'] = 0
        for i, row in scenarios_df.iterrows():
            # TODO: convert the event_tags and row['tags'] to set will speed this up
            score = len([word for word in row['tags'] if word in event_tags])
            scenarios_df.at[i, 'matching_score'] = score

        # filter senarios by number of matching tags
        number_matching_tags_threashold = 2
        scenarios_df = scenarios_df[scenarios_df['matching_score'] >= number_matching_tags_threashold]
        number_senarios_for_similarity_comparison = 8
        top_senarios_df = scenarios_df.sort_values(
            ['matching_score'], ascending=[False]).head(number_senarios_for_similarity_comparison)
        print(top_senarios_df)
        
        # track scentence matching score for top scenarios
        top_senarios_df['scentence_similarity'] = 0
        for i, row in top_senarios_df.iterrows():
            # TODO: convert the event_tags and row['tags'] to set will speed this up
            score = self.check_2_sentence_similarities(row['scenarios'], event['event_title'])
            top_senarios_df.at[i, 'scentence_similarity'] = score

        # filter senarios by scentence_similarity
        number_senarios_for_getting_principles = 2
        top_senarios_df = top_senarios_df.sort_values(
            ['scentence_similarity'], ascending=[False]).head(number_senarios_for_getting_principles)

        principle_scenario_pairs_df = pd.DataFrame(
            columns=["principles", "scenarios"])
        principle_scenario_pairs_df["scenarios"] = []
        found_principles = []

        # make principle_scenario_pairs, the scencario here will be useful for formatting principles later
        for i, row in top_senarios_df.iterrows():
            num_principles = len(row['principles'])
            principle_idx = randint(0, num_principles-1)
            new_principle = row['principles'][principle_idx]

            while (new_principle in found_principles):
                principle_idx = randint(0, num_principles-1)
                new_principle = row['principles'][principle_idx]
            found_principles.append(new_principle)

            row_to_add = {
                "principles": new_principle,
                "scenarios": row['scenarios_human']
            }
            principle_scenario_pairs_df = principle_scenario_pairs_df.append(
                row_to_add, ignore_index=True)
            # for principle_id in row['principles']:
            #     import pdb; pdb.set_trace()
            #     if principle_id not in principle_scenario_pairs_df['principles']:
            #         row_to_add = {
            #             "principles": principle_id,
            #             "scenarios": [row['scenarios']]
            #         }
            #         principle_scenario_pairs_df = principle_scenario_pairs_df.append(row_to_add, ignore_index = True)
            #     else:
            #         principle_scenario_pairs_df.loc[principle_scenario_pairs_df['principles'] == principle_id, 'scenarios'] += [row['scenarios']]

        print(f'principle_scenario_pairs: {principle_scenario_pairs_df}')

        return principle_scenario_pairs_df

    def format_principles(self, principles_df, principle_scenario_pairs_df):
        results = []
        for i, row in principles_df.iterrows():
            # import pdb; pdb.set_trace()
            scenario = principle_scenario_pairs_df.loc[principle_scenario_pairs_df['principles'] == row['id'], 'scenarios_human'].tolist()[
                0]
            principle = row['principle'].replace('\n', '')
            new_principle = [f'👀 {scenario}?', f"💡 Reminder: {principle}"]
            if row['notes'] != '':
                new_principle.append('🔎  ' + row['notes'])
            if row['source'] != '':
                new_principle.append('🔗 From: ' + row['source'])
            results.append('\n'.join(new_principle))
        return results
