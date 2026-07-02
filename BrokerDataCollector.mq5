//+------------------------------------------------------------------+
//|                                          BrokerDataCollector.mq5 |
//|                        Broker-universal MT5 data collector (v1)  |
//|                     Research / backtesting only — does NOT trade |
//+------------------------------------------------------------------+
#property copyright "Broker Data Collector"
#property version   "1.50"
#property description "Collects broker-specific market data to CSV. No trading."

#define OUTPUT_FOLDER           "BrokerDataCollector"
#define COMPETITION_LAB_FOLDER  "BrokerDataCollector\\CompetitionLab"
#define CSV_HEADER              "timestamp,broker_name,server,account_login,account_type_company,symbol,timeframe,open,high,low,close,tick_volume,bid,ask,spread_points,spread_price,digits,point"
#define COMPETITION_LAB_HEADER  "Timestamp,Open,High,Low,Close,Volume"
#define SUMMARY_HEADER          "date,broker,server,symbol,timeframe,bars_written,avg_spread,min_spread,max_spread"
#define MANIFEST_FILE           "manifest.json"

//--- export format
enum ENUM_EXPORT_FORMAT
  {
   EXPORT_RAW             = 0,   // Raw
   EXPORT_COMPETITION_LAB = 1    // CompetitionLab
  };

//--- manifest file entry
struct ManifestFileEntry
  {
   string   symbol;
   string   timeframe;
   string   date;
   string   filename;
   string   folder;
   int      rows_written;
   datetime first_timestamp;
   datetime last_timestamp;
  };

//--- backfill quality stats for one symbol
struct BackfillStats
  {
   int      bars_written;
   datetime first_timestamp;
   datetime last_timestamp;
   long     spread_sum;
   int      min_spread;
   int      max_spread;
  };

//--- inputs
input string            InpSymbols       = "BTCUSD,XAUUSD,US100,EURUSD";
input string            InpTimeframes     = "M1,M5,M15,H1";
input int               InpTimerSeconds  = 60;
input bool              EnableBackfill   = true;
input int               BackfillBars     = 5000;
input ENUM_EXPORT_FORMAT ExportFormat    = EXPORT_RAW;

//--- globals
string          g_symbols[];
ENUM_TIMEFRAMES g_timeframes[];
datetime        g_lastWrittenBarTime[];

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

   if(EnableBackfill && BackfillBars < 1)
     {
      Print("BrokerDataCollector: BackfillBars must be >= 1 when backfill is enabled.");
      return INIT_PARAMETERS_INCORRECT;
     }

   if(!ParseSymbolList(InpSymbols, g_symbols))
     {
      Print("BrokerDataCollector: no valid symbols in input list.");
      return INIT_PARAMETERS_INCORRECT;
     }

   if(!ParseTimeframeList(InpTimeframes, g_timeframes))
     {
      Print("BrokerDataCollector: no valid timeframes in input list.");
      return INIT_PARAMETERS_INCORRECT;
     }

   ArrayResize(g_lastWrittenBarTime, StreamCount());
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

      for(int j = 0; j < ArraySize(g_timeframes); j++)
        {
         ENUM_TIMEFRAMES tf = g_timeframes[j];
         int streamIndex = StreamIndex(i, j);

         if(EnableBackfill && BackfillBars > 0)
           {
            BackfillStats stats;
            ResetBackfillStats(stats);
            BackfillSymbol(i, j, stats);
            PrintBackfillSummary(symbol, tf, stats);
            AppendDailySummaryRow(symbol, tf, stats);
           }
         else
           {
            g_lastWrittenBarTime[streamIndex] =
               ReadLastTimestampFromDailyFile(symbol, tf, TimeCurrent());
           }

         Print("BrokerDataCollector: tracking ", symbol, " ", TimeframeLabel(tf),
               ", last written bar: ",
               (g_lastWrittenBarTime[streamIndex] > 0
                ? TimeToString(g_lastWrittenBarTime[streamIndex], TIME_DATE | TIME_SECONDS)
                : "none"));
        }
     }

   WriteManifest();

   if(!EventSetTimer(InpTimerSeconds))
     {
      Print("BrokerDataCollector: EventSetTimer failed (error ", GetLastError(), ").");
      return INIT_FAILED;
     }

   Print("BrokerDataCollector: started. Symbols=", ArraySize(g_symbols),
         ", timeframes=", ArraySize(g_timeframes),
         ", streams=", StreamCount(),
         ", timer=", InpTimerSeconds, "s",
         ", backfill=", (EnableBackfill ? "on" : "off"),
         ", export=", ExportFormatLabel());
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Reset backfill stats structure                                   |
//+------------------------------------------------------------------+
void ResetBackfillStats(BackfillStats &stats)
  {
   stats.bars_written    = 0;
   stats.first_timestamp = 0;
   stats.last_timestamp  = 0;
   stats.spread_sum      = 0;
   stats.min_spread      = 0;
   stats.max_spread      = 0;
  }

//+------------------------------------------------------------------+
//| Record one written bar in backfill stats                         |
//+------------------------------------------------------------------+
void RecordWrittenBar(BackfillStats &stats,
                      const datetime barTime,
                      const int spreadPoints)
  {
   if(stats.bars_written == 0)
     {
      stats.first_timestamp = barTime;
      stats.min_spread      = spreadPoints;
      stats.max_spread      = spreadPoints;
     }
   else
     {
      if(spreadPoints < stats.min_spread)
         stats.min_spread = spreadPoints;
      if(spreadPoints > stats.max_spread)
         stats.max_spread = spreadPoints;
     }

   stats.last_timestamp = barTime;
   stats.spread_sum    += spreadPoints;
   stats.bars_written++;
  }

//+------------------------------------------------------------------+
//| Backfill closed bars for one symbol (oldest first, skip dupes)   |
//+------------------------------------------------------------------+
void BackfillSymbol(const int symbolIndex,
                    const int tfIndex,
                    BackfillStats &stats)
  {
   ResetBackfillStats(stats);

   string symbol = g_symbols[symbolIndex];
   ENUM_TIMEFRAMES tf = g_timeframes[tfIndex];
   int streamIndex = StreamIndex(symbolIndex, tfIndex);

   if(!SymbolSelect(symbol, true))
      return;

   int available = Bars(symbol, tf);
   if(available < 2)
     {
      Print("BrokerDataCollector: insufficient history for backfill on ",
            symbol, " ", TimeframeLabel(tf), ".");
      return;
     }

   int requestBars = MathMin(BackfillBars, available - 1);

   MqlRates rates[];
   ArraySetAsSeries(rates, true);

   int copied = CopyRates(symbol, tf, 1, requestBars, rates);
   if(copied < 1)
     {
      Print("BrokerDataCollector: backfill CopyRates failed for ", symbol,
            " ", TimeframeLabel(tf), " (error ", GetLastError(), ").");
      return;
     }

   int      written        = 0;
   datetime dayAnchor      = 0;
   datetime dayLastWritten = 0;

   for(int i = copied - 1; i >= 0; i--)
     {
      datetime barTime = rates[i].time;
      datetime barDay  = BarDayStart(barTime);

      if(barDay != dayAnchor)
        {
         dayAnchor      = barDay;
         dayLastWritten = ReadLastTimestampFromDailyFile(symbol, tf, barTime);
        }

      if(barTime <= dayLastWritten)
         continue;

      if(!AppendBarRow(symbol, tf, rates[i]))
         continue;

      int spreadPoints = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
      RecordWrittenBar(stats, barTime, spreadPoints);

      written++;
      dayLastWritten = barTime;

      if(barTime > g_lastWrittenBarTime[streamIndex])
         g_lastWrittenBarTime[streamIndex] = barTime;
     }

   datetime todayLast = ReadLastTimestampFromDailyFile(symbol, tf, TimeCurrent());
   if(todayLast > g_lastWrittenBarTime[streamIndex])
      g_lastWrittenBarTime[streamIndex] = todayLast;

   Print("BrokerDataCollector: backfill ", symbol, " ", TimeframeLabel(tf),
         " — ", written, " bar(s) written (requested ", BackfillBars, ")");

   if(written > 0)
      WriteManifest();
  }

//+------------------------------------------------------------------+
//| Print dataset quality summary after backfill                     |
//+------------------------------------------------------------------+
void PrintBackfillSummary(const string symbol,
                          const ENUM_TIMEFRAMES tf,
                          const BackfillStats &stats)
  {
   string tfLabel = TimeframeLabel(tf);

   if(stats.bars_written == 0)
     {
      Print("BrokerDataCollector: quality summary ", symbol, " ", tfLabel,
            " | bars=0 | first=n/a | last=n/a | avg_spread=n/a | min_spread=n/a | max_spread=n/a");
      return;
     }

   double avgSpread = (double)stats.spread_sum / stats.bars_written;

   Print("BrokerDataCollector: quality summary ", symbol, " ", tfLabel,
         " | bars=", stats.bars_written,
         " | first=", TimeToString(stats.first_timestamp, TIME_DATE | TIME_SECONDS),
         " | last=", TimeToString(stats.last_timestamp, TIME_DATE | TIME_SECONDS),
         " | avg_spread=", DoubleToString(avgSpread, 2),
         " | min_spread=", stats.min_spread,
         " | max_spread=", stats.max_spread);
  }

//+------------------------------------------------------------------+
//| Append one row to the daily backfill summary CSV                 |
//+------------------------------------------------------------------+
bool AppendDailySummaryRow(const string symbol,
                           const ENUM_TIMEFRAMES tf,
                           const BackfillStats &stats)
  {
   string filePath = OUTPUT_FOLDER + "\\" + BuildSummaryFileName();
   bool isNewFile = !FileIsExist(filePath);

   int handle = FileOpen(filePath, FILE_READ | FILE_WRITE | FILE_ANSI);
   if(handle == INVALID_HANDLE)
     {
      Print("BrokerDataCollector: summary FileOpen failed for ", filePath,
            " (error ", GetLastError(), ").");
      return false;
     }

   if(isNewFile)
      FileWriteString(handle, SUMMARY_HEADER + "\r\n");
   else
      FileSeek(handle, 0, SEEK_END);

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   string dateStr   = StringFormat("%04d-%02d-%02d", dt.year, dt.mon, dt.day);
   string broker    = TerminalInfoString(TERMINAL_COMPANY);
   string server    = AccountInfoString(ACCOUNT_SERVER);
   string tfLabel   = TimeframeLabel(tf);
   double avgSpread = (stats.bars_written > 0)
                      ? (double)stats.spread_sum / stats.bars_written
                      : 0.0;

   string row = StringFormat("%s,%s,%s,%s,%s,%d,%s,%d,%d",
                             dateStr,
                             CsvEscape(broker),
                             CsvEscape(server),
                             CsvEscape(symbol),
                             tfLabel,
                             stats.bars_written,
                             DoubleToString(avgSpread, 2),
                             stats.min_spread,
                             stats.max_spread);

   FileWriteString(handle, row + "\r\n");
   FileFlush(handle);
   FileClose(handle);
   return true;
  }

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   WriteManifest();
   Print("BrokerDataCollector: stopped (reason ", reason, ").");
  }

//+------------------------------------------------------------------+
//| Timer handler                                                    |
//+------------------------------------------------------------------+
void OnTimer()
  {
   for(int i = 0; i < ArraySize(g_symbols); i++)
      for(int j = 0; j < ArraySize(g_timeframes); j++)
         CollectSymbolBar(i, j);
  }

//+------------------------------------------------------------------+
//| Collect and persist the latest completed bar for one stream      |
//+------------------------------------------------------------------+
void CollectSymbolBar(const int symbolIndex, const int tfIndex)
  {
   string symbol = g_symbols[symbolIndex];
   ENUM_TIMEFRAMES tf = g_timeframes[tfIndex];
   int streamIndex = StreamIndex(symbolIndex, tfIndex);

   if(!SymbolSelect(symbol, true))
      return;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);

   int copied = CopyRates(symbol, tf, 1, 1, rates);
   if(copied < 1)
     {
      Print("BrokerDataCollector: CopyRates failed for ", symbol,
            " ", TimeframeLabel(tf), " (error ", GetLastError(), ").");
      return;
     }

   datetime barTime = rates[0].time;
   if(barTime <= g_lastWrittenBarTime[streamIndex])
      return;

   if(!AppendBarRow(symbol, tf, rates[0]))
     {
      Print("BrokerDataCollector: failed to write row for ", symbol,
            " ", TimeframeLabel(tf), ".");
      return;
     }

   g_lastWrittenBarTime[streamIndex] = barTime;
   WriteManifest();
  }

//+------------------------------------------------------------------+
//| Append one CSV row (creates file + header when needed)           |
//+------------------------------------------------------------------+
bool AppendBarRow(const string symbol,
                  const ENUM_TIMEFRAMES tf,
                  const MqlRates &bar)
  {
   string filePath = GetDataOutputFolder() + "\\" + BuildDailyFileName(symbol, tf, bar.time);

   bool isNewFile = !FileIsExist(filePath);
   int handle = FileOpen(filePath, FILE_READ | FILE_WRITE | FILE_ANSI);
   if(handle == INVALID_HANDLE)
     {
      Print("BrokerDataCollector: FileOpen failed for ", filePath,
            " (error ", GetLastError(), ").");
      return false;
     }

   if(isNewFile)
      FileWriteString(handle, GetDataCsvHeader() + "\r\n");
   else
      FileSeek(handle, 0, SEEK_END);

   string row;
   if(ExportFormat == EXPORT_COMPETITION_LAB)
      row = BuildCompetitionLabRow(symbol, bar);
   else
     {
      double bid          = SymbolInfoDouble(symbol, SYMBOL_BID);
      double ask          = SymbolInfoDouble(symbol, SYMBOL_ASK);
      int    spreadPoints = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
      int    digits       = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      double point        = SymbolInfoDouble(symbol, SYMBOL_POINT);
      double spreadPrice  = (ask - bid);
      row = BuildCsvRow(symbol, tf, bar, bid, ask, spreadPoints, spreadPrice, digits, point);
     }

   FileWriteString(handle, row + "\r\n");
   FileFlush(handle);
   FileClose(handle);
   return true;
  }

//+------------------------------------------------------------------+
//| Build Quant Competition Lab CSV row (completed candles only)     |
//+------------------------------------------------------------------+
string BuildCompetitionLabRow(const string symbol, const MqlRates &bar)
  {
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   return StringFormat("%s,%s,%s,%s,%s,%I64d",
                       TimeToString(bar.time, TIME_DATE | TIME_SECONDS),
                       DoubleToString(bar.open, digits),
                       DoubleToString(bar.high, digits),
                       DoubleToString(bar.low, digits),
                       DoubleToString(bar.close, digits),
                       bar.tick_volume);
  }

//+------------------------------------------------------------------+
//| Build a single CSV data row                                      |
//+------------------------------------------------------------------+
string BuildCsvRow(const string symbol,
                   const ENUM_TIMEFRAMES tf,
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
   string tfLabel   = TimeframeLabel(tf);

   return StringFormat("%s,%s,%s,%I64d,%s,%s,%s,%s,%s,%s,%s,%I64d,%s,%s,%d,%s,%d,%s",
                       timestamp,
                       CsvEscape(broker),
                       CsvEscape(server),
                       login,
                       CsvEscape(acctType),
                       CsvEscape(symbol),
                       tfLabel,
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
//| Parse comma-separated timeframe list                             |
//+------------------------------------------------------------------+
bool ParseTimeframeList(const string raw, ENUM_TIMEFRAMES &timeframes[])
  {
   string parts[];
   int count = StringSplit(raw, ',', parts);
   if(count < 1)
      return false;

   ArrayResize(timeframes, 0);

   for(int i = 0; i < count; i++)
     {
      string label = Trim(parts[i]);
      if(label == "")
         continue;

      ENUM_TIMEFRAMES tf;
      if(!ParseTimeframeLabel(label, tf))
        {
         Print("BrokerDataCollector: unknown timeframe '", label, "'.");
         continue;
        }

      int n = ArraySize(timeframes);
      ArrayResize(timeframes, n + 1);
      timeframes[n] = tf;
     }

   return ArraySize(timeframes) > 0;
  }

//+------------------------------------------------------------------+
//| Parse one timeframe label into ENUM_TIMEFRAMES                     |
//+------------------------------------------------------------------+
bool ParseTimeframeLabel(const string label, ENUM_TIMEFRAMES &tf)
  {
   string s = Trim(label);

   if(StringCompare(s, "M1", false) == 0)   { tf = PERIOD_M1;  return true; }
   if(StringCompare(s, "M5", false) == 0)   { tf = PERIOD_M5;  return true; }
   if(StringCompare(s, "M15", false) == 0)  { tf = PERIOD_M15; return true; }
   if(StringCompare(s, "M30", false) == 0)  { tf = PERIOD_M30; return true; }
   if(StringCompare(s, "H1", false) == 0)   { tf = PERIOD_H1;  return true; }
   if(StringCompare(s, "H4", false) == 0)   { tf = PERIOD_H4;  return true; }
   if(StringCompare(s, "D1", false) == 0)   { tf = PERIOD_D1;  return true; }
   if(StringCompare(s, "W1", false) == 0)   { tf = PERIOD_W1;  return true; }
   if(StringCompare(s, "MN1", false) == 0)  { tf = PERIOD_MN1; return true; }

   return false;
  }

//+------------------------------------------------------------------+
//| Total symbol x timeframe streams                                 |
//+------------------------------------------------------------------+
int StreamCount()
  {
   return ArraySize(g_symbols) * ArraySize(g_timeframes);
  }

//+------------------------------------------------------------------+
//| Flat index for symbol/timeframe stream state                     |
//+------------------------------------------------------------------+
int StreamIndex(const int symbolIndex, const int tfIndex)
  {
   return symbolIndex * ArraySize(g_timeframes) + tfIndex;
  }

//+------------------------------------------------------------------+
//| Ensure output directory exists under MQL5/Files                  |
//+------------------------------------------------------------------+
bool EnsureOutputFolder()
  {
   if(!EnsureFolder(OUTPUT_FOLDER))
      return false;

   if(ExportFormat == EXPORT_COMPETITION_LAB)
      return EnsureFolder(COMPETITION_LAB_FOLDER);

   return true;
  }

//+------------------------------------------------------------------+
//| Create folder if missing (treat already-exists as success)       |
//+------------------------------------------------------------------+
bool EnsureFolder(const string folder)
  {
   if(FolderCreate(folder))
      return true;

   int err = GetLastError();
   if(err == 0 || err == 5019)
      return true;

   Print("BrokerDataCollector: FolderCreate failed for ", folder, " (error ", err, ").");
   return false;
  }

//+------------------------------------------------------------------+
//| Active data output folder for selected export format             |
//+------------------------------------------------------------------+
string GetDataOutputFolder()
  {
   if(ExportFormat == EXPORT_COMPETITION_LAB)
      return COMPETITION_LAB_FOLDER;
   return OUTPUT_FOLDER;
  }

//+------------------------------------------------------------------+
//| CSV header for selected export format                            |
//+------------------------------------------------------------------+
string GetDataCsvHeader()
  {
   if(ExportFormat == EXPORT_COMPETITION_LAB)
      return COMPETITION_LAB_HEADER;
   return CSV_HEADER;
  }

//+------------------------------------------------------------------+
//| Human-readable export format label                               |
//+------------------------------------------------------------------+
string ExportFormatLabel()
  {
   if(ExportFormat == EXPORT_COMPETITION_LAB)
      return "CompetitionLab";
   return "Raw";
  }

//+------------------------------------------------------------------+
//| True when line is a data-file header row                         |
//+------------------------------------------------------------------+
bool IsDataHeaderLine(const string line)
  {
   if(ExportFormat == EXPORT_COMPETITION_LAB)
      return (StringFind(line, "Timestamp,") == 0);
   return (line == CSV_HEADER || StringFind(line, "timestamp,") == 0);
  }

//+------------------------------------------------------------------+
//| Daily CSV filename: SYMBOL_TIMEFRAME_YYYYMMDD.csv                |
//+------------------------------------------------------------------+
string BuildDailyFileName(const string symbol,
                          const ENUM_TIMEFRAMES tf,
                          const datetime barTime)
  {
   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   return StringFormat("%s_%s_%04d%02d%02d.csv",
                       symbol,
                       TimeframeLabel(tf),
                       dt.year, dt.mon, dt.day);
  }

//+------------------------------------------------------------------+
//| Daily summary filename: summary_YYYYMMDD.csv                     |
//+------------------------------------------------------------------+
string BuildSummaryFileName()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return StringFormat("summary_%04d%02d%02d.csv", dt.year, dt.mon, dt.day);
  }

//+------------------------------------------------------------------+
//| Midnight timestamp for the bar's calendar day                      |
//+------------------------------------------------------------------+
datetime BarDayStart(const datetime barTime)
  {
   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   dt.hour = 0;
   dt.min  = 0;
   dt.sec  = 0;
   return StructToTime(dt);
  }

//+------------------------------------------------------------------+
//| Read last written bar timestamp from a daily file (resume safe)  |
//+------------------------------------------------------------------+
datetime ReadLastTimestampFromDailyFile(const string symbol,
                                        const ENUM_TIMEFRAMES tf,
                                        const datetime barTime)
  {
   string filePath = GetDataOutputFolder() + "\\" + BuildDailyFileName(symbol, tf, barTime);
   if(!FileIsExist(filePath))
      return 0;

   int handle = FileOpen(filePath, FILE_READ | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return 0;

   datetime lastTime = 0;
   while(!FileIsEnding(handle))
     {
      string line = FileReadString(handle);
      if(line == "" || IsDataHeaderLine(line))
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
//| Escape string for JSON output                                    |
//+------------------------------------------------------------------+
string JsonEscape(const string value)
  {
   string escaped = value;
   StringReplace(escaped, "\\", "\\\\");
   StringReplace(escaped, "\"", "\\\"");
   StringReplace(escaped, "\r", "\\r");
   StringReplace(escaped, "\n", "\\n");
   StringReplace(escaped, "\t", "\\t");
   return escaped;
  }

//+------------------------------------------------------------------+
//| Manifest folder label (relative to MQL5/Files)                   |
//+------------------------------------------------------------------+
string GetManifestFolderLabel()
  {
   if(ExportFormat == EXPORT_COMPETITION_LAB)
      return "BrokerDataCollector/CompetitionLab";
   return "BrokerDataCollector";
  }

//+------------------------------------------------------------------+
//| Full path to manifest.json                                       |
//+------------------------------------------------------------------+
string ManifestFilePath()
  {
   return OUTPUT_FOLDER + "\\" + MANIFEST_FILE;
  }

//+------------------------------------------------------------------+
//| Format datetime for manifest timestamps                          |
//+------------------------------------------------------------------+
string ManifestTimestamp(const datetime value)
  {
   if(value <= 0)
      return "";
   return TimeToString(value, TIME_DATE | TIME_SECONDS);
  }

//+------------------------------------------------------------------+
//| Format YYYY-MM-DD from YYYYMMDD                                  |
//+------------------------------------------------------------------+
string FormatIsoDateFromYmd(const string ymd)
  {
   if(StringLen(ymd) != 8)
      return ymd;
   return StringSubstr(ymd, 0, 4) + "-" +
          StringSubstr(ymd, 4, 2) + "-" +
          StringSubstr(ymd, 6, 2);
  }

//+------------------------------------------------------------------+
//| Parse SYMBOL_TIMEFRAME_YYYYMMDD.csv filename                     |
//+------------------------------------------------------------------+
bool ParseDataFileName(const string filename,
                       string &symbol,
                       string &timeframe,
                       string &dateYmd)
  {
   if(StringFind(filename, "summary_") == 0)
      return false;

   int dotPos = StringFind(filename, ".csv");
   if(dotPos < 0)
      return false;

   string base = StringSubstr(filename, 0, dotPos);
   int lastUnderscore = -1;
   int prevUnderscore = -1;

   for(int i = StringLen(base) - 1; i >= 0; i--)
     {
      if(StringGetCharacter(base, i) != '_')
         continue;

      if(lastUnderscore < 0)
         lastUnderscore = i;
      else
        {
         prevUnderscore = i;
         break;
        }
     }

   if(lastUnderscore < 0 || prevUnderscore < 0)
      return false;

   dateYmd = StringSubstr(base, lastUnderscore + 1);
   if(StringLen(dateYmd) != 8)
      return false;

   timeframe = StringSubstr(base, prevUnderscore + 1, lastUnderscore - prevUnderscore - 1);
   symbol = StringSubstr(base, 0, prevUnderscore);

   return (symbol != "" && timeframe != "");
  }

//+------------------------------------------------------------------+
//| Count rows and timestamp range in a data CSV file                |
//+------------------------------------------------------------------+
bool GetFileRowStats(const string filePath,
                     int &rows,
                     datetime &firstTs,
                     datetime &lastTs)
  {
   rows    = 0;
   firstTs = 0;
   lastTs  = 0;

   if(!FileIsExist(filePath))
      return false;

   int handle = FileOpen(filePath, FILE_READ | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return false;

   while(!FileIsEnding(handle))
     {
      string line = FileReadString(handle);
      if(line == "" || IsDataHeaderLine(line))
         continue;

      int comma = StringFind(line, ",");
      if(comma < 0)
         continue;

      datetime ts = StringToTime(StringSubstr(line, 0, comma));
      rows++;

      if(firstTs == 0 || ts < firstTs)
         firstTs = ts;
      if(ts > lastTs)
         lastTs = ts;
     }

   FileClose(handle);
   return (rows > 0);
  }

//+------------------------------------------------------------------+
//| Collect manifest entries by scanning the active data folder      |
//+------------------------------------------------------------------+
void CollectManifestFilesFromDisk(ManifestFileEntry &files[])
  {
   ArrayResize(files, 0);

   string folder = GetDataOutputFolder();
   string search = folder + "\\*.csv";
   string filename;
   long searchHandle = FileFindFirst(search, filename);

   if(searchHandle == INVALID_HANDLE)
      return;

   do
     {
      if(StringFind(filename, "summary_") == 0)
         continue;

      string symbol = "";
      string timeframe = "";
      string dateYmd = "";
      if(!ParseDataFileName(filename, symbol, timeframe, dateYmd))
         continue;

      string filePath = folder + "\\" + filename;
      int rows = 0;
      datetime firstTs = 0;
      datetime lastTs = 0;
      if(!GetFileRowStats(filePath, rows, firstTs, lastTs))
         continue;

      int n = ArraySize(files);
      ArrayResize(files, n + 1);
      files[n].symbol          = symbol;
      files[n].timeframe       = timeframe;
      files[n].date            = FormatIsoDateFromYmd(dateYmd);
      files[n].filename        = filename;
      files[n].folder          = GetManifestFolderLabel();
      files[n].rows_written    = rows;
      files[n].first_timestamp = firstTs;
      files[n].last_timestamp  = lastTs;
     }
   while(FileFindNext(searchHandle, filename));

   FileFindClose(searchHandle);
  }

//+------------------------------------------------------------------+
//| Build JSON string array from symbols                             |
//+------------------------------------------------------------------+
string BuildJsonStringArray(const string &items[])
  {
   string json = "[";
   int count = ArraySize(items);

   for(int i = 0; i < count; i++)
     {
      if(i > 0)
         json += ",";
      json += "\"" + JsonEscape(items[i]) + "\"";
     }

   return json + "]";
  }

//+------------------------------------------------------------------+
//| Build JSON string array from configured timeframes               |
//+------------------------------------------------------------------+
string BuildJsonTimeframeArray()
  {
   string labels[];
   ArrayResize(labels, ArraySize(g_timeframes));

   for(int i = 0; i < ArraySize(g_timeframes); i++)
      labels[i] = TimeframeLabel(g_timeframes[i]);

   return BuildJsonStringArray(labels);
  }

//+------------------------------------------------------------------+
//| Build JSON for one manifest file entry                           |
//+------------------------------------------------------------------+
string BuildManifestFileJson(const ManifestFileEntry &entry)
  {
   return StringFormat(
      "    {\n"
      "      \"symbol\": \"%s\",\n"
      "      \"timeframe\": \"%s\",\n"
      "      \"date\": \"%s\",\n"
      "      \"filename\": \"%s\",\n"
      "      \"folder\": \"%s\",\n"
      "      \"rows_written\": %d,\n"
      "      \"first_timestamp\": \"%s\",\n"
      "      \"last_timestamp\": \"%s\"\n"
      "    }",
      JsonEscape(entry.symbol),
      JsonEscape(entry.timeframe),
      JsonEscape(entry.date),
      JsonEscape(entry.filename),
      JsonEscape(entry.folder),
      entry.rows_written,
      JsonEscape(ManifestTimestamp(entry.first_timestamp)),
      JsonEscape(ManifestTimestamp(entry.last_timestamp)));
  }

//+------------------------------------------------------------------+
//| Write manifest.json for Quant Competition Lab auto-discovery     |
//+------------------------------------------------------------------+
bool WriteManifest()
  {
   ManifestFileEntry files[];
   CollectManifestFilesFromDisk(files);

   string json = "{\n";
   json += "  \"generated_at\": \"" + JsonEscape(TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS)) + "\",\n";
   json += "  \"broker\": \"" + JsonEscape(TerminalInfoString(TERMINAL_COMPANY)) + "\",\n";
   json += "  \"server\": \"" + JsonEscape(AccountInfoString(ACCOUNT_SERVER)) + "\",\n";
   json += "  \"account_login\": " + IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN)) + ",\n";
   json += "  \"account_company\": \"" + JsonEscape(AccountInfoString(ACCOUNT_COMPANY)) + "\",\n";
   json += "  \"export_format\": \"" + JsonEscape(ExportFormatLabel()) + "\",\n";
   json += "  \"symbols\": " + BuildJsonStringArray(g_symbols) + ",\n";
   json += "  \"timeframes\": " + BuildJsonTimeframeArray() + ",\n";
   json += "  \"files\": [\n";

   int fileCount = ArraySize(files);
   for(int i = 0; i < fileCount; i++)
     {
      if(i > 0)
         json += ",\n";
      json += BuildManifestFileJson(files[i]);
     }

   json += "\n  ]\n}\n";

   string filePath = ManifestFilePath();
   int handle = FileOpen(filePath, FILE_WRITE | FILE_ANSI);
   if(handle == INVALID_HANDLE)
     {
      Print("BrokerDataCollector: manifest FileOpen failed for ", filePath,
            " (error ", GetLastError(), ").");
      return false;
     }

   FileWriteString(handle, json);
   FileFlush(handle);
   FileClose(handle);
   return true;
  }

//+------------------------------------------------------------------+
