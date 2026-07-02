//+------------------------------------------------------------------+
//|                                          BrokerDataCollector.mq5 |
//|                        Broker-universal MT5 data collector (v1)  |
//|                     Research / backtesting only — does NOT trade |
//+------------------------------------------------------------------+
#property copyright "Broker Data Collector"
#property version   "1.00"
#property description "Collects broker-specific market data to CSV. No trading."

#define OUTPUT_FOLDER "BrokerDataCollector"
#define CSV_HEADER    "timestamp,broker_name,server,account_login,account_type_company,symbol,timeframe,open,high,low,close,tick_volume,bid,ask,spread_points,spread_price,digits,point"

//--- inputs
input string            InpSymbols       = "BTCUSD,XAUUSD,US100,EURUSD";
input ENUM_TIMEFRAMES   InpTimeframe     = PERIOD_M1;
input int               InpTimerSeconds  = 60;

//--- globals
string   g_symbols[];
datetime g_lastWrittenBarTime[];

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpTimerSeconds < 1)
     {
      Print("BrokerDataCollector: timer interval must be >= 1 second.");
      return INIT_PARAMETERS_INCORRECT;
     }

   if(!ParseSymbolList(InpSymbols, g_symbols))
     {
      Print("BrokerDataCollector: no valid symbols in input list.");
      return INIT_PARAMETERS_INCORRECT;
     }

   ArrayResize(g_lastWrittenBarTime, ArraySize(g_symbols));
   ArrayInitialize(g_lastWrittenBarTime, 0);

   if(!EnsureOutputFolder())
     {
      Print("BrokerDataCollector: failed to create output folder.");
      return INIT_FAILED;
     }

   for(int i = 0; i < ArraySize(g_symbols); i++)
     {
      string symbol = g_symbols[i];
      if(!SymbolSelect(symbol, true))
        {
         Print("BrokerDataCollector: SymbolSelect failed for ", symbol,
               " (error ", GetLastError(), ").");
         continue;
        }

      g_lastWrittenBarTime[i] = ReadLastTimestampFromTodayFile(symbol);
      Print("BrokerDataCollector: tracking ", symbol,
            ", last written bar: ",
            (g_lastWrittenBarTime[i] > 0
             ? TimeToString(g_lastWrittenBarTime[i], TIME_DATE | TIME_SECONDS)
             : "none"));
     }

   if(!EventSetTimer(InpTimerSeconds))
     {
      Print("BrokerDataCollector: EventSetTimer failed (error ", GetLastError(), ").");
      return INIT_FAILED;
     }

   Print("BrokerDataCollector: started. Symbols=", ArraySize(g_symbols),
         ", timeframe=", TimeframeLabel(InpTimeframe),
         ", timer=", InpTimerSeconds, "s");
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Print("BrokerDataCollector: stopped (reason ", reason, ").");
  }

//+------------------------------------------------------------------+
//| Timer handler                                                    |
//+------------------------------------------------------------------+
void OnTimer()
  {
   for(int i = 0; i < ArraySize(g_symbols); i++)
      CollectSymbolBar(i);
  }

//+------------------------------------------------------------------+
//| Collect and persist the latest completed bar for one symbol      |
//+------------------------------------------------------------------+
void CollectSymbolBar(const int symbolIndex)
  {
   string symbol = g_symbols[symbolIndex];

   if(!SymbolSelect(symbol, true))
      return;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);

   // Bar index 1 = last fully closed candle
   int copied = CopyRates(symbol, InpTimeframe, 1, 1, rates);
   if(copied < 1)
     {
      Print("BrokerDataCollector: CopyRates failed for ", symbol,
            " (error ", GetLastError(), ").");
      return;
     }

   datetime barTime = rates[0].time;
   if(barTime <= g_lastWrittenBarTime[symbolIndex])
      return;

   if(!AppendBarRow(symbol, rates[0]))
     {
      Print("BrokerDataCollector: failed to write row for ", symbol, ".");
      return;
     }

   g_lastWrittenBarTime[symbolIndex] = barTime;
  }

//+------------------------------------------------------------------+
//| Append one CSV row (creates file + header when needed)           |
//+------------------------------------------------------------------+
bool AppendBarRow(const string symbol, const MqlRates &bar)
  {
   string fileName = BuildDailyFileName(symbol);
   string filePath = OUTPUT_FOLDER + "\\" + fileName;

   bool isNewFile = !FileIsExist(filePath);
   int handle = FileOpen(filePath, FILE_READ | FILE_WRITE | FILE_ANSI);
   if(handle == INVALID_HANDLE)
     {
      Print("BrokerDataCollector: FileOpen failed for ", filePath,
            " (error ", GetLastError(), ").");
      return false;
     }

   if(isNewFile)
     {
      FileWriteString(handle, CSV_HEADER + "\r\n");
     }
   else
     {
      FileSeek(handle, 0, SEEK_END);
     }

   double bid          = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask          = SymbolInfoDouble(symbol, SYMBOL_ASK);
   int    spreadPoints = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   int    digits       = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double point        = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double spreadPrice  = (ask - bid);

   string row = BuildCsvRow(symbol, bar, bid, ask, spreadPoints, spreadPrice, digits, point);
   FileWriteString(handle, row + "\r\n");
   FileFlush(handle);
   FileClose(handle);
   return true;
  }

//+------------------------------------------------------------------+
//| Build a single CSV data row                                      |
//+------------------------------------------------------------------+
string BuildCsvRow(const string symbol,
                   const MqlRates &bar,
                   const double bid,
                   const double ask,
                   const int spreadPoints,
                   const double spreadPrice,
                   const int digits,
                   const double point)
  {
   string timestamp = TimeToString(bar.time, TIME_DATE | TIME_SECONDS);
   string broker    = TerminalInfoString(TERMINAL_COMPANY);
   string server    = AccountInfoString(ACCOUNT_SERVER);
   long   login     = AccountInfoInteger(ACCOUNT_LOGIN);
   string acctType  = BuildAccountTypeCompany();
   string tf        = TimeframeLabel(InpTimeframe);

   return StringFormat("%s,%s,%s,%I64d,%s,%s,%s,%s,%s,%s,%s,%I64d,%s,%s,%d,%s,%d,%s",
                       timestamp,
                       CsvEscape(broker),
                       CsvEscape(server),
                       login,
                       CsvEscape(acctType),
                       CsvEscape(symbol),
                       tf,
                       DoubleToString(bar.open, digits),
                       DoubleToString(bar.high, digits),
                       DoubleToString(bar.low, digits),
                       DoubleToString(bar.close, digits),
                       bar.tick_volume,
                       DoubleToString(bid, digits),
                       DoubleToString(ask, digits),
                       spreadPoints,
                       DoubleToString(spreadPrice, digits),
                       digits,
                       DoubleToString(point, digits + 2));
  }

//+------------------------------------------------------------------+
//| Account company + trade mode label                               |
//+------------------------------------------------------------------+
string BuildAccountTypeCompany()
  {
   string company = AccountInfoString(ACCOUNT_COMPANY);
   ENUM_ACCOUNT_TRADE_MODE mode = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);

   string modeLabel = "unknown";
   switch(mode)
     {
      case ACCOUNT_TRADE_MODE_DEMO:   modeLabel = "demo"; break;
      case ACCOUNT_TRADE_MODE_CONTEST: modeLabel = "contest"; break;
      case ACCOUNT_TRADE_MODE_REAL: modeLabel = "real"; break;
     }

   if(company == "")
      return modeLabel;
   return company + " (" + modeLabel + ")";
  }

//+------------------------------------------------------------------+
//| Parse comma-separated symbol list                                |
//+------------------------------------------------------------------+
bool ParseSymbolList(const string raw, string &symbols[])
  {
   string parts[];
   int count = StringSplit(raw, ',', parts);
   if(count < 1)
      return false;

   ArrayResize(symbols, 0);

   for(int i = 0; i < count; i++)
     {
      string sym = Trim(parts[i]);
      if(sym == "")
         continue;

      int n = ArraySize(symbols);
      ArrayResize(symbols, n + 1);
      symbols[n] = sym;
     }

   return ArraySize(symbols) > 0;
  }

//+------------------------------------------------------------------+
//| Ensure output directory exists under MQL5/Files                  |
//+------------------------------------------------------------------+
bool EnsureOutputFolder()
  {
   if(FolderCreate(OUTPUT_FOLDER))
      return true;

   int err = GetLastError();
   if(err == 0 || err == 5019) // already exists
      return true;

   Print("BrokerDataCollector: FolderCreate failed (error ", err, ").");
   return false;
  }

//+------------------------------------------------------------------+
//| Daily CSV filename: SYMBOL_YYYYMMDD.csv                          |
//+------------------------------------------------------------------+
string BuildDailyFileName(const string symbol)
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return StringFormat("%s_%04d%02d%02d.csv", symbol, dt.year, dt.mon, dt.day);
  }

//+------------------------------------------------------------------+
//| Read last written bar timestamp from today's file (resume safe)  |
//+------------------------------------------------------------------+
datetime ReadLastTimestampFromTodayFile(const string symbol)
  {
   string filePath = OUTPUT_FOLDER + "\\" + BuildDailyFileName(symbol);
   if(!FileIsExist(filePath))
      return 0;

   int handle = FileOpen(filePath, FILE_READ | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return 0;

   datetime lastTime = 0;
   while(!FileIsEnding(handle))
     {
      string line = FileReadString(handle);
      if(line == "" || line == CSV_HEADER || StringFind(line, "timestamp,") == 0)
         continue;

      int comma = StringFind(line, ",");
      if(comma < 0)
         continue;

      datetime ts = StringToTime(StringSubstr(line, 0, comma));
      if(ts > lastTime)
         lastTime = ts;
     }

   FileClose(handle);
   return lastTime;
  }

//+------------------------------------------------------------------+
//| Human-readable timeframe label                                   |
//+------------------------------------------------------------------+
string TimeframeLabel(const ENUM_TIMEFRAMES tf)
  {
   switch(tf)
     {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN1";
      default:         return EnumToString(tf);
     }
  }

//+------------------------------------------------------------------+
//| Trim leading/trailing whitespace                                 |
//+------------------------------------------------------------------+
string Trim(const string value)
  {
   string s = value;
   StringTrimLeft(s);
   StringTrimRight(s);
   return s;
  }

//+------------------------------------------------------------------+
//| Escape commas in CSV text fields                                 |
//+------------------------------------------------------------------+
string CsvEscape(const string value)
  {
   if(StringFind(value, ",") < 0 && StringFind(value, "\"") < 0)
      return value;

   string escaped = value;
   StringReplace(escaped, "\"", "\"\"");
   return "\"" + escaped + "\"";
  }

//+------------------------------------------------------------------+
