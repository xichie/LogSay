'''
    将问题匹配与日志模板匹配, 并计算准确率
'''
import torch
from q2e_model import BertSimilarity
from utils import read_json, get_similarity_logs
import pandas as pd
from tqdm import tqdm
from transformers import BertTokenizer, BertModel
import argparse
import time

        
def match_question_event(dataset, similarity_metric='Jaro'):
    if similarity_metric == 'Gold':
        qe = {} # question: event
        for qa_info in tqdm(read_json('./logs/{}/qa_test.json'.format(dataset))):
            if qa_info['Question'] in qe.keys(): # 查重
                print(qa_info['Question'])
            qe[qa_info['Question']] = qa_info['Events'][0]  
        return 1.0, qe
    log_events =  pd.read_csv('./logs/{}/{}_2k.log_templates.csv'.format(dataset, dataset))
    event2id = {row['EventTemplate']: row['EventId'] for index, row  in log_events.iterrows()}
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased") if (similarity_metric in ['cosine', 'mybert'] )  else None
  
    if similarity_metric == 'cosine':
        bert_model = BertModel.from_pretrained("bert-base-uncased")
    elif similarity_metric == 'mybert':
        bert_model = BertSimilarity()
        bert_model.load_state_dict(torch.load('./logs/{}/mybert.pth'.format(dataset)))
    else:
        bert_model = None


    q2e_start = time.time()
    correct_count = 0
    total_count = 0
    qe = {} # question: event
    for qa_info in tqdm(read_json('./logs/{}/qa_test.json'.format(dataset))):
        if qa_info['Question'] in qe.keys(): # 查重
                print(qa_info['Question'])
        most_similarity_events = get_similarity_logs(qa_info['Question'], log_events['EventTemplate'], similarity_metric, dataset, tokenizer, bert_model)
        most_similarity_eventIds = [event2id[event] for event in most_similarity_events]
        if most_similarity_eventIds[0] in qa_info['Events']:  # 如果问题匹配到了正确事件，则添加到qe中
            correct_count += 1
            qe[qa_info['Question']] = most_similarity_eventIds[0]
        else:                                                # 否则，问题对应的事件为空
            qe[qa_info['Question']] = ''      
            # print(qa_info['Question'])
            # print(qa_info['Events'][0], '----', most_similarity_eventIds[0])          
        total_count += 1
    acc = correct_count / total_count
    q2e_end = time.time()
    print("Log q2e time:", (q2e_end-q2e_start))
    return acc, qe 

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--dataset', type=str, help='dataset to use')
    arg = argparser.parse_args()
    dataset = arg.dataset
    similarity_list = [
        "random",
        "Edit_Distance",
        "jaccard",
        "BM25",
        "Jaro",
        "jaro_winkler",
        "cosine",
        'mybert',
    ]
    result = {'similarity_metric': [], 'accuracy': []}
    for similarity_metric in similarity_list:
        acc, qe = match_question_event(dataset, similarity_metric)
        print('method: {}, accuarcy: {}'.format(similarity_metric ,acc))
        result['similarity_metric'].append(similarity_metric)
        result['accuracy'].append(acc)

    # pd.DataFrame(result).to_csv('./results/{}/{}_match_question_event_acc.csv'.format(dataset, dataset), index=False)