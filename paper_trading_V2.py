#######################
# Author: slurpxbt
#######################

import pybit
import time
import logging
import datetime as dt
import binance_candle_data as bcd
import pandas as pd
import pickle
from pathlib import Path
import traceback
import urllib
import websockets
from dhooks import Webhook
import pickle
import os



def get_emas_bybit(pair, time_frame):
    # pair BTCUSD, ETHUSD
    # time_frame = 1 3 5 15 30 60 120 240 360 720 "D" "M" "W"

    # pretvorba trenutni čas do recimo 100 dni nazanj v sekunde
    now = dt.datetime.utcnow()
    if time_frame == "D":
        days_back = now - dt.timedelta(days=int(200/1))
    elif time_frame == "720": 
        days_back = now - dt.timedelta(days=int(200/(24/12)))
    elif time_frame == "240": 
        days_back = now - dt.timedelta(days=int(200/(24/4)))
    



    print(now, "tme_frame:", time_frame)
    print(days_back, "ts:", days_back.timestamp())

    api_client = pybit.HTTP(endpoint='https://api.bybit.com')
    candles = api_client.query_kline(symbol=pair, interval=time_frame, from_time=int(days_back.timestamp()))

    for i in candles["result"]:
        open_time_sec = i["open_time"]
        open_time_dt = dt.datetime.utcfromtimestamp(open_time_sec)
        i["open_time"] = open_time_dt 
        #print(i, open_time_dt, "||", c)
        #c+=1

    kline_df = pd.DataFrame.from_dict(candles["result"])
    kline_df["open"] = pd.to_numeric(kline_df["open"])
    kline_df["high"] = pd.to_numeric(kline_df["high"])
    kline_df["low"] = pd.to_numeric(kline_df["low"])
    kline_df["close"] = pd.to_numeric(kline_df["close"])
    kline_df["EMA21"] = round(kline_df["close"].ewm(span=21).mean(), 2)
    del kline_df["volume"]
    del kline_df["turnover"]
    del kline_df["symbol"]
    del kline_df["interval"]
    kline_df = kline_df[:-1]
    print(kline_df)

    return kline_df

def send_dis_msg(api_key, msg):
    try:
        hook = Webhook(api_key)
    except Exception:
        pass
    
    try:
        hook.send(msg)
    except Exception:
        pass


def main(ws_client, api_client):
   
    
    # -----------------------------------------------------------------------------------------------------------------------------
    # this is done in order to get the latest EMA values
    # get hourly candle data
    candle_data_4h = get_emas_bybit("BTCUSD", "240")
    candle_data_12h = get_emas_bybit("BTCUSD", "720")
    candle_data_1D = get_emas_bybit("BTCUSD", "D") 

    last_candle_close_4h = candle_data_4h.iloc[-1]
    close_4h = last_candle_close_4h["close"]
    ema21_4h = last_candle_close_4h["EMA21"]

    last_candle_close_12h = candle_data_12h.iloc[-1]
    close_12h = last_candle_close_12h["close"]
    ema21_12h = last_candle_close_12h["EMA21"]

    last_candle_close_1D = candle_data_1D.iloc[-1]
    close_1D = last_candle_close_1D["close"]
    ema21_1D = last_candle_close_1D["EMA21"]

    # -----------------------------------------------------------------------------------------------------------------------------
    today = dt.datetime.utcnow()
    day_ = today.date()
    hour_ = today.time().hour
    sec_ = today.time().second
    # -----------------------------------------------------------------------------------
    # ping vars
    ping_index = 0
    ping_sec = [0, 20, 40]
    # -----------------------------------------------------------------------------------
    data_received = False
    first_loop = True
    first_run = True
    trade_opened = False
    # STRATEGY VARS ---------------------------------------------------------------------
   
                    
    root = Path(".")

    while True: 

        # websocket ping -----------------------------
        cur_time = dt.datetime.utcnow().time()

        # risk check
        if cur_time.second == ping_sec[ping_index]:
            ping_index +=1

            if ping_index == 3:
                ping_index = 0
            
        # CODE FOR CHECKING RISK PARAMETERS EVERY 20s

        # --------------------------------------------

        # Data Requests --------------------
        try:
            trade_data = ws_client.fetch("trade.BTCUSD")
        except:
            #dis_msg = f"```Trade data error -> exception ignored```"
            #send_dis_msg(dis_api_key, dis_msg)
            pass
        # --------------------------------------------
        
        if trade_data:  # if data is returned 
            
            data_received = True

            now = dt.datetime.utcnow()

            curret_date = now.date()
            current_time = now.time()

            for trade in trade_data:
                side = trade["side"]
                size = trade["size"]
                price = trade["price"]
                
     
          


        # candle close saving
        if "current_time" in locals():
            if hour_ != current_time.hour and data_received:
                
                        
                hour_ = current_time.hour

                # 4h close
                if hour_ % 4 == 0:
                    print("NEW 4H CLOSE")
                    # UPDATE EMA VALUES HERE
                    if hour_ == 12 or hour_ == 0:
                        print("NEW 12H CLOSE")
                        # UPDATE EMA VALUES HERE
                        if hour_ == 0:
                            print(f"NEW DAILY CLOSE")
                            # UPDATE EMA VALUES HERE
                    

        time.sleep(0.05)


if __name__ == "__main__":
    
    
    while True:
        dis_api_key = ""
        try:
            
            # connect to api
            api_endpoint = "https://api.bybit.com"
            api_client = pybit.HTTP(api_endpoint, api_key="", api_secret="")

            # connect to websocket
            ws_endpoint = "wss://stream.bytick.com/realtime"
            subs = ["trade.BTCUSD"]
            ws = pybit.WebSocket(ws_endpoint, subscriptions=subs)    
            


            dis_msg = "```algo successfully connected to exchange```"
            send_dis_msg(dis_api_key, dis_msg)
            main(ws, api_client)
        
        except KeyboardInterrupt:
            ws.exit()
            dis_msg = "```algo manually closed [keyboard interrupt]```"
            send_dis_msg(dis_api_key, dis_msg)
            break

        except Exception as e:
            traceback.print_exc()
            dis_msg = "```algo disconected from datastream [check algo status] ```"
            send_dis_msg(dis_api_key, dis_msg)
            error = f"```error:{e}```"
            send_dis_msg(dis_api_key, error)
            print("-"*100)
            time.sleep(3)
            
    


        