from flask import Flask, render_template, request
import requests
import json
import datetime
import time
from flask_apscheduler import APScheduler
from config import headers, p_headers




app = Flask(__name__)
scheduler = APScheduler()



salon_id = 780413

now = datetime.date.today()
# now = '2023-03-07'
data_list = [{}]
new_data_list = []
db = []
dataset = {}
transaction_data = {}
visits = {}
loyalty_visits = {}








def findallrec():
    print(f"Запуск поиска записей за дату: {now}")
    url = f"https://api.yclients.com/api/v1/records/{salon_id}?start_date={now}&end_date={now}&include_finance_transactions=1&page=1&count=1000"
    payload = ""
    response = requests.request("GET", url, headers=headers, data=payload)
    response_pretty = response.json()
    return response_pretty

def parserdata(data):
    visit_ids = []
    clients = []
    phones = []
    for i in range(len(data)):
        # print(data[i]["client"])
        if len(data[i]["client"]["phone"]) != 0:
            clients.append(data[i]["client"]["id"])
            visit_ids.append(data[i]["visit_id"])
            phones.append(data[i]["client"]["phone"])
    print(visit_ids)
    print(clients)
    print(phones)
    print(len(visit_ids))
    return visit_ids


def findalltrans():

    url = "https://api.yclients.com/api/v1/chain/767469/loyalty/transactions"
    payload = json.dumps({
        "created_after": f"{now}",
        "created_before": f"{now}",
        "type": 9,
        "count":1000
    })
    response = requests.request("GET", url, headers=headers, data=payload)
    pr_response = response.json()
    return pr_response

def parserloyal(data):
    visit_ids = []
    for i in range(len(data)):
        visit_ids.append(data[i]["visit_id"])
    # print(visit_ids)
    return visit_ids

def prefind():
    global dataset
    global transaction_data
    global visits
    global loyalty_visits

    dataset = findallrec()
    transaction_data = findalltrans()

    visits = parserdata(dataset["data"])
    print(f"Получено визитов: {len(visits)}")

    loyalty_visits = parserloyal(transaction_data["data"])
    print(f"Получено визитов из лояльности: {len(loyalty_visits)}")

    visits = [x for x in visits if x not in loyalty_visits]

    print(f"Визиты ({len(visits)})шт, в которых нет по какой то причине использования абонемента: \n {visits}")


# 2 часть. Начинаем забирать клиентов / их абики


def parsernew(data): # выбираю данные по тем визитам которые не обнаружились в транзакциях лояльности в сети, чтобы дальше работать  с этим списком
    for i in range(len(data)):
        if data[i]["visit_id"] in visits:
            print(data[i]["client"])
            data_list[i]["client"] = data[i]["client"]["name"]
            data_list[i]["phone"] = data[i]["client"]["phone"]
            data_list[i]["doc_id"] = data[i]["documents"][0]["id"]
            data_list[i]["services"] = data[i]["services"][0]["id"]
            data_list[i]["date"] = data[i]["date"]
            data_list[i]["paidstat"] = data[i]["paid_full"]
            data_list[i]["url"] = f"https://yclients.com/timetable/{salon_id}#main_date={now}&open_modal_by_record_id={data[i]['id']}"
        data_list.append({})



def checkloyalty(data):
    for i in range(len(data)):
        phones = data[i]["phone"]
        # print(f"итерация: {i}, телефон: {phones}")
        payload = {}
        url = f"https://api.yclients.com/api/v1/loyalty/abonements/?company_id={salon_id}&phone={phones}"
        response = requests.request("GET", url, headers=headers, data=payload)
        response_json = response.json()
        if len(response_json["data"]) == 0:
            data_list[i]["check_res"] = "Абонемента нет у клиента"
        else:
            numbers = []
            ids = []
            services = []
            for j in range(len(response_json["data"])):
                numbers.append(response_json["data"][j]["number"])
                ids.append(response_json["data"][j]["id"])
                print(response_json["data"][j]["balance_container"])
                for k in range(len(response_json["data"][j]["balance_container"]["links"])):
                    services.append(response_json["data"][j]["balance_container"]["links"][k]["service"]["id"])
            data_list[i]["check_res"] = f'Есть абонемент'
            data_list[i]["ab_data"] = {}
            data_list[i]["ab_data"]["id"] = ids
            data_list[i]["ab_data"]["services"] = services
            data_list[i]["ab_data"]["number"] = numbers
        print(response_json)


def payment(doc_id, abon_id, abon_num, counter):
    url = f"https://api.yclients.com/api/v1/company/{salon_id}/sale/{doc_id}/payment"
    print(url)
    print(abon_id)
    print(abon_num)
    payload = json.dumps({
        "payment": {
            "method": {
                "slug": "loyalty_abonement",
                "loyalty_abonement_id": abon_id
            },
            "number": f"{abon_num}"
        }
    })
    response = requests.request("POST", url, headers=p_headers, data=payload)
    pr_response = response.json()
    print(pr_response)
    new_data_list[counter]["pay_res"] = pr_response["meta"]


def read_db(date):
    with open('db.json', 'r') as file:
        file_content = file.read()
    f = file_content + '\n}'
    dict = eval(f)
    if date in dict:
        return dict[date]
    else:
        return False

def save_db():
    if read_db(now) == False:
        f = open('db.json', 'a')
        out = json.dumps(new_data_list, ensure_ascii=False)
        f.write(", \n ")
        f.write(f'"{now}" : {out}')
        f.write("\n")
        f.close()

def start(arg):
    time = datetime.datetime.now()
    print(f"\n запуск start {time} с аргументом {arg}")
    global now
    if arg == 1:
        now = datetime.date.today()
    else:
        now = arg
    prefind()
    global dataset
    global data_list
    global new_data_list
    # print(dataset)
    data_list = [{}]
    parsernew(dataset["data"])
    data_list = [lst for lst in data_list if lst]
    print(data_list)
    print(len(data_list))
    checkloyalty(data_list)
    print("Новый даталист:")
    print(data_list)
    print("Еще один новый список, у кого paidfull != 1")
    new_data_list = list(filter(lambda x: x['paidstat'] != 1, data_list))
    print(len(new_data_list))
    print(new_data_list)
    for i in range(len(new_data_list)):
        if new_data_list[i]["check_res"] == "Есть абонемент":
            print(new_data_list[i]["doc_id"], new_data_list[i]["ab_data"]["id"][0], new_data_list[i]["ab_data"]["number"][0], i)
            payment(new_data_list[i]["doc_id"], new_data_list[i]["ab_data"]["id"][0], new_data_list[i]["ab_data"]["number"][0], i)
    save_db()
    return new_data_list




app.config['JOBS'] = [
    {
        'id': 'job1',
        'func': start,
        'args': ("1",),
        'trigger': 'cron',
        'hour': 22,
        'minute': 30
    }
]

# Запуск планировщика
scheduler.init_app(app)
scheduler.start()


@app.route('/autopayments', methods=['GET', 'POST'])
def ap():
    if request.method == 'POST':
        inputdata = str(request.form.get('cal'))
        print(inputdata)
        hist_list = read_db(inputdata)
        return render_template('logs.html', data_list=hist_list, now=inputdata, enddata=now)
    if request.method == 'GET':
        return render_template('logs.html', data_list=new_data_list, now=now, enddata=now)

@app.route('/autopaymentslog')
def autolog():
        f = open('stdout.txt', 'r')
        text = f.read()
        return f'''<h3> stdout </h3>
{text}
        '''


@app.route('/autopaymentsforce', methods=['GET', 'POST'])
def force():
    if request.method == 'POST':
        inputdata = request.form.get('data')
        print(inputdata)
        if inputdata == "":
            output = start(1)
        else:
            output = start(inputdata)
        return f"<h1>OK</h1>{output}"

    return f'''
              <form id="" method="post" class="form-horizontal">
    <label class="col-xs-3 control-label">Выберите дату</label>
        <input type="date" class="form-control" name="data" min = "2023-02-28" max = "{datetime.date.today()}" />
    <button type="submit" class="btn btn-default">Показать</button>
</form>'''


@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        inputdata = str(request.form.get('cal'))
        print(inputdata)
        hist_list = read_db(inputdata)
        return render_template('logs.html', data_list=hist_list, now=inputdata, enddata=now)
    if request.method == 'GET':
        return render_template('selenium.html',)


if __name__ == '__main__':
    app.run()

