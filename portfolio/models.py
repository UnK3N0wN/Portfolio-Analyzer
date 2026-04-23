from django.db import models
from django.contrib.auth.models import User


class Portfolio(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='portfolio')
    name       = models.CharField(max_length=100, default='My Portfolio')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.name}'

    def total_value(self):
        return sum(h.current_value() for h in self.holdings.all())

    def total_invested(self):
        return sum(h.total_invested() for h in self.holdings.all())

    def total_profit_loss(self):
        return self.total_value() - self.total_invested()

    def profit_loss_percent(self):
        invested = self.total_invested()
        if invested == 0:
            return 0
        return ((self.total_value() - invested) / invested) * 100


class Holding(models.Model):
    ASSET_TYPES = [('stock', 'Stock'), ('crypto', 'Crypto')]

    portfolio     = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='holdings')
    symbol        = models.CharField(max_length=20)
    name          = models.CharField(max_length=100)
    asset_type    = models.CharField(max_length=10, choices=ASSET_TYPES, default='stock')
    quantity      = models.DecimalField(max_digits=20, decimal_places=8)
    avg_price     = models.DecimalField(max_digits=20, decimal_places=8)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    last_updated  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['portfolio', 'symbol']

    def __str__(self):
        return f'{self.symbol} - {self.quantity}'

    def total_invested(self):
        return float(self.quantity) * float(self.avg_price)

    def current_value(self):
        return float(self.quantity) * float(self.current_price)

    def profit_loss(self):
        return self.current_value() - self.total_invested()

    def profit_loss_percent(self):
        invested = self.total_invested()
        if invested == 0:
            return 0
        return ((self.current_value() - invested) / invested) * 100


class Transaction(models.Model):
    TRANSACTION_TYPES = [('buy', 'Buy'), ('sell', 'Sell')]

    portfolio        = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='transactions')
    symbol           = models.CharField(max_length=20)
    name             = models.CharField(max_length=100)
    asset_type       = models.CharField(max_length=10, choices=Holding.ASSET_TYPES, default='stock')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity         = models.DecimalField(max_digits=20, decimal_places=8)
    price            = models.DecimalField(max_digits=20, decimal_places=8)
    total_amount     = models.DecimalField(max_digits=20, decimal_places=8)
    date             = models.DateTimeField(auto_now_add=True)
    notes            = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.transaction_type.upper()} {self.quantity} {self.symbol} @ {self.price}'

class PriceAlert(models.Model):
    ALERT_TYPES = [
        ('above', 'Price goes above'),
        ('below', 'Price goes below'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='price_alerts')
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPES)
    target_price = models.DecimalField(max_digits=20, decimal_places=8)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    is_triggered = models.BooleanField(default=False)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    triggered_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.symbol} {self.alert_type} ${self.target_price}'
    
    def check_trigger(self):
        if not self.is_active or self.is_triggered:
            return False
        price  = float(self.current_price)
        target = float(self.target_price)
        if self.alert_type == 'above' and price >= target:
            return True
        if self.alert_type == 'below' and price <= target:
            return True
        return False

class WatchlistItem(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    symbol        = models.CharField(max_length=20)
    name          = models.CharField(max_length=100)
    asset_type    = models.CharField(max_length=10, choices=Holding.ASSET_TYPES, default='stock')
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    added_at      = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ['user', 'symbol']
        ordering        = ['-added_at']
 
    def __str__(self):
        return f'{self.user.username} watching {self.symbol}'
 
 
class PortfolioSnapshot(models.Model):
    portfolio      = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='snapshots')
    date           = models.DateField()
    total_value    = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    profit_loss    = models.DecimalField(max_digits=20, decimal_places=2, default=0)
 
    class Meta:
        ordering        = ['date']
        unique_together = ['portfolio', 'date']
 
    def __str__(self):
        return f'{self.portfolio} snapshot {self.date}'