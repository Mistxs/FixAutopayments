from flask import Flask
from flask_apscheduler import APScheduler
import datetime

app = Flask(__name__)
scheduler = APScheduler()

def start():
    now = datetime.datetime.now()
    print("Функция start() была запущена в ", now)

# Настройки для выполнения заданий APScheduler
app.config['JOBS'] = [
    {
        'id': 'job1',
        'func': start,
        'trigger': 'cron',
        'hour': 20,
        'minute': 41
    }
]

# Запуск планировщика
scheduler.init_app(app)
scheduler.start()

# Ваш код для Flask-приложения
@app.route('/')
def index():
    return 'Flask-приложение работает!'

if __name__ == '__main__':
    app.run()