import pytest
from django.urls import reverse
from django.test import Client
from django.utils import timezone
from cinema.models import Ticket, Review, Showtime, NewsArticle


@pytest.mark.django_db
class TestPublicViews:
    """Тесты публичных представлений."""

    def test_index_view(self):
        response = Client().get(reverse('index'))
        assert response.status_code == 200

    def test_about_view(self):
        response = Client().get(reverse('about'))
        assert response.status_code == 200

    def test_movies_list_view(self):
        response = Client().get(reverse('movies_list'))
        assert response.status_code == 200

    def test_contacts_view(self):
        response = Client().get(reverse('contacts'))
        assert response.status_code == 200

    def test_reviews_view(self):
        response = Client().get(reverse('reviews'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAuthViews:
    """Тесты представлений аутентификации."""

    def test_login_view_get(self):
        response = Client().get(reverse('login'))
        assert response.status_code == 200

    def test_register_view_get(self):
        response = Client().get(reverse('register'))
        assert response.status_code == 200

    def test_logout_view(self, user):
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('logout'))
        assert response.status_code == 302


@pytest.mark.django_db
class TestMovieDetailView:
    """Тесты детальной страницы фильма."""

    def test_movie_detail_view(self, movie):
        response = Client().get(reverse('movie_detail', args=[movie.id]))
        assert response.status_code == 200

    def test_movie_detail_with_employee(self, movie, staff_user):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.get(reverse('movie_detail', args=[movie.id]))
        assert response.status_code == 200

    def test_movie_detail_not_found(self):
        response = Client().get(reverse('movie_detail', args=[9999]))
        assert response.status_code == 404


@pytest.mark.django_db
class TestBookingViews:
    """Тесты бронирования билетов."""

    def test_select_seats_authenticated(self, user, showtime):
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('select_seats', args=[showtime.id]))
        assert response.status_code == 200

    def test_select_seats_unauthenticated(self, showtime):
        response = Client().get(reverse('select_seats', args=[showtime.id]))
        assert response.status_code == 302

    def test_book_ticket_action(self, user, showtime):
        def test_book_ticket_action(self, user, showtime):
            """Тест создания билета напрямую."""
            ticket = Ticket.objects.create(
                showtime=showtime,
                customer=user,
                row=3,
                seat=3
            )
            assert ticket.row == 3
            assert ticket.seat == 3
            assert ticket.customer == user

    def test_book_taken_seat(self, user, showtime):
        """Тест попытки забронировать уже занятое место."""
        Ticket.objects.create(showtime=showtime, customer=user, row=3, seat=3)
        client = Client()
        client.login(username='testuser', password='testpass123')
        # Пробуем забронировать то же место
        response = client.post(
            reverse('select_seats', args=[showtime.id]),
            {'row': 3, 'seat': 3}
        )
        # Должен остаться только один билет на это место
        count = Ticket.objects.filter(showtime=showtime, row=3, seat=3).count()
        assert count == 1

    def test_delete_ticket(self, user, showtime):
        ticket = Ticket.objects.create(showtime=showtime, customer=user, row=5, seat=5)
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.post(reverse('delete_ticket', args=[ticket.id]))
        assert response.status_code == 302
        assert not Ticket.objects.filter(id=ticket.id).exists()

    def test_edit_ticket_view(self, user, showtime):
        ticket = Ticket.objects.create(showtime=showtime, customer=user, row=5, seat=5)
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('edit_ticket', args=[ticket.id]))
        assert response.status_code == 200


@pytest.mark.django_db
class TestProfileView:
    """Тесты личного кабинета."""

    def test_profile_view_authenticated(self, user):
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('profile'))
        assert response.status_code == 200

    def test_profile_view_unauthenticated(self):
        response = Client().get(reverse('profile'))
        assert response.status_code == 302

    def test_profile_staff_view(self, staff_user):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.get(reverse('profile'))
        assert response.status_code == 200

    def test_profile_with_tickets(self, user, ticket):
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('profile'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestStaffViews:
    """Тесты представлений для сотрудников."""

    def test_news_create_staff(self, staff_user):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.get(reverse('news_create'))
        assert response.status_code == 200

    def test_news_create_regular_user(self, user):
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('news_create'))
        assert response.status_code == 302

    def test_news_create_post(self, staff_user):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.post(reverse('news_create'), {
            'title': 'Новость',
            'short_description': 'Кратко',
            'content': 'Содержание',
        })
        assert response.status_code == 302
        assert NewsArticle.objects.filter(title='Новость').exists()

    def test_news_update_view(self, staff_user, news_article):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.get(reverse('news_update', args=[news_article.id]))
        assert response.status_code == 200

    def test_news_delete_view(self, staff_user, news_article):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.get(reverse('news_delete', args=[news_article.id]))
        assert response.status_code == 200

    def test_news_delete_post(self, staff_user, news_article):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.post(reverse('news_delete', args=[news_article.id]))
        assert response.status_code == 302
        assert not NewsArticle.objects.filter(id=news_article.id).exists()


@pytest.mark.django_db
class TestReviewsView:
    """Тесты отзывов."""

    def test_create_review(self, user):
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.post(reverse('reviews'), {
            'rating': 4,
            'text': 'Хороший фильм',
        })
        assert response.status_code == 302
        assert Review.objects.filter(user=user, rating=4).exists()

    def test_staff_cannot_review(self, staff_user):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.post(reverse('reviews'), {
            'rating': 4,
            'text': 'Хороший фильм',
        })
        assert response.status_code == 302
        assert not Review.objects.filter(user=staff_user).exists()

    def test_unauthenticated_review_redirect(self):
        client = Client()
        response = client.post(reverse('reviews'), {'rating': 4, 'text': 'Тест'})
        assert response.status_code == 302

    def test_reviews_with_existing_review(self, user, review):
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('reviews'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestPromoCodeInList:
    """Тесты отображения промокодов."""

    def test_movies_list_with_promo(self, promo_code):
        response = Client().get(reverse('movies_list'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'TEST10' in content


@pytest.mark.django_db
class TestRegistrationView:
    """Тесты регистрации."""

    def test_register_post_success(self):
        client = Client()
        response = client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'age': 20,
            'email': 'new@example.com',
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'phone': '+375 (29) 123-45-67',
        })
        assert response.status_code == 302

    def test_register_underage(self):
        client = Client()
        response = client.post(reverse('register'), {
            'username': 'younguser',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'age': 15,
        })
        assert response.status_code == 200


@pytest.mark.django_db
class TestLoginView:
    """Тесты входа."""

    def test_login_post_success(self, user):
        client = Client()
        response = client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        assert response.status_code == 302

    def test_login_post_fail(self):
        client = Client()
        response = client.post(reverse('login'), {
            'username': 'wrong',
            'password': 'wrong',
        })
        assert response.status_code == 200


@pytest.mark.django_db
class TestNewsDetailView:
    """Тесты страницы новости."""

    def test_news_update_post(self, staff_user, news_article):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.post(reverse('news_update', args=[news_article.id]), {
            'title': 'Обновленная новость',
            'short_description': 'Новое описание',
            'content': 'Новый контент',
        })
        assert response.status_code == 302


@pytest.mark.django_db
class TestEditTicketView:
    """Тесты редактирования билета."""

    def test_edit_ticket_post(self, user, showtime):
        ticket = Ticket.objects.create(showtime=showtime, customer=user, row=5, seat=5)
        client = Client()
        client.login(username='testuser', password='testpass123')
        response = client.post(reverse('edit_ticket', args=[ticket.id]), {
            'row': 7,
            'seat': 7,
        })
        assert response.status_code == 302


@pytest.mark.django_db
class TestProfileStaffCharts:
    """Тесты графиков в профиле сотрудника."""

    def test_profile_staff_with_data(self, staff_user, ticket):
        client = Client()
        client.login(username='staffuser', password='testpass123')
        response = client.get(reverse('profile'))
        assert response.status_code == 200

    def test_profile_superuser_with_data(self, superuser, ticket):
        client = Client()
        client.login(username='admin', password='admin123')
        response = client.get(reverse('profile'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestContactEmployeeViews:
    """Тесты контактов сотрудников."""

    def test_contacts_with_employees(self, staff_user):
        response = Client().get(reverse('contacts'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestMovieListFilters:
    """Тесты фильтрации фильмов."""

    def test_movies_filter_by_genre(self, movie, genre):
        response = Client().get(f"{reverse('movies_list')}?genre={genre.id}")
        assert response.status_code == 200

    def test_movies_filter_by_country(self, movie, country):
        response = Client().get(f"{reverse('movies_list')}?country={country.id}")
        assert response.status_code == 200

    def test_movies_search(self, movie):
        response = Client().get(f"{reverse('movies_list')}?search=Тестовый")
        assert response.status_code == 200

    def test_movies_sort(self):
        response = Client().get(f"{reverse('movies_list')}?ordering=-rating")
        assert response.status_code == 200