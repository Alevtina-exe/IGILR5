from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f"{i} ★") for i in range(5, 0, -1)],
                attrs={'style': 'width: 100%; padding: 10px; border-radius: 4px; border: 1px solid #ccc; font-size: 16px;'}
            ),
            'text': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'Поделитесь своими впечатлениями о кинотеатре...', 'style': 'width: 100%; padding: 12px; border-radius: 4px; border: 1px solid #ccc; font-size: 15px; resize: vertical; font-family: inherit;'}
            ),
        }