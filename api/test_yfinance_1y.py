import yfinance as yf

print("Testing GLD 1y fetch...")
try:
    gld = yf.Ticker("GLD")
    hist = gld.history(period="1y", interval="1d")
    print(hist.head())
    print("\nEmpty?", hist.empty)
except Exception as e:
    print("Error:", e)
