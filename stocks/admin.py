from django.contrib import admin
from .models import StockCache


@admin.register(StockCache)
class StockCacheAdmin(admin.ModelAdmin):
    list_display  = ['symbol', 'name', 'current_price', 'price_change', 'volume', 'last_updated']
    search_fields = ['symbol', 'name']