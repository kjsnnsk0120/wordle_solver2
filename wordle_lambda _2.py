if __name__ == "lambda_function":
    import pandas as pd
    import numpy as np
    import collections
    import boto3
    word_list_answer_filename = "s3://wordle-solver-uxrt6nnu/word_list_answer.pk"
    word_list_all_filename = "s3://wordle-solver-uxrt6nnu/word_list_all.pk"
    word_relation_table_filename = "s3://wordle-solver-uxrt6nnu/word_relation_table_limited_int8.pk"
    word_list_answer = pd.read_pickle(word_list_answer_filename)
    word_list_all = pd.read_pickle(word_list_all_filename)
    #word_list_filename = "https://raw.githubusercontent.com/alex1770/wordle/main/wordlist_nyt20220316_all"
    #ans_list_filename = "https://raw.githubusercontent.com/alex1770/wordle/main/wordlist_nyt20220316_hidden"
    #words = pd.read_table(word_list_filename, header = None)[0]
    #anss = pd.read_table(ans_list_filename, header = None)[0]

elif __name__ == "__main__":
    import requests
    import json
    api_endpoint = "https://cz3cdlwyw1.execute-api.ap-northeast-1.amazonaws.com/default/wordle_2"

def client():
    word_list_int = -1
    print("suggested word is soare")
    while(True):
        input_word = input("input your word\n")
        input_response = input("input its response\n")
        res = call_lambda(word_list_int,input_word,input_response)
        if int(res["number_of_candidates"]) == 0:
            print("something wrong")
            break
        elif int(res["number_of_candidates"]) == 1:
            print("the answer is " + str(res["candidates"]))
            break
        print("number_of_candidates: "+str(res["number_of_candidates"]))
        print("suggested word is " + str(res["suggested_word"]))
        if int(res["number_of_candidates"]) <= 10:
            print("candidates are " + res["candidates"])
        word_list_int = res["available_int"]

def call_lambda(word_list_int,input_word,input_response):
    params = {"word_list_int":str(word_list_int),
            "input_word": input_word,
            "input_response": input_response}
    print("calculating......")
    result = json.loads(requests.get(api_endpoint,params = params).text)
    return result

def call_relation_table():
    return pd.read_pickle(word_relation_table_filename)

def word_list_int_to_word_list(word_list_int):
    if word_list_int == -1:
        return word_list_answer.copy()
    else:
        word_list_init = word_list_answer.copy()
        d = []
        for i in range(len(word_list_init)-1,-1,-1):
            if word_list_int & 1<<i:
                d.append(True)
            else:
                d.append(False)
        return word_list_init[d]

def word_list_to_word_list_int(word_list):
    c = 0
    for aa in word_list.index:
        c += 1<<(len(word_list_answer)-aa-1)
    return c

def calc_candidate(word_list,input_word,res):
    word_dict = {chr(i):5 for i in range(97,123)}
    def check_word_available(word, o_list, p_list):
        w_counter = {}
        for w in word:
            if w in w_counter:
                w_counter[w] += 1
            else:
                w_counter[w] = 1
        for w in w_counter:
            if w_counter[w] > word_dict[w]:
                return False
        for i in o_list:
            if o_list[i] != word[i]:
                return False
        for i,p in p_list.items():
            if p not in word:
                return False
            if p == word[i]:
                return False
        return True

    tmp = ""
    o_list = {}
    p_list = {}
    word_counter = collections.Counter(input_word)
    for i in range(5):
        if res[i] == "o":
            o_list.update({i:input_word[i]})
            tmp += input_word[i]
        if res[i] == "-":
            p_list.update({i:input_word[i]})
            tmp += input_word[i]
    used_counter = collections.Counter(tmp)
    for w in input_word:
        if w in used_counter and used_counter[w] != word_counter[w]:
            word_dict[w] = used_counter[w]
        elif w not in used_counter:
            word_dict[w] = 0

    available_list = word_list.apply(check_word_available,o_list = o_list,p_list = p_list)
    return word_list[available_list]

def suggest_best_word(word_list):
    def calc_aic(row):
        c = collections.Counter(row)
        c_np = np.array(list(c.values()))
        prob = c_np/c_np.sum()
        return -(prob * np.log2(prob)).sum()

    relation_table = call_relation_table()[word_list.to_list()]
    ans = relation_table.apply(calc_aic,axis = 1)
    ans = {k: v for k, v in ans.items()}
    ans_sorted = sorted(ans.items(), key=lambda x:x[1],reverse=True)
    return ans_sorted

def suggest_input_word(ans_sorted,word_list):
    best_aic = ans_sorted[0][1]
    ans_sorted_dict = dict(ans_sorted)
    word_list_list = word_list.to_list()
    for word in word_list_list:
        if ans_sorted_dict[word] == best_aic:
            return word
    return ans_sorted[0][0]

def print_available_words(word_list_available):
    if len(word_list_available) <= 10:
        return " ".join(word_list_available.to_list())
    else:
        return "over"

def lambda_handler(event, context):
    input_params = event['queryStringParameters']
    word_list_int = int(input_params["word_list_int"])
    input_word  = input_params["input_word"]
    input_response = input_params["input_response"]
    word_list = word_list_int_to_word_list(word_list_int)
    word_list_available = calc_candidate(word_list,input_word,input_response)
    aic_list = suggest_best_word(word_list_available)
    suggest_word = suggest_input_word(aic_list,word_list_available)
    available_int = word_list_to_word_list_int(word_list_available)
    return_params = {"available_int" : str(available_int), 
                    "number_of_candidates" : str(len(word_list_available)),
                    "candidates": print_available_words(word_list_available),
                    "suggested_word": suggest_word}
    return return_params

def event_simulator():
    available_int = (1<<2309) - 1
    input_word = "soare"
    input_response = "ox--x"
    return {"word_list_int":str(available_int),
            "input_word": input_word,
            "input_response": input_response}
            
def create_wordlist_pk():
    word_list_answer_filename = "https://raw.githubusercontent.com/alex1770/wordle/main/wordlist_nyt20220316_hidden"
    word_list_all_filename = "https://raw.githubusercontent.com/alex1770/wordle/main/wordlist_nyt20220316_all"
    word_list_answer = pd.read_table(word_list_answer_filename,header = None)[0]
    word_list_all = pd.read_table(word_list_all_filename,header = None)[0]
    word_list_answer.to_pickle("word_list_answer.pk")
    word_list_all.to_pickle("word_list_all.pk")

if __name__ == "__main__":
    client()
