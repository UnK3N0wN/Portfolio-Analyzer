import csv
import io
import yfinance as yf
import numpy as np
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Portfolio, Holding, Transaction, PriceAlert, WatchlistItem, PortfolioSnapshot
from .forms import AddHoldingForm, BuyForm, SellForm, PriceAlertForm, WatchlistForm
from ai.llm import ask_llm, analyze_portfolio, get_risk_assessment, get_buy_sell_suggestions
from ai.utils import get_portfolio_summary, get_asset_allocation
from ai.predict import get_portfolio_trend

try:
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False



def get_or_create_portfolio(user):
    portfolio, _ = Portfolio.objects.get_or_create(user=user)
    return portfolio


def update_prices(portfolio):
    for holding in portfolio.holdings.all():
        try:
            data = yf.Ticker(holding.symbol).history(period='1d')
            if not data.empty:
                holding.current_price = round(float(data['Close'].iloc[-1]), 8)
                holding.save()
        except Exception:
            pass


def save_snapshot(portfolio):
    today = date.today()
    PortfolioSnapshot.objects.update_or_create(
        portfolio=portfolio, date=today,
        defaults={
            'total_value':    round(portfolio.total_value(), 2),
            'total_invested': round(portfolio.total_invested(), 2),
            'profit_loss':    round(portfolio.total_profit_loss(), 2),
        }
    )


def check_price_alerts(user):
    triggered = []
    for alert in PriceAlert.objects.filter(user=user, is_active=True, is_triggered=False):
        try:
            data = yf.Ticker(alert.symbol).history(period='1d')
            if not data.empty:
                alert.current_price = round(float(data['Close'].iloc[-1]), 8)
                alert.save()
                if alert.check_trigger():
                    alert.is_triggered = True
                    alert.triggered_at = timezone.now()
                    alert.save()
                    triggered.append(alert)
        except Exception:
            pass
    return triggered


def update_watchlist_prices(user):
    for item in WatchlistItem.objects.filter(user=user):
        try:
            data = yf.Ticker(item.symbol).history(period='1d')
            if not data.empty:
                item.current_price = round(float(data['Close'].iloc[-1]), 8)
                item.save()
        except Exception:
            pass


def get_weekly_snapshots(portfolio):
    seven_days_ago = date.today() - timedelta(days=7)
    return portfolio.snapshots.filter(date__gte=seven_days_ago).order_by('date')

def calculate_ema(series, period):
    """Exponential moving average (used by MACD and internally elsewhere)."""
    series = np.array(series, dtype=float)
    if len(series) == 0:
        return series
    ema = np.zeros_like(series)
    k = 2.0 / (period + 1)
    ema[0] = series[0]
    for i in range(1, len(series)):
        ema[i] = series[i] * k + ema[i - 1] * (1 - k)
    return ema


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD line, signal line, and histogram."""
    prices = np.array(prices, dtype=float)
    if len(prices) < 2:
        return [], [], []
    ema_fast    = calculate_ema(prices, fast)
    ema_slow    = calculate_ema(prices, slow)
    macd_line   = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram   = macd_line - signal_line
    return (
        [round(float(v), 4) for v in macd_line],
        [round(float(v), 4) for v in signal_line],
        [round(float(v), 4) for v in histogram],
    )


def calculate_rsi(prices, period=14):
    """Relative Strength Index (Wilder's smoothing)."""
    prices = np.array(prices, dtype=float)
    n = len(prices)
    if n < 2:
        return [50.0] * n

    deltas = np.diff(prices)
    rsi = np.zeros(n)
    rsi[0] = 50.0

    seed_len = min(period, len(deltas))
    seed = deltas[:seed_len]
    up   = seed[seed > 0].sum() / period if seed_len else 0
    down = -seed[seed < 0].sum() / period if seed_len else 0

    for i in range(1, n):
        if i <= seed_len:
            rs = up / down if down != 0 else np.inf
            rsi[i] = 100.0 - (100.0 / (1.0 + rs)) if down != 0 else 100.0
            continue
        delta   = deltas[i - 1]
        upval   = delta if delta > 0 else 0.0
        downval = -delta if delta < 0 else 0.0
        up      = (up * (period - 1) + upval) / period
        down    = (down * (period - 1) + downval) / period
        rs      = up / down if down != 0 else np.inf
        rsi[i]  = 100.0 - (100.0 / (1.0 + rs)) if down != 0 else 100.0

    return [round(float(v), 2) for v in rsi]


def calculate_bollinger_bands(prices, period=20, num_std=2):
    """Middle (SMA), upper and lower Bollinger Bands."""
    prices = np.array(prices, dtype=float)
    n = len(prices)
    mid   = np.zeros(n)
    upper = np.zeros(n)
    lower = np.zeros(n)
    for i in range(n):
        window   = prices[max(0, i - period + 1):i + 1]
        mid[i]   = np.mean(window)
        std      = np.std(window)
        upper[i] = mid[i] + num_std * std
        lower[i] = mid[i] - num_std * std
    return (
        [round(float(v), 2) for v in mid],
        [round(float(v), 2) for v in upper],
        [round(float(v), 2) for v in lower],
    )


def predict_prices(prices, days=7):
    prices = np.array(prices, dtype=float)
    n = len(prices)

    if n < 10:
        return {'predicted': [], 'upper': [], 'lower': [], 'model': 'insufficient_data'}

    lookback = 5

    def build_features(series):
        feats, targets = [], []
        for i in range(lookback, len(series)):
            window     = series[i - lookback:i]
            ma5        = np.mean(series[max(0, i - 5):i])
            ma10       = np.mean(series[max(0, i - 10):i]) if i >= 10 else ma5
            momentum   = series[i - 1] - series[i - lookback]
            volatility = np.std(series[max(0, i - 10):i]) if i >= 2 else 0.0
            feats.append([*window, ma5, ma10, momentum, volatility])
            targets.append(series[i])
        return np.array(feats), np.array(targets)

    X, y = build_features(prices)

    rf = None
    model_name = 'holt_linear'
    if SKLEARN_AVAILABLE and len(X) >= 8:
        try:
            rf = RandomForestRegressor(
                n_estimators=200, max_depth=4, min_samples_leaf=2, random_state=42
            )
            rf.fit(X, y)
            residual_std = float(np.std(y - rf.predict(X)))
            model_name = 'ensemble_rf_holt'
        except Exception:
            rf = None
            residual_std = float(np.std(np.diff(prices))) if n > 1 else 0.0
    else:
        residual_std = float(np.std(np.diff(prices))) if n > 1 else 0.0

    # Holt's linear (double exponential smoothing) trend
    alpha, beta = 0.5, 0.3
    level = prices[0]
    trend = prices[1] - prices[0]
    for p in prices[1:]:
        last_level = level
        level = alpha * p + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend

    history   = list(prices)
    predicted = []
    for step in range(1, days + 1):
        holt_forecast = level + step * trend

        if rf is not None:
            window     = np.array(history[-lookback:])
            ma5        = np.mean(history[-5:])
            ma10       = np.mean(history[-10:]) if len(history) >= 10 else ma5
            momentum   = history[-1] - history[-lookback]
            volatility = np.std(history[-10:]) if len(history) >= 2 else 0.0
            feat       = np.array([[*window, ma5, ma10, momentum, volatility]])
            rf_forecast = float(rf.predict(feat)[0])
            blended = 0.6 * rf_forecast + 0.4 * holt_forecast
        else:
            blended = holt_forecast

        predicted.append(round(float(blended), 2))
        history.append(blended)

    band  = residual_std * 1.5
    upper = [round(float(p + band * np.sqrt(i + 1)), 2) for i, p in enumerate(predicted)]
    lower = [round(float(max(p - band * np.sqrt(i + 1), 0)), 2) for i, p in enumerate(predicted)]

    return {'predicted': predicted, 'upper': upper, 'lower': lower, 'model': model_name}


def landing(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    return render(request, 'landing.html')


@login_required
def dashboard(request):
    portfolio = get_or_create_portfolio(request.user)
    update_prices(portfolio)
    save_snapshot(portfolio)

    for alert in check_price_alerts(request.user):
        messages.warning(request, f'🔔 Alert: {alert.symbol} has gone {alert.alert_type} ${alert.target_price}!')

    holdings  = portfolio.holdings.all()
    snapshots = get_weekly_snapshots(portfolio)

    return render(request, 'portfolio/dashboard.html', {
        'portfolio':           portfolio,
        'holdings':            holdings,
        'top_gainers':         sorted(holdings, key=lambda h: h.profit_loss_percent(), reverse=True)[:3],
        'top_losers':          sorted(holdings, key=lambda h: h.profit_loss_percent())[:3],
        'recent_transactions': portfolio.transactions.all()[:5],
        'total_value':         portfolio.total_value(),
        'total_invested':      portfolio.total_invested(),
        'total_profit_loss':   portfolio.total_profit_loss(),
        'profit_loss_percent': portfolio.profit_loss_percent(),
        'snapshots':           snapshots,
        'active_alerts':       PriceAlert.objects.filter(user=request.user, is_active=True, is_triggered=False).count(),
    })


@login_required
def portfolio_view(request):
    portfolio = get_or_create_portfolio(request.user)
    update_prices(portfolio)
    return render(request, 'portfolio/portfolio.html', {
        'portfolio': portfolio,
        'holdings':  portfolio.holdings.all(),
    })


@login_required
def holding_detail(request, holding_id):
    portfolio = get_or_create_portfolio(request.user)
    holding   = get_object_or_404(Holding, id=holding_id, portfolio=portfolio)

    history       = []
    prices        = []
    history_dates = []
    info          = {}

    try:
        ticker = yf.Ticker(holding.symbol)
        # 3 months gives enough history for stable MACD/RSI/Bollinger Bands
        # and a better-fed prediction model than the old 30-day window.
        hist   = ticker.history(period='3mo')
        info   = ticker.info

        for row in hist.itertuples():
            close = round(float(row.Close), 2)
            history.append({'date': str(row.Index.date()), 'close': close})
            prices.append(close)
            history_dates.append(str(row.Index.date()))

        if prices:
            holding.current_price = prices[-1]
            holding.save()

    except Exception:
        pass

    # 7-day ensemble prediction (Random Forest + Holt's exponential smoothing)
    prediction = predict_prices(prices, days=7)
    predicted  = prediction['predicted']
    pred_upper = prediction['upper']
    pred_lower = prediction['lower']
    pred_model = prediction['model']

    # Technical indicators
    macd_line, macd_signal, macd_hist = calculate_macd(prices)
    rsi_values                        = calculate_rsi(prices)
    bb_mid, bb_upper, bb_lower        = calculate_bollinger_bands(prices)

    # Future dates
    if history_dates:
        last      = date.fromisoformat(history_dates[-1])
        fut_dates = [(last + timedelta(days=i+1)).isoformat() for i in range(len(predicted))]
    else:
        fut_dates = []

    trend = 'up' if predicted and prices and predicted[-1] > prices[-1] else 'down'

    stats = {
        'week_52_high': info.get('fiftyTwoWeekHigh', 0),
        'week_52_low':  info.get('fiftyTwoWeekLow', 0),
        'volume':       info.get('volume', 0),
        'market_cap':   info.get('marketCap', 0),
        'sector':       info.get('sector', 'N/A'),
        'pe_ratio':     round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 'N/A',
    }

    return render(request, 'portfolio/holding_detail.html', {
        'holding':        holding,
        'history':        history,
        'predicted':      predicted,
        'pred_upper':     pred_upper,
        'pred_lower':     pred_lower,
        'pred_model':     pred_model,
        'fut_dates':      fut_dates,
        'trend':          trend,
        'stats':          stats,
        'prices':         prices,
        'history_dates':  history_dates,
        'macd_line':      macd_line,
        'macd_signal':    macd_signal,
        'macd_hist':      macd_hist,
        'rsi_values':     rsi_values,
        'bb_mid':         bb_mid,
        'bb_upper':       bb_upper,
        'bb_lower':       bb_lower,
    })


@login_required
def add_stock(request):
    portfolio = get_or_create_portfolio(request.user)
    if portfolio.holdings.count() >= 10:
        messages.warning(request, 'Maximum of 10 holdings reached.')
        return redirect('portfolio:portfolio')

    if request.method == 'POST':
        form = AddHoldingForm(request.POST)
        if form.is_valid():
            symbol     = form.cleaned_data['symbol'].upper().strip()
            name       = form.cleaned_data['name']
            asset_type = form.cleaned_data['asset_type']
            quantity   = form.cleaned_data['quantity']
            price      = form.cleaned_data['price']
            notes      = form.cleaned_data['notes']

            if Holding.objects.filter(portfolio=portfolio, symbol=symbol).exists():
                messages.error(request, f'{symbol} already in portfolio. Use Buy More instead.')
                return render(request, 'portfolio/add_stock.html', {'form': form})

            Transaction.objects.create(
                portfolio=portfolio, symbol=symbol, name=name,
                asset_type=asset_type, transaction_type='buy',
                quantity=quantity, price=price,
                total_amount=quantity * price, notes=notes,
            )

            try:
                data = yf.Ticker(symbol).history(period='1d')
                current_price = round(float(data['Close'].iloc[-1]), 8) if not data.empty else price
            except Exception:
                current_price = price

            Holding.objects.create(
                portfolio=portfolio, symbol=symbol, name=name,
                asset_type=asset_type, quantity=quantity,
                avg_price=price, current_price=current_price,
            )

            messages.success(request, f'✅ Bought {quantity} {symbol} @ ${price}!')
            return redirect('portfolio:portfolio')
    else:
        form = AddHoldingForm()

    return render(request, 'portfolio/add_stock.html', {'form': form})


@login_required
def buy_more(request, holding_id):
    portfolio = get_or_create_portfolio(request.user)
    holding   = get_object_or_404(Holding, id=holding_id, portfolio=portfolio)

    if request.method == 'POST':
        form = BuyForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            price    = form.cleaned_data['price']
            notes    = form.cleaned_data['notes']

            Transaction.objects.create(
                portfolio=portfolio, symbol=holding.symbol, name=holding.name,
                asset_type=holding.asset_type, transaction_type='buy',
                quantity=quantity, price=price,
                total_amount=quantity * price, notes=notes,
            )

            old_total    = float(holding.quantity) * float(holding.avg_price)
            new_quantity = float(holding.quantity) + float(quantity)
            holding.avg_price = (old_total + float(quantity) * float(price)) / new_quantity
            holding.quantity  = new_quantity

            try:
                data = yf.Ticker(holding.symbol).history(period='1d')
                if not data.empty:
                    holding.current_price = round(float(data['Close'].iloc[-1]), 8)
            except Exception:
                pass

            holding.save()
            messages.success(request, f'✅ Bought {quantity} more {holding.symbol} @ ${price}!')
            return redirect('portfolio:portfolio')
    else:
        try:
            data  = yf.Ticker(holding.symbol).history(period='1d')
            price = round(float(data['Close'].iloc[-1]), 2) if not data.empty else float(holding.current_price)
        except Exception:
            price = float(holding.current_price)
        form = BuyForm(initial={'price': price})

    return render(request, 'portfolio/buy_more.html', {'form': form, 'holding': holding})


@login_required
def sell_holding(request, holding_id):
    portfolio = get_or_create_portfolio(request.user)
    holding   = get_object_or_404(Holding, id=holding_id, portfolio=portfolio)

    if request.method == 'POST':
        form = SellForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            price    = form.cleaned_data['price']
            notes    = form.cleaned_data['notes']

            if float(quantity) > float(holding.quantity):
                messages.error(request, f'You only own {holding.quantity} {holding.symbol}.')
                return render(request, 'portfolio/sell_holding.html', {'form': form, 'holding': holding})

            Transaction.objects.create(
                portfolio=portfolio, symbol=holding.symbol, name=holding.name,
                asset_type=holding.asset_type, transaction_type='sell',
                quantity=quantity, price=price,
                total_amount=quantity * price, notes=notes,
            )

            new_quantity = float(holding.quantity) - float(quantity)
            if new_quantity == 0:
                holding.delete()
                messages.success(request, f'✅ Sold all {holding.symbol} — removed from portfolio.')
            else:
                holding.quantity = new_quantity
                holding.save()
                messages.success(request, f'✅ Sold {quantity} {holding.symbol} @ ${price}!')

            return redirect('portfolio:portfolio')
    else:
        try:
            data  = yf.Ticker(holding.symbol).history(period='1d')
            price = round(float(data['Close'].iloc[-1]), 2) if not data.empty else float(holding.current_price)
        except Exception:
            price = float(holding.current_price)
        form = SellForm(initial={'price': price})

    return render(request, 'portfolio/sell_holding.html', {'form': form, 'holding': holding})


@login_required
def delete_stock(request, holding_id):
    portfolio = get_or_create_portfolio(request.user)
    holding   = get_object_or_404(Holding, id=holding_id, portfolio=portfolio)
    if request.method == 'POST':
        symbol = holding.symbol
        holding.delete()
        messages.success(request, f'{symbol} removed from portfolio.')
    return redirect('portfolio:portfolio')


@login_required
def transactions(request):
    portfolio = get_or_create_portfolio(request.user)
    return render(request, 'portfolio/transactions.html', {
        'portfolio':    portfolio,
        'transactions': _filtered_transactions(request, portfolio),
    })

def _filtered_transactions(request, portfolio):
    """ Helper function to filter transactions based on date, symbol and type."""
    qs = portfolio.transactions.all()

    start = request.GET.get('start')
    end = request.GET.get('end')
    symbol = request.GET.get('symbol', '').strip().upper()
    ttype = request.GET.get('type', '').strip().upper()

    if start:
        qs = qs.filter(date__date__gte=start)
    if end:
        qs = qs.filter(date__date__lte=end)
    if symbol:
        qs = qs.filter(symbol=symbol)
    if ttype in ('buy', 'sell'):
        qs = qs.filter(transaction_type=ttype)

    return qs

@login_required
def export_transactions_csv(request):
    portfolio = get_or_create_portfolio(request.user)
    transactions = _filtered_transactions(request, portfolio)

    filename = f'transactions_{request.user.username}_{date.today().isoformat()}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Symbol', 'Name', 'Asset Type', 'Transaction Type', 'Quantity', 'Price', 'Total Amount', 'Notes'])

    for t in transactions:
        writer.writerow([
            timezone.localtime(t.date).strftime('%Y-%m-%d %H:%M'),
            t.symbol,
            t.name,
            t.get_asset_type_display(),
            t.get_transaction_type_display(),
            f'{float(t.quantity):.8f}'.rstrip('0').rstrip('.'),
            f'{float(t.price):.2f}',
            f'{float(t.total_amount):.2f}',
            t.notes or '',
        ])


@login_required
def export_transactions_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    portfolio    = get_or_create_portfolio(request.user)
    transactions = _filtered_transactions(request, portfolio)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter),
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f'Transaction History — {portfolio.name}', styles['Title']))
    story.append(Paragraph(
        f'{request.user.username} &middot; Generated {timezone.localtime(timezone.now()).strftime("%b %d, %Y %H:%M")}',
        styles['Normal']
    ))
    story.append(Spacer(1, 16))

    buys  = [t for t in transactions if t.transaction_type == 'buy']
    sells = [t for t in transactions if t.transaction_type == 'sell']
    total_bought = sum(float(t.total_amount) for t in buys)
    total_sold   = sum(float(t.total_amount) for t in sells)

    summary_data = [
        ['Total Transactions', 'Buys', 'Sells', 'Total Bought', 'Total Sold'],
        [str(len(transactions)), str(len(buys)), str(len(sells)),
         f'${total_bought:,.2f}', f'${total_sold:,.2f}'],
    ]
    summary_table = Table(summary_data, hAlign='LEFT', colWidths=[1.8 * inch] * 5)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    table_data = [['Date', 'Symbol', 'Name', 'Asset', 'Type', 'Quantity', 'Price', 'Total', 'Notes']]
    for t in transactions:
        table_data.append([
            timezone.localtime(t.date).strftime('%Y-%m-%d %H:%M'),
            t.symbol,
            (t.name[:22] + '…') if len(t.name) > 22 else t.name,
            t.get_asset_type_display(),
            t.get_transaction_type_display(),
            f'{float(t.quantity):.4f}'.rstrip('0').rstrip('.'),
            f'${float(t.price):,.2f}',
            f'${float(t.total_amount):,.2f}',
            (t.notes[:20] + '…') if t.notes and len(t.notes) > 20 else (t.notes or '—'),
        ])

    if len(table_data) == 1:
        story.append(Paragraph('No transactions found for the selected filters.', styles['Normal']))
    else:
        col_widths = [1.1*inch, 0.7*inch, 1.7*inch, 0.6*inch, 0.6*inch, 0.9*inch, 0.9*inch, 1.0*inch, 1.6*inch]
        tx_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#111827')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d1d5db')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        # Color buy/sell rows in the "Type" column (index 4)
        for i, t in enumerate(transactions, start=1):
            color = colors.HexColor('#16a34a') if t.transaction_type == 'buy' else colors.HexColor('#dc2626')
            style_cmds.append(('TEXTCOLOR', (4, i), (4, i), color))
            style_cmds.append(('FONTNAME', (4, i), (4, i), 'Helvetica-Bold'))

        tx_table.setStyle(TableStyle(style_cmds))
        story.append(tx_table)

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        'Generated by Portfolio Analyzer. Past performance is not indicative of future results.',
        styles['Italic']
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f'transactions_{request.user.username}_{date.today().isoformat()}.pdf'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response     

@login_required
def price_alerts(request):
    if request.method == 'POST':
        form = PriceAlertForm(request.POST)
        if form.is_valid():
            alert      = form.save(commit=False)
            alert.user = request.user
            alert.save()
            messages.success(request, f'Alert set for {alert.symbol}!')
            return redirect('portfolio:price_alerts')
    else:
        form = PriceAlertForm()

    return render(request, 'portfolio/price_alerts.html', {
        'form':   form,
        'alerts': PriceAlert.objects.filter(user=request.user),
    })


@login_required
def delete_alert(request, alert_id):
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    if request.method == 'POST':
        alert.delete()
        messages.success(request, 'Alert deleted.')
    return redirect('portfolio:price_alerts')


@login_required
def toggle_alert(request, alert_id):
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    if request.method == 'POST':
        alert.is_active = not alert.is_active
        alert.save()
        messages.success(request, f'Alert {"activated" if alert.is_active else "paused"}.')
    return redirect('portfolio:price_alerts')


@login_required
def watchlist(request):
    if request.method == 'POST':
        form = WatchlistForm(request.POST)
        if form.is_valid():
            symbol     = form.cleaned_data['symbol'].upper().strip()
            name       = form.cleaned_data['name']
            asset_type = form.cleaned_data['asset_type']
            item, created = WatchlistItem.objects.get_or_create(
                user=request.user, symbol=symbol,
                defaults={'name': name, 'asset_type': asset_type}
            )
            messages.success(request, f'{symbol} {"added to" if created else "already in"} watchlist.')
            return redirect('portfolio:watchlist')
    else:
        form = WatchlistForm()

    update_watchlist_prices(request.user)
    return render(request, 'portfolio/watchlist.html', {
        'form':  form,
        'items': WatchlistItem.objects.filter(user=request.user),
    })


@login_required
def delete_watchlist(request, item_id):
    item = get_object_or_404(WatchlistItem, id=item_id, user=request.user)
    if request.method == 'POST':
        item.delete()
        messages.success(request, f'{item.symbol} removed from watchlist.')
    return redirect('portfolio:watchlist')


@login_required
def ai_chat(request):
    portfolio  = get_or_create_portfolio(request.user)
    holdings   = portfolio.holdings.all()
    context    = get_portfolio_summary(portfolio)
    allocation = get_asset_allocation(portfolio)
    trend      = get_portfolio_trend(list(holdings))

    ai_response = None
    user_query  = None

    if request.method == 'POST':
        action     = request.POST.get('action', 'chat')
        user_query = request.POST.get('query', '').strip()

        if action == 'analyze':
            ai_response = analyze_portfolio(context)
            user_query  = "Analyze my portfolio"
        elif action == 'risk':
            ai_response = get_risk_assessment(context)
            user_query  = "Assess my portfolio risk"
        elif action == 'suggest':
            ai_response = get_buy_sell_suggestions(context)
            user_query  = "Give me buy/sell suggestions"
        elif action == 'chat' and user_query:
            ai_response = ask_llm(user_query, context)
        else:
            messages.warning(request, 'Please enter a question.')

    return render(request, 'portfolio/ai_chat.html', {
        'portfolio':   portfolio,
        'holdings':    holdings,
        'allocation':  allocation,
        'trend':       trend,
        'ai_response': ai_response,
        'user_query':  user_query,
    })