from django.urls import path
from . import views

app_name = 'stocks'

urlpatterns = [
    path('search/',          views.search,       name='search'),
    path('<str:symbol>/',    views.stock_detail, name='detail'),
]