
import json
import requests
host = 'http://localhost:8000'

def collect_data():
    sql = ('SELECT *'
        ' FROM post_post;')
    api_key = '1DyQ69AJGu6chA2B306VDQ5Qiy4mT4eH8'
    url = host + '/api/rawsql?api_key={}&sql={}'.format(api_key, sql)
    print(url)
    r = requests.get(url)
    with open('save.json', 'w') as f:
        f.write(json.dumps(json.loads(r.text)))

def get_salary(val):
    val = val.replace(',', '').replace('$', '').strip()
    if '-' in val:
        s1, s2 = val.split('-')
        return str((float(s2) + float(s1)) / 2)
    return val

def parse():
    data = []
    with open('save.json', 'r') as f:
        data = f.read()
    
    data = json.loads(data)
    trainX = []
    trainY = []
    for d in data:
        salary = d[3]
        vec = d[7]
        if '$' in salary:
            trainX.append(vec)
            trainY.append(get_salary(salary))
    
    with open('trainX', 'w') as f:
        f.write("-".join(trainX))

    with open('trainY', 'w') as f:
        f.write("-".join(trainY))

def load_train():
    trainX = []
    trainY = []
    with open('trainX', 'r') as f:
        trainX = f.read().split('-')
    with open('trainY', 'r') as f:
        trainY = [float(_) for _ in f.read().split('-')]

    return trainX, trainY

# parse()
load_train()