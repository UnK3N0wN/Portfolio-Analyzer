from django.db import models


class StockCache(models.Model):
    symbol        = models.CharField(max_length=20, unique=True)
    name          = models.CharField(max_length=100)
    asset_type    = models.CharField(max_length=10, default='stock')
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    open_price    = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    high_price    = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    low_price     = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    volume        = models.BigIntegerField(default=0)
    market_cap    = models.BigIntegerField(default=0)
    week_52_high  = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    week_52_low   = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    sector        = models.CharField(max_length=100, blank=True, null=True)
    last_updated  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.symbol} — {self.name}'

    def price_change(self):
        if float(self.open_price) == 0:
            return 0
        return float(self.current_price) - float(self.open_price)

    def price_change_percent(self):
        if float(self.open_price) == 0:
            return 0
        return ((float(self.current_price) - float(self.open_price)) / float(self.open_price)) * 100
    
    