import os
import django
import pytest
from django.contrib.auth.models import User
from cinema.models import (
    UserProfile, Movie, Genre, Country, CinemaHall, Showtime,
    Ticket, Review, NewsArticle, PromoCode, ContactEmployee,
    AboutCompany, FAQItem, JobVacancy, PrivacyPolicy
)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()


@pytest.fixture
def user(db):
    """Обычный пользователь."""
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='testuser@example.com'
    )


@pytest.fixture
def staff_user(db):
    """Сотрудник."""
    user = User.objects.create_user(
        username='staffuser',
        password='testpass123',
        email='staff@example.com',
        is_staff=True
    )
    ContactEmployee.objects.create(
        user=user,
        position='Менеджер',
        is_visible=True
    )
    return user


@pytest.fixture
def superuser(db):
    """Суперпользователь."""
    return User.objects.create_superuser(
        username='admin',
        password='admin123',
        email='admin@example.com'
    )


@pytest.fixture
def user_profile(db, user):
    """Профиль пользователя."""
    return UserProfile.objects.get(user=user)


@pytest.fixture
def genre(db):
    """Жанр фильма."""
    return Genre.objects.create(name='Боевик')


@pytest.fixture
def country(db):
    """Страна производства."""
    return Country.objects.create(name='США')


@pytest.fixture
def movie(db, genre, country):
    """Фильм."""
    movie = Movie.objects.create(
        title_ru='Тестовый фильм',
        title_en='Test Movie',
        description='Описание тестового фильма',
        duration=120,
        budget=1000000,
        rating=8.5
    )
    movie.genres.add(genre)
    movie.countries.add(country)
    return movie


@pytest.fixture
def cinema_hall(db):
    """Кинозал."""
    return CinemaHall.objects.create(
        name='Зал 1',
        rows_count=10,
        seats_per_row=10
    )


@pytest.fixture
def showtime(db, movie, cinema_hall):
    """Сеанс."""
    from django.utils import timezone
    return Showtime.objects.create(
        movie=movie,
        hall=cinema_hall,
        start_time=timezone.now() + timezone.timedelta(days=1),
        ticket_price=15.00
    )


@pytest.fixture
def ticket(db, showtime, user):
    """Билет."""
    return Ticket.objects.create(
        showtime=showtime,
        customer=user,
        row=1,
        seat=1
    )


@pytest.fixture
def review(db, user):
    """Отзыв."""
    return Review.objects.create(
        user=user,
        rating=5,
        text='Отличный фильм!'
    )


@pytest.fixture
def news_article(db):
    """Новость."""
    return NewsArticle.objects.create(
        title='Тестовая новость',
        short_description='Краткое описание',
        content='Полный текст новости'
    )


@pytest.fixture
def promo_code(db):
    """Промокод."""
    return PromoCode.objects.create(
        code='TEST10',
        description='Скидка 10%',
        is_active=True
    )