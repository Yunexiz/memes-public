from flask import Flask
from threading import Thread

app = Flask(__name__)


@app.route('/')
def home():
    return "Hello World!"


def run():
    app.run(host='0.0.0.0', port=5000)


def keep_alive():
    t = Thread(target=run)
    t.start()

# after this do "from (file name withoout the .py extension) import keep_alive"- at the top, then right before #bot.run(os.get.env("TOKEN")) do keep_alive()
