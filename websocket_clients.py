# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import _thread
import time
import socket
import websocket


last_time = time.time()
messages = ""
new_message = False


def check_internet():  # checking if internet is available
    try:
        host = socket.gethostbyname('ws.kraken.com')  # sets up address in socket
        con = socket.create_connection((host, 80), 2)  # try to connect to address
        socket.close()
        return True
    except Exception:  # if con trows exception, check_internet returns false
        return False


def ws_message(ws, message):
    global last_time
    global messages
    global new_message
    messages = message
    new_message = True
    last_time = time.time()


def ws_open(ws):
    ws.send('{"event":"subscribe", "subscription":{"name":"spread"}, "pair":["XMR/USD", "STORJ/USD", "ETH/USD",'
            ' "ETHW/USD", "SHIB/USD", "SOL/USD", "FTM/USD", "MATIC/USD", "LINK/USD", "TIA/USD", "QNT/USD", '
            ' "DYDX/USD", "RNDR/USD", "LDO/USD", "RUNE/USD", "SUSHI/USD", "NEAR/USD", "ARB/USD", "FET/USD", '
            ' "EOS/USD", "ATOM/USD", "YFI/USD", "AAVE/USD", "INJ/USD", "AVAX/USD", "XRP/USD", "LTC/USD", '
            ' "BLUR/USD", "FIL/USD", "OCEAN/USD", "XLM/USD", "UNI/USD", "MKR/USD", "SUPER/USD", '
            ' "APT/USD", "MANA/USD", "IMX/USD", "ICP/USD", "GRT/USD", "OP/USD", "SAND/USD", '
            ' "DOT/USD", "LUNA/USD", "APE/USD", "STX/USD", "MINA/USD", "ADA/USD"]}')


def ws_close(ws):
    print('socket closed, restarting')
    _thread.start_new_thread(ws_thread, ())


def ws_thread(*args):
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("wss://ws.kraken.com/", on_open=ws_open, on_message=ws_message, on_close=ws_close)
    ws.run_forever(ping_interval=30)


def main():
    global messages
    global new_message
    global last_time
    _thread.start_new_thread(ws_thread, ())
    ws = websocket.WebSocket()
    ws.connect("ws://127.0.0.1:7890")
    while True:
        if time.time() > last_time + 15:  # after 15sec without new message restarting websocket
            print("no websocket connection pausing for 30sec and reconnecting")
            time.sleep(30)
            _thread.start_new_thread(ws_thread, ())
            last_time = time.time()
        if new_message:
            new_message = False
            try:
                ws.send(messages)
            except socket.error as e:
                print(e)
                ws.connect("ws://127.0.0.1:7890")

main()
