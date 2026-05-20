import pytest
from django.core.exceptions import ValidationError
from cinema.models import (
    UserProfile, Movie, CinemaHall, Showtime, Ticket, Review,
    NewsArticle, PromoCode, ContactEmployee, AboutCompany,
    FAQItem, JobVacancy, PrivacyPolicy, Genre, Country
)


@pytest.mark.django_db
class TestUserProfile:
    """Тесты модели UserProfile."""

    def test_create_profile(self, user, user_profile):
        assert user_profile.user == user
        assert user_profile.age == 18

    def test_str_method(self, user_profile, user):
        assert str(user_profile) == f"Профиль: {user.username} (Возраст: {user_profile.age})"

    def test_validate_age(self):
        with pytest.raises(ValidationError):
            profile = UserProfile(age=15)
            profile.full_clean()

    def test_phone_format(self, user_profile):
        user_profile.phone = '+375 (29) 123-45-67'
        user_profile.full_clean()

    def test_invalid_phone_format(self, user_profile):
        user_profile.phone = '12345'
        with pytest.raises(ValidationError):
            user_profile.full_clean()


@pytest.mark.django_db
class TestMovie:
    """Тесты модели Movie."""

    def test_create_movie(self, movie):
        assert movie.title_ru == 'Тестовый фильм'
        assert movie.title_en == 'Test Movie'
        assert movie.duration == 120
        assert float(movie.budget) == 1000000.0
        assert float(movie.rating) == 8.5

    def test_str_method(self, movie):
        assert str(movie) == "Тестовый фильм (Test Movie)"

    def test_genres_relation(self, movie, genre):
        assert genre in movie.genres.all()

    def test_countries_relation(self, movie, country):
        assert country in movie.countries.all()


@pytest.mark.django_db
class TestCinemaHall:
    """Тесты модели CinemaHall."""

    def test_create_hall(self, cinema_hall):
        assert cinema_hall.name == 'Зал 1'
        assert cinema_hall.rows_count == 10
        assert cinema_hall.seats_per_row == 10
        assert cinema_hall.capacity == 100

    def test_capacity_calculation(self):
        hall = CinemaHall.objects.create(name='Зал 2', rows_count=15, seats_per_row=20)
        assert hall.capacity == 300

    def test_str_method(self, cinema_hall):
        expected = "Зал 1 (Рядов: 10, Мест в ряду: 10, Всего: 100)"
        assert str(cinema_hall) == expected


@pytest.mark.django_db
class TestShowtime:
    """Тесты модели Showtime."""

    def test_create_showtime(self, showtime, movie, cinema_hall):
        assert showtime.movie == movie
        assert showtime.hall == cinema_hall
        assert float(showtime.ticket_price) == 15.00

    def test_str_method(self, showtime):
        assert 'Тестовый фильм' in str(showtime)
        assert 'Зал 1' in str(showtime)


@pytest.mark.django_db
class TestTicket:
    """Тесты модели Ticket."""

    def test_create_ticket(self, ticket, showtime, user):
        assert ticket.showtime == showtime
        assert ticket.customer == user
        assert ticket.row == 1
        assert ticket.seat == 1

    def test_unique_constraint(self, showtime, user):
        Ticket.objects.create(showtime=showtime, customer=user, row=2, seat=2)
        with pytest.raises(Exception):
            Ticket.objects.create(showtime=showtime, customer=user, row=2, seat=2)

    def test_str_method(self, ticket, showtime):
        assert str(ticket).startswith(f"Билет #{ticket.id}")


@pytest.mark.django_db
class TestReview:
    """Тесты модели Review."""

    def test_create_review(self, review, user):
        assert review.user == user
        assert review.rating == 5
        assert review.text == 'Отличный фильм!'

    def test_rating_min_validator(self, user):
        review = Review(user=user, rating=0, text='Плохо')
        with pytest.raises(ValidationError):
            review.full_clean()

    def test_rating_max_validator(self, user):
        review = Review(user=user, rating=6, text='Супер')
        with pytest.raises(ValidationError):
            review.full_clean()

    def test_str_method(self, review, user):
        assert str(review) == f"Отзыв от {user.username} (Оценка: 5)"

    def test_ordering(self, user):
        r1 = Review.objects.create(user=user, rating=3, text='Первый')
        r2 = Review.objects.create(user=user, rating=4, text='Второй')
        assert list(Review.objects.all())[0] == r2


@pytest.mark.django_db
class TestNewsArticle:
    """Тесты модели NewsArticle."""

    def test_create_article(self, news_article):
        assert news_article.title == 'Тестовая новость'
        assert news_article.short_description == 'Краткое описание'
        assert news_article.content == 'Полный текст новости'

    def test_str_method(self, news_article):
        assert str(news_article) == 'Тестовая новость'


@pytest.mark.django_db
class TestPromoCode:
    """Тесты модели PromoCode."""

    def test_create_promo(self, promo_code):
        assert promo_code.code == 'TEST10'
        assert promo_code.is_active is True

    def test_str_method_active(self, promo_code):
        assert 'Активен' in str(promo_code)

    def test_str_method_archived(self):
        promo = PromoCode.objects.create(code='OLD50', description='Старая скидка', is_active=False)
        assert 'В архиве' in str(promo)


@pytest.mark.django_db
class TestContactEmployee:
    """Тесты модели ContactEmployee."""

    def test_create_contact(self, staff_user):
        contact = ContactEmployee.objects.get(user=staff_user)
        assert contact.position == 'Менеджер'
        assert contact.is_visible is True

    def test_get_full_name(self, staff_user):
        contact = ContactEmployee.objects.get(user=staff_user)
        assert contact.get_full_name() == staff_user.username

    def test_get_phone_from_profile(self, staff_user):
        contact = ContactEmployee.objects.get(user=staff_user)
        staff_user.profile.phone = '+375 (29) 111-22-33'
        staff_user.profile.save()
        assert contact.get_phone() == '+375 (29) 111-22-33'

    def test_get_email_fallback(self, staff_user):
        contact = ContactEmployee.objects.get(user=staff_user)
        assert contact.get_email() == staff_user.email


@pytest.mark.django_db
class TestAboutCompany:
    """Тесты модели AboutCompany."""

    def test_create(self):
        company = AboutCompany.objects.create(
            title='Тестовая компания',
            description='Описание',
            requisites='Реквизиты'
        )
        assert str(company) == 'Тестовая компания'


@pytest.mark.django_db
class TestFAQItem:
    """Тесты модели FAQItem."""

    def test_create(self):
        faq = FAQItem.objects.create(question='Вопрос?', answer='Ответ.')
        assert str(faq) == 'Вопрос?'


@pytest.mark.django_db
class TestJobVacancy:
    """Тесты модели JobVacancy."""

    def test_create(self):
        vacancy = JobVacancy.objects.create(
            title='Вакансия',
            description='Описание',
            salary='1000 BYN'
        )
        assert str(vacancy) == 'Вакансия'
        assert vacancy.is_active is True

    def test_inactive_vacancy(self):
        vacancy = JobVacancy.objects.create(
            title='Закрыта',
            description='Описание',
            is_active=False
        )
        assert vacancy.is_active is False


@pytest.mark.django_db
class TestPrivacyPolicy:
    """Тесты модели PrivacyPolicy."""

    def test_create(self):
        policy = PrivacyPolicy.objects.create(content='Текст политики')
        assert str(policy) == 'Политика конфиденциальности'


@pytest.mark.django_db
class TestGenre:
    """Тесты модели Genre."""

    def test_create(self, genre):
        assert str(genre) == 'Боевик'

    def test_unique_name(self):
        Genre.objects.create(name='Комедия')
        with pytest.raises(Exception):
            Genre.objects.create(name='Комедия')


@pytest.mark.django_db
class TestCountry:
    """Тесты модели Country."""

    def test_create(self, country):
        assert str(country) == 'США'

    def test_unique_name(self):
        Country.objects.create(name='Россия')
        with pytest.raises(Exception):
            Country.objects.create(name='Россия')


@pytest.mark.django_db
class TestTimeStampedModel:
    """Тесты временных меток."""

    def test_created_at_set(self, movie):
        assert movie.created_at_utc is not None
        assert movie.created_at_local is not None

    def test_updated_at_after_save(self, movie):
        movie.title_ru = 'Обновленный фильм'
        movie.save()
        assert movie.updated_at_utc is not None
        assert movie.updated_at_local is not None

    def test_timezone_difference(self, movie):
        """Проверка, что created_at_utc и created_at_local не None."""
        assert movie.created_at_utc is not None
        assert movie.created_at_local is not None


@pytest.mark.django_db
class TestMovieAdditional:
    """Дополнительные тесты Movie."""

    def test_movie_default_image(self, movie):
        assert not movie.poster

    def test_movie_multiple_genres(self, movie):
        genre2 = Genre.objects.create(name='Драма')
        movie.genres.add(genre2)
        assert movie.genres.count() == 2


@pytest.mark.django_db
class TestCinemaHallAdditional:
    """Дополнительные тесты CinemaHall."""

    def test_hall_capacity_update(self):
        hall = CinemaHall.objects.create(name='Тест', rows_count=5, seats_per_row=8)
        assert hall.capacity == 40
        hall.rows_count = 10
        hall.save()
        assert hall.capacity == 80


@pytest.mark.django_db
class TestShowtimeAdditional:
    """Дополнительные тесты Showtime."""

    def test_showtime_ordering(self, movie, cinema_hall):
        from django.utils import timezone
        s1 = Showtime.objects.create(
            movie=movie, hall=cinema_hall,
            start_time=timezone.now() + timezone.timedelta(days=2),
            ticket_price=10.00
        )
        s2 = Showtime.objects.create(
            movie=movie, hall=cinema_hall,
            start_time=timezone.now() + timezone.timedelta(days=1),
            ticket_price=15.00
        )
        showtimes = list(Showtime.objects.all())
        assert showtimes[0] == s2


@pytest.mark.django_db
class TestTicketAdditional:
    """Дополнительные тесты Ticket."""

    def test_ticket_customer_null(self, showtime):
        ticket = Ticket.objects.create(showtime=showtime, row=10, seat=10)
        assert ticket.customer is None

    def test_ticket_str_contains_movie(self, ticket, showtime):
        assert showtime.movie.title_ru in str(ticket)


@pytest.mark.django_db
class TestReviewAdditional:
    """Дополнительные тесты Review."""

    def test_review_text_content(self, review):
        assert len(review.text) > 0

    def test_review_rating_range(self, user):
        for r in [1, 2, 3, 4, 5]:
            review = Review.objects.create(user=user, rating=r, text=f'Оценка {r}')
            review.full_clean()
            assert review.rating == r


@pytest.mark.django_db
class TestUserProfileAdditional:
    """Дополнительные тесты UserProfile."""

    def test_profile_auto_created(self, user):
        assert hasattr(user, 'profile')
        assert user.profile.age == 18

    def test_profile_photo_upload(self, user_profile):
        user_profile.photo = 'users_photos/test.jpg'
        user_profile.save()
        assert user_profile.photo == 'users_photos/test.jpg'