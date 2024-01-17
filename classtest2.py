import _thread
import time
import datetime
import websocket
import requests

candle_classes = set()


class candle:

    def __init__(self, pairing_name):
        self.pairing = pairing_name
        self.candle_list = []
        self.high = 0
        self.low = 0
        self.open = 0
        self.close = 0
        self.last_mark = 0
        self.trade_setup = False
        self.negative_slope = False
        self.setup_position = False

    def new_message(self, message):
        message = message.replace('[', "")
        message = message.replace(']', "")
        message = message.replace('"', "")
        new_list = message.split(",")
        last_ask = float(new_list[2])
        last_bid = float(new_list[1])
        self.last_mark = (last_ask + last_bid)/2
        if self.open == 0:
            self.open = self.last_mark
            self.close = self.last_mark
            self.high = self.last_mark
            self.low = self.last_mark
        else:
            if self.last_mark > self.high:
                self.high = self.last_mark
            if self.last_mark < self.low:
                self.low = self.last_mark

    def append_candle(self):
        if self.open != 0:
            self.close = self.last_mark
            data = [time.time(), self.open, self.close, self.high, self.low]
            self.candle_list.append(data)
            self.open = self.last_mark
            self.high = self.last_mark
            self.low = self.last_mark
        if len(self.candle_list) > 1400:
            sma_list = get_sma(self.candle_list, 621, 2)
            if ((sma_list[-720]) * 1.0025) > sma_list[-1] > ((sma_list[-720]) * .9975) and ((sma_list[-720]) * 1.0025) > sma_list[-360] > ((sma_list[-720]) * .9975) and ((sma_list[-360]) * 1.0025) > sma_list[-1] > ((sma_list[-360]) * .9975):
                if self.last_mark < sma_list[-1] and not self.trade_setup:
                    self.trade_setup = True
                    ts = time.time()
                    st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    print(str(st) + ': trade setup for: ' + self.pairing)
            elif self.trade_setup:
                self.trade_setup = False
                ts = time.time()
                st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                print(str(st) + ': cancel setup for: ' + self.pairing)
    def get_rsi(self, period):
        if len(self.candle_list) >= period:
            up_list = []
            down_list = []
            for x in range(period):
                if self.candle_list[(-1 - x)][1] > self.candle_list[(-1 - x)][2]:
                    price_diff = self.candle_list[(-1 - x)][1] - self.candle_list[(-1 - x)][2]
                    down_list.append(price_diff)
                elif self.candle_list[(-1 - x)][2] > self.candle_list[(-1 - x)][1]:
                    price_diff = self.candle_list[(-1 - x)][2] - self.candle_list[(-1 - x)][1]
                    up_list.append(price_diff)
                else:
                    pass
            if len(up_list) > 0:
                up_avg = sum(up_list) / period
            else:
                up_avg = 0
            if len(down_list) > 0:
                down_avg = sum(down_list) / period
            else:
                down_avg = 0
            if up_avg == 0:
                rsi_last = 0
            elif down_avg == 0:
                rsi_last = 100
            else:
                rsi_last = 100 - (100 / (1 + (up_avg / down_avg)))
            if up_avg == 0 and down_avg == 0:
                rsi_last = 50
            return rsi_last
        else:
            print('not enough data to build index')
            return 50


def get_sma(minute_list, lengthlst, pos):
    total = 0
    sma_list = []
    if len(minute_list) >= lengthlst:
        if len(minute_list) == lengthlst:
            for n in range(lengthlst):
                total += minute_list[len(minute_list) - n - 1][pos]
            sma_list.append(total / lengthlst)
            return sma_list
        else:
            for n in range(len(minute_list) - lengthlst):
                for n2 in range(lengthlst):
                    total += minute_list[n2 + n][pos]
                sma_list.append(total/lengthlst)
                total = 0
            return sma_list


def ws_message(ws, message):
    if 'heartbeat' in message:
        pass
    else:
        for objects in candle_classes:
            if objects.pairing in message:
                objects.new_message(message)


def ws_thread(*args):
    ws = websocket.WebSocketApp("ws://127.0.0.1:7890", on_message=ws_message)
    ws.run_forever(ping_interval=30)


def main():
    appending = False
    counter = 0
    temp_list = ['"XMR/USD"', '"STORJ/USD"', '"ETH/USD"', '"ETHW/USD"', '"SHIB/USD"', '"SOL/USD"', '"FTM/USD"',
                 '"MATIC/USD"', '"LINK/USD"', '"TIA/USD"', '"AVAX/USD"', '"DOT/USD"', '"ADA/USD"', '"LTC/USD"',
                 '"DYDX/USD"', '"RNDR/USD"', '"LDO/USD"', '"RUNE/USD"', '"SUSHI/USD"', '"NEAR/USD"', '"ARB/USD"',
                 '"EOS/USD"', '"ATOM/USD"', '"YFI/USD"', '"INJ/USD"', '"AAVE/USD"', '"XRP/USD"', '"QNT/USD"',
                 '"BLUR/USD"', '"FIL/USD"', '"OCEAN/USD"', '"XLM/USD"', '"UNI/USD"', '"SUPER/USD"',
                 '"APT/USD"', '"MANA/USD"', '"IMX/USD"', '"ICP/USD"', '"GRT/USD"', '"OP/USD"',
                 '"SAND/USD"', '"MKR/USD"', '"LUNA/USD"', '"FET/USD"', '"STX/USD"', '"MINA/USD"', '"APE/USD"']
    for x in range(len(temp_list)):
        class_obj = candle(temp_list[x])
        candle_classes.add(class_obj)

    _thread.start_new_thread(ws_thread, ())
    while True:
        time.sleep(.25)
        if datetime.datetime.now().second == 0 and not appending:
            counter += 1
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            appending = True
            for objects in candle_classes:
                objects.append_candle()
                if len(objects.candle_list) > 34:
                    if objects.get_rsi(34) < 15 and objects.get_rsi(34) != 0 and objects.trade_setup and not objects.setup_position:
                        objects.setup_position = True
                        ticker = objects.pairing
                        ticker = ticker.replace('"', "")
                        value = 80/objects.last_mark
                        value = round(value, 5)
                        print(str(st) + ' ######  setting up for autotrade')
                        requests.get('http://127.0.0.1:5001/load?ticker=' + ticker + '&value=' + str(value))
                        requests.post('http://127.0.0.1:5001/buy')
        if datetime.datetime.now().second == 59:
            appending = False
        if counter == 600:
            counter = 0
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            for objects in candle_classes:
                if objects.setup_position:
                    objects.setup_position = False
                    print(str(st) + 'reseting trade setup for : ' + str(objects.pairing))


main()
