#######################
# Author: slurpxbt
#######################

from BybitWebsocket import BybitWebsocket
import time
import logging
import datetime as dt
import binance_candle_data as bcd
import pandas as pd
import pickle
from pathlib import Path
import traceback

def setup_logger():

    # Prints logger info to terminal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Change this to DEBUG if you want a lot more info
    ch = logging.StreamHandler()

    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def get_emas(pair, time_frame):
    # This function prepares you ema for you strategy if you need them
    # 

    candles = bcd.get_candle_data(pair, time_frame, dt.datetime.today()-dt.timedelta(days=90), dt.datetime.today())
    candles["EMA21"] = round(candles["close"].ewm(span=21).mean(), 2)
    candles["EMA50"] = round(candles["close"].ewm(span=50).mean(), 2)
    print(candles)
    del candles["open"]
    del candles["volume"]
    del candles["number_of_trades"]
    del candles["open_time"]
    del candles["close_time"]
    

    return candles


    
def main(client):
    # Websocket subscriptions ------------ 
    client.subscribe_trade()
    client.subscribe_kline("ETHUSD", "1h")
    # -----------------------------------
    

    # -----------------------------------------------------------------------------------------------------------------------------
    # this is done in order to get the latest EMA values
    # get hourly candle data
    candle_data = get_emas("ETHUSDT", "1h")

    last_candle_close = candle_data.iloc[-1]
    close = last_candle_close["close"]
    ema21 = last_candle_close["EMA21"]
    ema50 = last_candle_close["EMA50"]
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

     # STRATEGY VARS
    signal = False
    signal_side = ""
    trade_opened = False
    start_size = 5000
    pos_size = start_size
    market_order_fee = 0.075            # unit [%]
    slippage = 0                        # unit [%]
    tp_pct = 0.01                       # unit => 1 - 100%, 0.1 - 10%, 0.01 - 1%
    hard_stop = -(pos_size * 0.05)      # unit $ cut position if lose is equal to 5% of portfolio
    compounding = True

    pnl_file_path = "ema21_50_PNL"      # file for storing pnl data
    root = Path(".")
    while True: 

        # websocket ping -----------------------------
        cur_time = dt.datetime.utcnow().time()

        # this keeps connection alive
        if cur_time.second == ping_sec[ping_index]:
            client.ping()
            ping_index +=1

            if ping_index == 3:
                ping_index = 0
        # --------------------------------------------

        # Data Requests --------------------
        trade_data = client.get_data("trade.ETHUSD")
        kline = client.get_data("kline.ETHUSD.1h")
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
                

                # YOUR STRATEGY -------------------------------------------------------------------------------------
                # If there is trade signal execute trade
                if signal:
                    signal = False
                    
                    if signal_side == "long":
                        trade_opened = True
                        trade_entry = price
                        tp = round(trade_entry + (trade_entry * tp_pct), 2)                 # tp based on % gain from entry
                        print(f"long entry @ {trade_entry} with tp @ {tp} -> size {pos_size}")

                        # This is used for tracking pnl and trade statistics
                        trade_data = [signal_side, current_time, trade_entry]

                    elif signal_side == "short":
                        trade_opened = True
                        trade_entry = price
                        tp = round(trade_entry - (trade_entry * tp_pct), 2)                  # tp based on % gain from entry
                        print(f"short entry @ {trade_entry} with tp @ {tp} -> size {pos_size}")

                        # This is used for tracking pnl and trade statistics
                        trade_data = [signal_side, current_time, trade_entry]


                # IF trade is opened search for tp/sl
                if trade_opened:

                    # LONG TRADE
                    if signal_side == "long":
                        # LONG HARD STOP
                        gain = round((price / trade_entry - 1) * 100 - market_order_fee - slippage, 2)
                        trade_profit = gain * pos_size / 100

                        if trade_profit <= hard_stop:
                            gain = round((price / trade_entry - 1) * 100 - market_order_fee - slippage, 2)
                            trade_profit = hard_stop
                            tmp_txt = "hard_stop"  

                            exit_price = price
                            trade_data.append(exit_price)
                            trade_data.append(trade_profit)
                            trade_data.append(gain)
                            trade_data.append(tmp_txt)


                            if compounding:  # if this is True it calculates compounding profits
                                pos_size = pos_size + trade_profit

                          
                            print(f"HARD STOP executed @ {price} -> gain {gain}% -> profit {trade_profit} $")
                            trade_opened = False
                            print("-" * 100)
                            # FORMAT = [signal_side, current_time, trade_entry], exit_price, trade_profit, gain, tmp_txt]
                            pickle.dump(trade_data, open(f"{root}/{pnl_file_path}.p", "ab"))
                            signal = False

                        else:
                            # LONG TP
                            if price >= tp:
                                gain = round((tp / trade_entry - 1) * 100 - market_order_fee - slippage,2)      # pct gain includes market order fee
                                trade_profit = gain * pos_size / 100                                            # take profit takes into account % gain (that's why /100)
                                tmp_txt = "tp"

                                exit_price = price
                                trade_data.append(exit_price)
                                trade_data.append(trade_profit)
                                trade_data.append(gain)
                                trade_data.append(tmp_txt)

                                if compounding:                   # if this is True it calculates compounding profits
                                    pos_size = pos_size + trade_profit
                   
                                print(f"tp executed @ {tp} -> gain {gain}% -> profit {trade_profit} $")
                                trade_opened = False
                                print("-" * 100)
                                # FORMAT = [signal_side, current_time, trade_entry], exit_price, trade_profit, gain, tmp_txt]
                                pickle.dump(trade_data, open(f"{root}/{pnl_file_path}.p", "ab"))
                                signal = False

                            # LONG SL
                            elif close < ema21 and close < ema50:
                                gain = round((price / trade_entry - 1) * 100 - market_order_fee - slippage, 2)
                                trade_profit = gain * pos_size / 100
                                tmp_txt = "stop_loss"

                                exit_price = price
                                trade_data.append(exit_price)
                                trade_data.append(trade_profit)
                                trade_data.append(gain)
                                trade_data.append(tmp_txt)

                                if compounding:                   # if this is True it calculates compounding profits
                                    pos_size = pos_size + trade_profit

                               
                                print(f"sl executed @ {price} -> gain {gain}% -> profit {trade_profit} $")
                                trade_opened = False
                                print("-" * 100)
                                # FORMAT = [signal_side, current_time, trade_entry], exit_price, trade_profit, gain, tmp_txt]
                                pickle.dump(trade_data, open(f"{root}/{pnl_file_path}.p", "ab"))
                                signal = False

                    # SHORT TRADE
                    elif signal == "short":
                        # SHORT HARD STOP
                        gain = round((price / trade_entry - 1) * 100 * (-1) - market_order_fee - slippage, 2)
                        trade_profit = gain * pos_size / 100
                        print("-" * 100, trade_profit, "current close=", price, "entry", trade_entry)

                        if trade_profit <= hard_stop:
                            gain = round((price / trade_entry - 1) * 100 * (-1) - market_order_fee - slippage, 2)
                            trade_profit = hard_stop
                            tmp_txt = "hard_stop"  

                            exit_price = price
                            trade_data.append(exit_price)
                            trade_data.append(trade_profit)
                            trade_data.append(gain)
                            trade_data.append(tmp_txt)
                            
                            if compounding:  # if this is True it calculates compounding profits
                                pos_size = pos_size + trade_profit
                            

                            print(f"HARD STOP executed @ {price} -> gain {gain}% -> profit {trade_profit} $")
                            trade_opened = False
                            print("-" * 100)

                            # FORMAT = [signal_side, current_time, trade_entry], exit_price, trade_profit, gain, tmp_txt]
                            pickle.dump(trade_data, open(f"{root}/{pnl_file_path}.p", "ab"))
                            signal = False

                        else:
                            # SHORT TP
                            if price <= tp:
                                gain = round((tp / trade_entry - 1) * 100 * (-1) - market_order_fee - slippage, 2)      # pct gain includes market order fee
                                trade_profit = gain * pos_size / 100                                                        # take profit takes into account % gain (that's why /100)

                                tmp_txt = "tp"

                                exit_price = price
                                trade_data.append(exit_price)
                                trade_data.append(trade_profit)
                                trade_data.append(gain)
                                trade_data.append(tmp_txt)


                                if compounding:                   # if this is True it calculates compounding profits
                                    pos_size = pos_size + trade_profit
                                
                                print(f"tp executed @ {tp} -> gain {gain}% -> profit {trade_profit} $")
                                trade_opened = False
                                print("-"*100)

                                # FORMAT = [signal_side, current_time, trade_entry], exit_price, trade_profit, gain, tmp_txt]
                                pickle.dump(trade_data, open(f"{root}/{pnl_file_path}.p", "ab"))
                                signal = False


                            # SHORT SL
                            elif close > ema21 and close > ema50:
                                gain = round((price / trade_entry - 1) * 100 * (-1) - market_order_fee - slippage, 2)
                                trade_profit = gain * pos_size / 100

                                tmp_txt = "stop_loss"

                                exit_price = price
                                trade_data.append(exit_price)
                                trade_data.append(trade_profit)
                                trade_data.append(gain)
                                trade_data.append(tmp_txt)
                           
                                if compounding:                   # if this is True it calculates compounding profits
                                    pos_size = pos_size + trade_profit
                          

                                print(f"sl executed @ {price} -> gain {gain}% -> profit {trade_profit} $")
                                trade_opened = False
                                print("-" * 100)

                                # FORMAT = [signal_side, current_time, trade_entry], exit_price, trade_profit, gain, tmp_txt]
                                pickle.dump(trade_data, open(f"{root}/{pnl_file_path}.p", "ab"))
                                signal = False

                
        if kline:
            candle_close = kline["close"]
            candle_high = kline["high"]
            candle_low = kline["low"]
            
           


        # Intervall prints
        if cur_time.second % 20 == 0 and cur_time.second != sec_  and data_received:
            
            sec_ = cur_time.second
            
            if trade_opened:
                print(f"<{curret_date} {cur_time.strftime('%H:%M:%S')} UTC> -> price: {price} => current trade gain: {gain} % => current trade profit {trade_profit} => size {pos_size}") 
            else:
                print(f"<{curret_date} {cur_time.strftime('%H:%M:%S')} UTC> -> price: {price}") 


        # candle close saving
        if "current_time" in locals():
            if hour_ != current_time.hour and data_received:
                    print("-"*100, "NEW HOUR")
                    hour_ = current_time.hour


                    # THIS CALCULATES NEW EMA VALUES
                    candle_data = candle_data.append({'high':candle_high,'low':candle_low ,'close': candle_close , 'EMA21' : 0, "EMA50":0} , ignore_index=True)
                    candle_data["EMA21"] = round(candle_data["high"].ewm(span=21).mean(), 2)
                    candle_data["EMA50"] = round(candle_data["low"].ewm(span=50).mean(), 2)

                    last_candle_close = candle_data.iloc[-1]
                    close = last_candle_close["close"]
                    ema21 = last_candle_close["EMA21"]
                    ema50 = last_candle_close["EMA50"]

                    print(f"NEW HOUR: close {close} --> ema21 {ema21} --> ema50 {ema50}")

                    # HERE GOES YOU SIGNAL SEARCH IF IT BASED ON CANDLE CLOSES
                    # search for signal
                    if trade_opened == False and signal == False:
                        if close > ema21 and close > ema50:
                            signal = True
                            signal_side = "long"

                        elif close < ema21 and close < ema50:
                            signal = True
                            signal_side = "short"
                        else:
                            signal = False
                            signal_side = "No signal"

                        print(f"SIGNAL => {signal_side}")

                   

            

            
                

        time.sleep(0.05)

if __name__ == "__main__":
    logger = setup_logger()
    
    while True:
        
        try:
            ws = BybitWebsocket(wsURL="wss://stream.bybit.com/realtime",api_key="", api_secret="")
            main(ws)
        
        except KeyboardInterrupt:
            ws.exit()
            logger.info("Manually closed datastream")
            break

        except Exception as e:
            logger.info("Exception thrown")
            logger.info(e)
            print("-"*100)
            print("TRACEBACK")
            traceback.format_exc()
            print("-"*100)
            time.sleep(3)
    


        