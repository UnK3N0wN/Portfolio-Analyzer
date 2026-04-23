from django.urls import path
from . import views

app_name = 'portfolio'

urlpatterns = [
    path('',                                        views.landing,         name='landing'),
    path('dashboard/',                              views.dashboard,       name='dashboard'),
    path('portfolio/',                              views.portfolio_view,  name='portfolio'),
    path('portfolio/add/',                          views.add_stock,       name='add_stock'),
    path('portfolio/<int:holding_id>/',             views.holding_detail,  name='holding_detail'),
    path('portfolio/buy/<int:holding_id>/',         views.buy_more,        name='buy_more'),
    path('portfolio/sell/<int:holding_id>/',        views.sell_holding,    name='sell_holding'),
    path('portfolio/delete/<int:holding_id>/',      views.delete_stock,    name='delete_stock'),
    path('transactions/',                           views.transactions,    name='transactions'),
    path('ai/',                                     views.ai_chat,         name='ai_chat'),
    path('alerts/',                                 views.price_alerts,    name='price_alerts'),
    path('alerts/delete/<int:alert_id>/',           views.delete_alert,    name='delete_alert'),
    path('alerts/toggle/<int:alert_id>/',           views.toggle_alert,    name='toggle_alert'),
    path('watchlist/',                              views.watchlist,       name='watchlist'),
    path('watchlist/delete/<int:item_id>/',         views.delete_watchlist,name='delete_watchlist'),
]