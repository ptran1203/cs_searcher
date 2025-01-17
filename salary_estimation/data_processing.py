import unidecode
import re
import nltk
import requests
import json
import numpy as np
import pickle
from nltk.tokenize import word_tokenize
from sklearn.ensemble import RandomForestRegressor
import sys

try:
    from salary_estimation.word2vec import embedding
except ImportError:
    from word2vec import embedding

# Values are "train", "collect"
OPT = -1 if len(sys.argv) < 2 else sys.argv[1]

print(OPT)

API_KEY = "1DyQ69AJGu6chA2B306VDQ5Qiy4mT4eH8"
SALARY_UNITS = ["$", "USD", "TRIỆU", "TRIEU"]
SALARY_DETECT_TERM = ["SALARY", "LƯƠNG", "LUONG"]

EXP_PARTERN = re.compile(r"year\D+experience|năm\D+kinh nghiệm", re.IGNORECASE)

nltk.download("punkt")

host = "http://iseek.herokuapp.com"


def pprint(*text):
    if OPT == 0:
        print(*text)


def collect_data():
    sql = (
        "SELECT post_post.content,post_post.title,post_post.salary_range"
        " FROM post_post;"
    )
    url = host + "/api/rawsql?api_key={}&sql={}".format(API_KEY, sql)
    r = requests.get(url)
    if r.status_code == 200:
        data = json.loads(r.text)
        pprint("Get {} records".format(len(data)))
    else:
        data = []
        pprint("Request failed with status code {}, {}".format(r.status_code, r.text))
    return data


def to_float(val):
    try:
        return float(val)
    except ValueError:
        return False


def _cleaned_num(val):
    if "%" in val:
        return ""

    return val.replace(".", "").replace(",", "")


def to_usd(val, vnd, scale):
    val = to_float(_cleaned_num(val))

    if val > 30000000:
        val /= 10

    if val >= 1000000:
        return val * 0.000043
        scale = 1

    if val is False:
        return False

    if vnd:
        return val * 0.000043 * scale

    elif val < 100:
        return False

    return val


def get_scale_factor(val):
    if "TRIỆU" in val.upper() or "TRIEU" in val.upper() or re.search(r"[0-9]+M", val):
        return 1e6

    if re.search(r"[0-9]+K", val):
        return 1e3

    return 1


def get_salary(val):
    if not val or type(val) is not str:
        return []

    scale = get_scale_factor(val)
    is_vnd = not ("$" in val or "USD" in val.upper()) and any(
        [c in val.upper() for c in {"VND", "VNĐ", "TRIỆU", "TRIEU"}]
    )

    if not is_vnd and scale == 1e6:
        """
        UPTO 20M/tháng.
        Lương thỏa thuận. Từ 20M – 30M/tháng.
        """
        is_vnd = True

    vals = re.findall(r"[0-9.,]+%?", val)

    vals = list(filter(lambda x: _cleaned_num(x) != "", vals))

    if not vals or len(vals) > 2:
        return []

    if len(vals) == 2:
        max_val, min_val = [
            to_usd(vals[0], is_vnd, scale),
            to_usd(vals[1], is_vnd, scale),
        ]
    else:
        max_val, min_val = [
            to_usd(vals[0], is_vnd, scale),
            to_usd(vals[0], is_vnd, scale),
        ]

    # print(max_val, min_val)

    if max_val is False:
        max_val = min_val
    elif min_val is False:
        min_val = max_val

    if max_val is False:
        return []

    return max_val, min_val


def clean_text(text):
    text = unidecode.unidecode(text.lower())
    tokens = word_tokenize(text)
    return [t for t in tokens if re.match(r"[^\W\d]*$", t)]


def _get_salaty_from_content(content):
    idx = -1
    for term in SALARY_DETECT_TERM:
        idx = content.upper().find(term)
        if idx != -1:
            trun = content[idx : idx + 45]
            salary = get_salary(trun)
            if salary and max(salary) > 10000:
                print(trun)
            if not salary:
                pass
                # with open("content.txt", "a") as f:
                #     f.write(
                #         content[idx : idx + 50] + "\n{}\n---------\n".format(salary)
                #     )
            else:
                # with open("have_salary.txt", "a") as f:
                #     f.write(
                #         content[idx : idx + 35]
                #         + "\n{} {}\n---------\n".format(
                #             salary, get_scale_factor(content[idx : idx + 35])
                #         )
                #     )
                return salary

    return False


def _cleaned_exp(val):
    val = val.replace(",", ".")
    val = re.sub(r"[^0-9.]", "", val)
    try:
        return float(val)
    except Exception as e:
        print("Convert to int error for value: {}".format(val), e)
        return None


def get_year_exp(description):
    key = EXP_PARTERN.search(description)
    if not key:
        return None

    head, tail = key.span()

    if tail - head > 100:
        return None

    key = key.group(0)
    truncated = description[max(head - 15, 0) : tail + 15].replace("\n", " ")
    term = "year" if "year" in key else "năm"
    rex = r"[0-9]+-?[0-9]+\+? {}".format(term)
    numbers = re.findall(rex, truncated)
    if not numbers:
        rex = r"[0-9.,]+\+? {}".format(term)
        numbers = re.findall(rex, truncated)

    if numbers and len(numbers) == 1:
        vals = numbers[0].split("-")
        len(vals) == 1 and vals.append(vals[0])
        vals = list(filter(lambda x: x is not None, [_cleaned_exp(n) for n in vals]))
        len(vals) == 1 and vals.append(vals[0])
        return vals


def parse(data, get_exp=False):
    trainX = []
    trainY = []
    exps = []
    for d in data:
        desc, title, salary = d
        text = title + " " + desc
        salary = get_salary_for_post(salary, title, desc)

        if salary:
            exp = get_year_exp(desc)
            if exp or get_exp:
                # pprint(exp, salary, desc[:200].replace("\n", " "))
                trainX.append(clean_text(text))
                trainY.append(salary)
                exps.append(exp)

    return trainX, trainY, exps


def get_salary_for_post(salary, title, desc):
    salary = get_salary(salary)
    if not salary:
        if any(c in title.upper() for c in SALARY_UNITS):
            salary = get_salary(title)

    if not salary:
        salary = _get_salaty_from_content(desc)

    return salary


def to_embedding(texts):
    r = []
    for txt in texts:
        r.append(embedding.text2vec(txt))

    return np.array(r)


def load_data(get_new=True):
    new_data = []
    if get_new:
        print("Fetch new data...")
        new_data = collect_data()

    with open("./salary_estimation/storage/temp.json", "r") as f:
        data = json.load(f)

    descriptions = set([d[0][:100] for d in data])
    count = 0
    for d in new_data:
        if d[0][:100] not in descriptions:
            data.append(d)
            count += 1

    print("Total: {}, {} new".format(len(data), count))

    if count:
        with open("./salary_estimation/storage/temp.json", "w") as f:
            json.dump(data, f)

    return data


if __name__ == "__main__":
    data = load_data(OPT == "collect")
    train_x, train_y, exps = parse(data, get_exp=OPT == "train")

    train_y = np.array(train_y)
    exps = np.array(exps)

    if OPT == "train":
        train_x = to_embedding(train_x)
        print(train_y.shape, exps.shape)
        max_salary = np.max(train_y)
        print("max_salary", max_salary)
        train_y = train_y / max_salary

        model = RandomForestRegressor(max_depth=3)
        model.fit(train_x, train_y)
        score = model.score(train_x, train_y)
        print(score)

        filename = "./salary_estimation/storage/model.pkl"
        pickle.dump(model, open(filename, "wb"))
        pickle.dump(max_salary, open("./salary_estimation/storage/maxval.pkl", "wb"))

    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd

    train_y = np.mean(train_y, axis=1)
    exps = np.mean(exps, axis=1)

    df = pd.DataFrame({"salary": train_y, "exp": exps})
    sns.jointplot(data=df, x="salary", y="exp")
    plt.show()
