# paper-trading-for-algorithmic-strategies
module for testing algorithmic strategies on live bybit datastream
 
 <h3>Instructions how to use the script</h3>
 
 <p>Required packages:<p>
 <ul>
   <li>python-binance</li>
   <li>bybit-ws</li>
   <li>pandas</li>
   <li>time</li>
   <li>matplotlib</li>
   <li>numpy</li>
   <li>pickle</li>
   <li>logging</li>
   <li><b>If any other are missing just pip install them</b></li>
 </ul>
 
 <p>How to us paper trading module:</p>
 
1. If you based you strategy on ema or ma edit the <b>get_emas()</b> function with desired ma and emas
   - change lines <b>62</b> and <b>63</b> according to you selected ma/emas
2. Depending on which ticker and timeframe you want to test the strategy change the ticker and timeframe in lines <b>51</b> and <b>58</b>
3. Change strategy variables from line <b>77</b> to <b>86</b>
5. Change the strategy to your strategy from line <b>126</b> onwards
7. Also feel free to explore and change or add any other functions

<b>If you have any question regarding the scripts you can ask me on twitter @slurpxbt</b>
