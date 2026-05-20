import pytest
from django.test import Client
from cinema.forms import ReviewForm


@pytest.mark.django_db
class TestReviewForm:
    """Тесты формы отзыва."""

    def test_valid_form(self):
        form_data = {'rating': 5, 'text': 'Отличный фильм!'}
        form = ReviewForm(data=form_data)
        assert form.is_valid()

    def test_invalid_rating(self):
        form_data = {'rating': 6, 'text': 'Слишком высокая оценка'}
        form = ReviewForm(data=form_data)
        assert not form.is_valid()

    def test_empty_text(self):
        form_data = {'rating': 3, 'text': ''}
        form = ReviewForm(data=form_data)
        assert not form.is_valid()