from django import forms


class StockSearchForm(forms.Form):

    symbol = forms.CharField(
        max_length=20,
        label="Ticker Symbol",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search AAPL, TSLA, BTC-USD"
            }
        )
    )

    def clean_symbol(self):

        symbol = self.cleaned_data["symbol"].upper().strip()

        if len(symbol) < 1:
            raise forms.ValidationError("Invalid ticker symbol")

        return symbol