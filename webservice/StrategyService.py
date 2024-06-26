from flask import Flask, render_template, request
from random import randrange
import random
import string
import base64
import datetime
import hashlib
import hmac
import json
import time
import urllib.parse
import requests
import _thread
import websocket

strategy_classes = set()
strategy_limit = 15
app = Flask(__name__)
config = {}
ticker = ''
value = 0
quantity_mod = 0


class Strategy:
    def __init__(self, pairing, quantity, api_public_key, api_private_key):
        self.pairing = pairing
        self.quantity = quantity
        self.last_mark = 0
        self.old_mark = 0
        self.side = ""
        self.side_value = 1
        self.upside = 0
        self.downside = 0
        self.in_position = False
        self.api_public_key = api_public_key
        self.api_private_key = api_private_key
        self.entry_price = 0
        self.exit_price = 0
        self.minimum_margin = 1.08
        self.reentry_price = 0
        self.side_modifier = 1.2

    def new_message(self, message):
        message = message.replace('[', "")
        message = message.replace(']', "")
        message = message.replace('"', "")
        new_list = message.split(",")
        last_ask = float(new_list[2])
        last_bid = float(new_list[1])
        self.last_mark = (last_ask + last_bid)/2
        self.get_side()

    def get_side(self):
        if self.in_position:
            if self.last_mark > (self.entry_price * self.side_modifier):
                self.side_value += 3
                self.side_modifier += .2
        if self.last_mark < self.entry_price * (2 - self.minimum_margin):
            self.minimum_margin += .02
        if self.old_mark == 0:
            self.old_mark = self.last_mark
        elif self.last_mark > self.old_mark:
            percentage = ((float(self.last_mark) - float(self.old_mark)) / float(self.last_mark)) * 100
            self.old_mark = self.last_mark
            self.upside += percentage
            if self.downside > 0:
                self.downside -= percentage
                if self.downside < 0:
                    self.downside = 0
            if self.upside > self.side_value:
                self.upside = 0
                self.side = "up"
                self.set_position()
        elif self.last_mark < self.old_mark:
            percentage = ((float(self.old_mark) - float(self.last_mark)) / float(self.old_mark)) * 100
            self.old_mark = self.last_mark
            self.downside += percentage
            if self.upside > 0:
                self.upside -= percentage
                if self.upside < 0:
                    self.upside = 0
            if self.downside > self.side_value:
                self.downside = 0
                self.side = "down"
                self.set_position()

    def set_position(self):
        if self.side == 'up':
            if self.exit_price != 0:
                if self.last_mark < self.reentry_price:
                    if not self.in_position:
                        ts = time.time()
                        st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                        self.side_value = 3
                        self.in_position = True
                        self.entry_price = self.last_mark
                        resp = kraken_request('/0/private/AddOrder', {
                            "nonce": str(int(1000 * time.time())),
                            "ordertype": "market",
                            "type": "buy",
                            "volume": self.quantity,
                            "pair": self.pairing
                        }, self.api_public_key, self.api_private_key)
                        print(str(st) + ' buying ' + self.pairing + "@ " + str(self.last_mark) + " quantity " + str(
                            self.quantity))
                        print(resp)
            else:
                if not self.in_position:
                    ts = time.time()
                    st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    self.side_value = 3
                    self.in_position = True
                    self.entry_price = self.last_mark
                    resp = kraken_request('/0/private/AddOrder', {
                        "nonce": str(int(1000 * time.time())),
                        "ordertype": "market",
                        "type": "buy",
                        "volume": self.quantity,
                        "pair": self.pairing
                    }, self.api_public_key, self.api_private_key)
                    print(str(st) + ' buying ' + self.pairing + "@ " + str(self.last_mark) + " quantity " + str(
                        self.quantity))
                    print(resp)
        elif self.side == 'down':
            if self.in_position:
                if self.last_mark > self.entry_price * self.minimum_margin:
                    ts = time.time()
                    st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    self.in_position = False
                    self.exit_price = self.last_mark
                    resp = kraken_request('/0/private/AddOrder', {
                        "nonce": str(int(1000 * time.time())),
                        "ordertype": "market",
                        "type": "sell",
                        "volume": self.quantity,
                        "pair": self.pairing
                    }, self.api_public_key, self.api_private_key)
                    print(str(st) + ' selling ' + self.pairing + " @ " + str(self.last_mark) + " quantity " + str(self.quantity))
                    print(resp)
                    if self.exit_price > (self.entry_price * 1.14):
                        print('profit')
                        self.reentry_price = (self.entry_price + self.exit_price + (self.exit_price * (self.side_value / 100))) / 2
                        self.side_value = 1
                        self.minimum_margin = 1.1
                        if self.exit_price > (self.entry_price * 1.20):
                            self.quantity = round(self.quantity * 1.01, 5)
                            print('quantity moded')
                    elif self.exit_price >= (self.entry_price * 1.08):
                        print('less profit')
                        strategy_classes.remove(self)


def get_config():
    global config
    with open('config.txt', 'r') as f:
        config = json.loads(f.read())
        f.close()


def get_kraken_signature(urlpath, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()


# Attaches auth headers and returns results of a POST request
def kraken_request(uri_path, data, api_key, api_sec):
    global config
    api_path = config['api_path']
    headers = {}
    headers['API-Key'] = api_key
    # get_kraken_signature() as defined in the 'Authentication' section
    headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)
    req = requests.post((api_path + uri_path), headers=headers, data=data)
    return req


@app.route("/raise_size", methods=['POST'])
def raise_size():
    global quantity_mod
    quantity_mod += .1
    print(quantity_mod)
    return '', 204


@app.route("/decrease_size", methods=['POST'])
def decrease_size():
    global quantity_mod
    quantity_mod -= .1
    print(quantity_mod)
    return '', 204


@app.route("/raise_limit", methods=['POST'])
def raise_limit():
    global strategy_limit
    strategy_limit += 1
    print(strategy_limit)
    return '', 204


@app.route("/decrease_limit", methods=['POST'])
def decrease_limit():
    global strategy_limit
    strategy_limit -= 1
    print(strategy_limit)
    return '', 204


@app.route("/load")
def load():
    global ticker, value
    ticker = request.args.get('ticker')
    value = request.args.get('value')
    return render_template("index1.html")


@app.route("/load_trades", methods=['POST'])
def load_trades():
    global config
    api_public_key = config['api_public_key']
    api_private_key = config['api_private_key']
    with open('trades.txt', 'r') as f:
        stringt = f.read()
        list_str = stringt.splitlines()
        f.close()
        for strings in list_str:
            try:
                json_dict = json.loads(strings)
                new_strategy = Strategy(json_dict['pairing'], round(json_dict['quantity'], 5), api_public_key, api_private_key)
                new_strategy.side_value = json_dict['side_value']
                new_strategy.entry_price = json_dict['entry_price']
                new_strategy.exit_price = json_dict['exit_price']
                new_strategy.side_modifier = json_dict['side_modifier']
                new_strategy.reentry_price = json_dict['reentry_price']
                new_strategy.minimum_margin = round(json_dict['minimum_margin'], 2)
                if json_dict['in_position']:
                    new_strategy.in_position = True
                if not json_dict['in_position']:
                    new_strategy.in_position = False
                strategy_classes.add(new_strategy)
            except ValueError:
                print(ValueError)
    return '', 204


@app.route("/save_trades", methods=['POST'])
def save_trades():
    new_string = ""
    x = 0
    for objects in strategy_classes:
        if x == 0:
            new_string += "{"
            new_string += '"' + "pairing" + '"' + ": "
            new_string += '"' + objects.pairing + '", '
            new_string += '"' + "quantity" + '"' + ": "
            new_string += str(objects.quantity) + ", "
            new_string += '"' + "side_value" + '"' + ": "
            new_string += str(objects.side_value) + ", "
            new_string += '"' + "entry_price" + '"' + ": "
            new_string += str(objects.entry_price) + ", "
            new_string += '"' + "exit_price" + '"' + ": "
            new_string += str(objects.exit_price) + ", "
            new_string += '"' + "minimum_margin" + '"' + ": "
            new_string += str(objects.minimum_margin) + ", "
            new_string += '"' + "reentry_price" + '"' + ": "
            new_string += str(objects.reentry_price) + ", "
            new_string += '"' + "side_modifier" + '"' + ": "
            new_string += str(objects.side_modifier) + ", "
            new_string += '"' + "in_position" + '"' + ": "
            if objects.in_position:
                new_string += 'true'
            if not objects.in_position:
                new_string += 'false'
            new_string += "}"
            x += 1
        else:
            new_string += "\n"
            new_string += "{"
            new_string += '"' + "pairing" + '"' + ": "
            new_string += '"' + objects.pairing + '", '
            new_string += '"' + "quantity" + '"' + ": "
            new_string += str(objects.quantity) + ", "
            new_string += '"' + "side_value" + '"' + ": "
            new_string += str(objects.side_value) + ", "
            new_string += '"' + "entry_price" + '"' + ": "
            new_string += str(objects.entry_price) + ", "
            new_string += '"' + "exit_price" + '"' + ": "
            new_string += str(objects.exit_price) + ", "
            new_string += '"' + "minimum_margin" + '"' + ": "
            new_string += str(objects.minimum_margin) + ", "
            new_string += '"' + "reentry_price" + '"' + ": "
            new_string += str(objects.reentry_price) + ", "
            new_string += '"' + "side_modifier" + '"' + ": "
            new_string += str(objects.side_modifier) + ", "
            new_string += '"' + "in_position" + '"' + ": "
            if objects.in_position:
                new_string += 'true'
            if not objects.in_position:
                new_string += 'false'
            new_string += "}"
    with open('trades.txt', 'w') as f:
        f.write(new_string)
        f.close()
    return '', 204


@app.route("/show", methods=['POST'])
def show():
    for objects in strategy_classes:
        print(objects.pairing + ' Position = ' + str(objects.in_position) + " entry: " + str(objects.entry_price) +
              " trailing percentage: " + str(objects.side_value) + " minimum margin: " + str(objects.minimum_margin) +
              " current price: " + str(objects.last_mark) + " side: " + str(objects.side) + " reentry price: " +
              str(objects.reentry_price) + " quantity: " + str(objects.quantity))
    return '', 204

@app.route("/remove")
def remove():
    ticker_local = request.args.get('ticker')
    for objects in set(strategy_classes):
        if ticker_local in objects.pairing:
            strategy_classes.remove(objects)
            print('removing ' + objects.pairing)
    for objects in strategy_classes:
        print(objects.pairing + ' Position = ' + str(objects.in_position))
    return '''<h1Removed pairing </h1>'''


@app.route("/", methods=['GET'])
def home():
    return render_template("home.html")


@app.route("/buy", methods=['POST'])
def buy():
    global ticker, value, strategy_limit, config, quantity_mod
    api_public_key = config['api_public_key']
    api_private_key = config['api_private_key']
    counter = 0
    strategy_counter = 0
    for objects in strategy_classes:
        strategy_counter += 1
        if ticker in objects.pairing:
            counter += 1
            break  # if pairing already in strategy set, break loop and increment counter(no duplicate pairing)
    if counter == 0 and strategy_counter < strategy_limit:
        new_strategy = Strategy(ticker, (float(value) * quantity_mod), api_public_key, api_private_key)
        strategy_classes.add(new_strategy)
        for objects in strategy_classes:
            print(objects.pairing + ' Position = ' + str(objects.in_position))
    return '''<h1>Adding trading strategy for {} </h1>'''.format(ticker)


def ws_message(ws, message):
    if 'heartbeat' in message:
        pass
    else:
        for objects in strategy_classes:
            if objects.pairing in message:
                objects.new_message(message)


def ws_thread(*args):
    ws = websocket.WebSocketApp("ws://127.0.0.1:7890", on_message=ws_message)
    ws.run_forever(ping_interval=30)


if __name__ == '__main__':
    get_config()
    quantity_mod = config['quantity_mod']
    _thread.start_new_thread(ws_thread, ())
    app.run(debug=True, host="127.0.0.1", port=5001)

