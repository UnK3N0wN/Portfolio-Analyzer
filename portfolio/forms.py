from django import forms
from .models import PriceAlert


class AddHoldingForm(forms.Form):
    ASSET_TYPES = [('stock', 'Stock'), ('crypto', 'Crypto')]

    symbol     = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AAPL or BTC-USD'}))
    name       = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Apple Inc.'}))
    asset_type = forms.ChoiceField(choices=ASSET_TYPES, widget=forms.Select(attrs={'class': 'form-control'}))
    quantity   = forms.DecimalField(max_digits=20, decimal_places=8, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10', 'step': 'any'}))
    price      = forms.DecimalField(max_digits=20, decimal_places=8, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 150.00', 'step': 'any'}))
    notes      = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'}))


class BuyForm(forms.Form):
    quantity = forms.DecimalField(max_digits=20, decimal_places=8, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity to buy', 'step': 'any'}))
    price    = forms.DecimalField(max_digits=20, decimal_places=8, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price per unit', 'step': 'any'}))
    notes    = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'}))


class SellForm(forms.Form):
    quantity = forms.DecimalField(max_digits=20, decimal_places=8, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity to sell', 'step': 'any'}))
    price    = forms.DecimalField(max_digits=20, decimal_places=8, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sell price per unit', 'step': 'any'}))
    notes    = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'}))


class PriceAlertForm(forms.ModelForm):
    class Meta:
        model   = PriceAlert
        fields  = ['symbol', 'name', 'alert_type', 'target_price']
        widgets = {
            'symbol':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AAPL'}),
            'name':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Apple Inc.'}),
            'alert_type':   forms.Select(attrs={'class': 'form-control'}),
            'target_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 200.00', 'step': 'any'}),
        }


class WatchlistForm(forms.Form):
    ASSET_TYPES = [('stock', 'Stock'), ('crypto', 'Crypto')]

    symbol     = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AAPL'}))
    name       = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Apple Inc.'}))
    asset_type = forms.ChoiceField(choices=ASSET_TYPES, widget=forms.Select(attrs={'class': 'form-control'}))