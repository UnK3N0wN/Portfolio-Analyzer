from django.contrib import admin
from .models import Portfolio, Holding, Transaction, PriceAlert, WatchlistItem, PortfolioSnapshot


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'created_at']


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'symbol', 'name', 'asset_type', 'quantity', 'avg_price', 'current_price']
    list_filter  = ['asset_type']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'symbol', 'transaction_type', 'quantity', 'price', 'total_amount', 'date']
    list_filter  = ['transaction_type', 'asset_type']


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'symbol', 'alert_type', 'target_price', 'current_price', 'is_triggered', 'is_active']
    list_filter  = ['alert_type', 'is_triggered', 'is_active']


@admin.register(WatchlistItem)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'symbol', 'name', 'current_price', 'added_at']


@admin.register(PortfolioSnapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'date', 'total_value', 'profit_loss']