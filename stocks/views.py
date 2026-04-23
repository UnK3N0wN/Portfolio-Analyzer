import yfinance as yf
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.cache import cache
from .models import StockCache


def fetch_stock_data(symbol):
    """Fetch stock data from yfinance and cache it."""
    cache_key = f'stock_{symbol}'
    cached    = cache.get(cache_key)
    if cached:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info
        hist   = ticker.history(period='1d')

        if hist.empty:
            return None

        data = {
            'symbol':        symbol.upper(),
            'name':          info.get('longName', symbol),
            'current_price': round(float(hist['Close'].iloc[-1]), 2),
            'open_price':    round(float(hist['Open'].iloc[-1]), 2),
            'high_price':    round(float(hist['High'].iloc[-1]), 2),
            'low_price':     round(float(hist['Low'].iloc[-1]), 2),
            'volume':        int(hist['Volume'].iloc[-1]),
            'market_cap':    info.get('marketCap', 0),
            'week_52_high':  info.get('fiftyTwoWeekHigh', 0),
            'week_52_low':   info.get('fiftyTwoWeekLow', 0),
            'sector':        info.get('sector', 'N/A'),
        }

        data['price_change']         = round(data['current_price'] - data['open_price'], 2)
        data['price_change_percent'] = round(((data['current_price'] - data['open_price']) / data['open_price']) * 100, 2) if data['open_price'] else 0

        # Save to DB cache
        StockCache.objects.update_or_create(
            symbol=symbol.upper(),
            defaults={
                'name':          data['name'],
                'current_price': data['current_price'],
                'open_price':    data['open_price'],
                'high_price':    data['high_price'],
                'low_price':     data['low_price'],
                'volume':        data['volume'],
                'market_cap':    data['market_cap'],
                'week_52_high':  data['week_52_high'],
                'week_52_low':   data['week_52_low'],
                'sector':        data['sector'],
            }
        )

        cache.set(cache_key, data, settings.STOCK_CACHE_TIMEOUT)
        return data

    except Exception:
        return None


@login_required
def search(request):
    query   = request.GET.get('q', '').strip().upper()
    results = []

    if query:
        data = fetch_stock_data(query)
        if data:
            results = [data]
        else:
            messages.error(request, f'Could not find data for "{query}". Check the symbol and try again.')

    return render(request, 'stocks/stock_search.html', {
        'query':   query,
        'results': results,
        'suggested_symbols': ['AAPL', 'MSFT', 'GOOGL', 'BTC-USD', 'ETH-USD', 'TSLA'],
    })


@login_required
def stock_detail(request, symbol):
    symbol = symbol.upper()
    data   = fetch_stock_data(symbol)

    if not data:
        messages.error(request, f'Could not fetch data for {symbol}.')
        return redirect('stocks:search')

    # Fetch 30 days history for chart
    try:
        hist = yf.Ticker(symbol).history(period='1mo')
        history = [
            {'date': str(row.Index.date()), 'close': round(float(row.Close), 2)}
            for row in hist.itertuples()
        ]
    except Exception:
        history = []

    return render(request, 'stocks/stock_detail.html', {
        'stock':   data,
        'history': history,
    })