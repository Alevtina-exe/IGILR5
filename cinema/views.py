import base64
import calendar
import io
from datetime import datetime, timedelta

import matplotlib
import matplotlib.pyplot as plt
import requests
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ReviewForm
from .models import *

matplotlib.use('Agg')

logger = logging.getLogger('cinema.views')


def is_staff_or_admin(user):
    """Проверяет, является ли пользователь сотрудником или администратором."""
    return user.is_superuser or hasattr(user, 'employee_contact')


def get_movie_data_from_api(movie_title):
    """Получает данные о фильме из внешнего API."""
    api_key = "d91bc258"
    safe_title = str(movie_title).strip().replace(' ', '+')
    url = f"http://www.omdbapi.com/?apikey={api_key}&t={safe_title}"

    default_data = {
        'imdb_rating': 'N/A',
        'director': 'Не указан',
        'year': '—'
    }

    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('Response') == 'True':
                logger.debug(f"Данные API получены для фильма: {movie_title}")
                return {
                    'imdb_rating': data.get('imdbRating', 'N/A'),
                    'director': data.get('Director', 'Не указан'),
                    'year': data.get('Year', '—')
                }
    except requests.RequestException as e:
        logger.warning(f"Ошибка запроса к API для фильма '{movie_title}': {e}")

    return default_data


def get_cached_movie_data(title_en):
    """Получает данные о фильме с кэшированием."""
    cache_key = f"movie_api_{title_en.replace(' ', '_').lower()}"
    data = cache.get(cache_key)

    if not data:
        try:
            data = get_movie_data_from_api(title_en)
        except Exception as e:
            logger.error(f"Ошибка при запросе к API для фильма {title_en}: {e}", exc_info=True)
            data = {'imdb_rating': 'N/A', 'director': 'Не указан', 'year': 'Не указан'}
        cache.set(cache_key, data, 86400)
        logger.debug(f"Данные для '{title_en}' сохранены в кэш")

    return data


def dashboard_view(request):
    """Главная страница с общей статистикой и календарём."""
    logger.debug("Загрузка dashboard")
    reviews = Review.objects.all()
    total_reviews = reviews.count()

    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    avg_rating = round(avg_rating, 2)

    ratings_list = sorted(list(reviews.values_list('rating', flat=True)))

    if total_reviews > 0:
        mid = total_reviews // 2
        if total_reviews % 2 == 0:
            median_rating = (ratings_list[mid - 1] + ratings_list[mid]) / 2
        else:
            median_rating = ratings_list[mid]
    else:
        median_rating = 0

    if total_reviews > 0:
        mode_data = reviews.values('rating').annotate(count=Count('rating')).order_by('-count').first()
        mode_rating = mode_data['rating'] if mode_data else 0
    else:
        mode_rating = 0

    popular_genre_data = Movie.objects.values('genres__name').annotate(
        movie_count=Count('id')
    ).order_by('-movie_count').first()
    top_genre = popular_genre_data['genres__name'] if popular_genre_data and popular_genre_data[
        'genres__name'] else "Нет данных"

    total_sales_sim = Showtime.objects.aggregate(total_price=Sum('ticket_price'))['total_price'] or 0
    movies_alphabetical = Movie.objects.order_by('title_ru')

    rating_counts = [reviews.filter(rating=i).count() for i in range(1, 6)]

    utc_now = datetime.now(zoneinfo.ZoneInfo("UTC"))
    user_tz_name = "Europe/Minsk"
    user_now = datetime.now(zoneinfo.ZoneInfo(user_tz_name))

    current_date_formatted = user_now.strftime("%d/%m/%Y")
    html_cal = calendar.HTMLCalendar(calendar.MONDAY).formatmonth(user_now.year, user_now.month)

    context = {
        'avg_rating': avg_rating,
        'median_rating': median_rating,
        'mode_rating': mode_rating,
        'total_reviews': total_reviews,
        'total_sales_sim': total_sales_sim,
        'top_genre': top_genre,
        'movies_alphabetical': movies_alphabetical,
        'rating_counts': rating_counts,
        'current_date_formatted': current_date_formatted,
        'utc_time': utc_now.strftime("%d/%m/%Y %H:%M:%S UTC"),
        'user_time': user_now.strftime("%d/%m/%Y %H:%M:%S") + f" ({user_tz_name})",
        'html_calendar': html_cal,
    }
    return render(request, 'cinema/dashboard.html', context)


def register_view(request):
    """Регистрация нового пользователя."""
    logger.info(f"Попытка регистрации с IP: {request.META.get('REMOTE_ADDR', 'unknown')}")

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        age = request.POST.get('age')
        photo = request.FILES.get('photo')

        if form.is_valid():
            if not age or int(age) < 18:
                logger.warning(f"Попытка регистрации несовершеннолетнего (возраст: {age})")
                messages.error(request, "Регистрация доступна только лицам старше 18 лет.")
                return render(request, 'cinema/register.html', {'form': form})

            user = form.save(commit=False)
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if email:
                user.email = email
            user.save()

            user.profile.age = int(age)
            if photo:
                user.profile.photo = photo
            if phone:
                user.profile.phone = phone
            user.profile.save()

            login(request, user)
            logger.info(f"Новый пользователь зарегистрирован: {user.username} (email: {email})")
            messages.success(request, "Регистрация прошла успешно!")
            return redirect('profile')
        else:
            logger.warning(f"Ошибка валидации формы регистрации: {form.errors}")
    else:
        form = UserCreationForm()
    return render(request, 'cinema/register.html', {'form': form})


def login_view(request):
    """Вход пользователя в систему."""
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"Пользователь вошел: {user.username}")
            next_url = request.GET.get('next', 'profile')
            return redirect(next_url)
        else:
            logger.warning(f"Неудачная попытка входа: {request.POST.get('username', 'unknown')}")
    else:
        form = AuthenticationForm()
    return render(request, 'cinema/login.html', {'form': form})


def logout_view(request):
    """Выход пользователя из системы."""
    if request.user.is_authenticated:
        logger.info(f"Пользователь вышел: {request.user.username}")
    logout(request)
    return redirect('index')


def index_view(request):
    """Главная страница сайта."""
    latest_news = NewsArticle.objects.order_by('-created_at_local').first()
    return render(request, 'cinema/index.html', {'latest_news': latest_news})


def about_view(request):
    """Страница с информацией о компании."""
    company_info = AboutCompany.objects.first()
    return render(request, 'cinema/about.html', {'company_info': company_info})


def movies_list_view(request):
    """Каталог фильмов с фильтрацией, поиском и сортировкой."""
    search_query = request.GET.get('search', '').strip()
    logger.debug(f"Загрузка каталога фильмов. Поиск: '{search_query}'")

    movies_queryset = Movie.objects.all()

    genre_id = request.GET.get('genre', '')
    country_id = request.GET.get('country', '')
    sort_by = request.GET.get('ordering', 'title_ru')

    if search_query:
        movies_queryset = movies_queryset.filter(
            Q(title_ru__icontains=search_query) |
            Q(title_en__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if genre_id:
        movies_queryset = movies_queryset.filter(genres__id=genre_id)

    if country_id:
        movies_queryset = movies_queryset.filter(countries__id=country_id)

    allowed_sort_fields = ['title_ru', '-title_ru', '-rating', 'duration']
    if sort_by in allowed_sort_fields:
        movies_queryset = movies_queryset.order_by(sort_by)
    else:
        movies_queryset = movies_queryset.order_by('title_ru')

    movies_list = list(movies_queryset.distinct())

    final_movies = []
    for movie in movies_list:
        api_data = get_cached_movie_data(movie.title_en)
        movie.imdb_rating = api_data.get('imdb_rating', 'N/A')
        movie.director = api_data.get('director', 'Не указан')
        movie.release_year = api_data.get('year', 'Не указан')

        if search_query and search_query.lower() in movie.director.lower():
            if movie not in final_movies:
                final_movies.append(movie)
        else:
            if not search_query or (search_query.lower() in movie.title_ru.lower() or
                                    search_query.lower() in movie.title_en.lower() or
                                    search_query.lower() in movie.description.lower()):
                final_movies.append(movie)

    if sort_by == '-imdb_rating':
        final_movies.sort(key=lambda m: float(m.imdb_rating) if m.imdb_rating != 'N/A' else 0.0, reverse=True)
    elif sort_by == '-release_year':
        final_movies.sort(key=lambda m: int(m.release_year) if m.release_year.isdigit() else 0, reverse=True)

    all_genres = Genre.objects.all().order_by('name')
    all_countries = Country.objects.all().order_by('name')

    active_promos = PromoCode.objects.filter(is_active=True)
    archived_promos = PromoCode.objects.filter(is_active=False)

    context = {
        'movies': final_movies,
        'all_genres': all_genres,
        'all_countries': all_countries,
        'active_promos': active_promos,
        'archived_promos': archived_promos,
        'search_query': search_query,
        'sort_by': sort_by
    }

    return render(request, 'cinema/movies_list.html', context)


def movie_detail_view(request, movie_id):
    """Детальная страница фильма с сеансами и статистикой для сотрудников."""
    movie = get_object_or_404(Movie, id=movie_id)
    logger.debug(f"Просмотр фильма: {movie.title_ru} (ID: {movie_id})")

    showtimes = movie.showtimes.all()
    is_employee = request.user.is_staff or request.user.is_superuser or hasattr(request.user, 'employee_contact')

    total_tickets_sold = Ticket.objects.filter(showtime__movie=movie).count()
    total_revenue = Ticket.objects.filter(showtime__movie=movie).aggregate(
        total=Sum('showtime__ticket_price')
    )['total'] or 0

    showtimes_with_stats = []
    for showtime in showtimes:
        tickets = Ticket.objects.filter(showtime=showtime)
        tickets_sold = tickets.count()
        revenue = tickets_sold * showtime.ticket_price
        occupancy = (tickets_sold / showtime.hall.capacity * 100) if showtime.hall.capacity > 0 else 0

        showtimes_with_stats.append({
            'showtime': showtime,
            'tickets_sold': tickets_sold,
            'revenue': revenue,
            'occupancy': occupancy,
            'tickets_list': tickets.select_related('customer') if is_employee else [],
        })

    context = {
        'movie': movie,
        'showtimes': showtimes,
        'showtimes_with_stats': showtimes_with_stats,
        'is_employee': is_employee,
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': total_revenue,
    }
    return render(request, 'cinema/movie_detail.html', context)


def contacts_view(request):
    """Страница с контактами сотрудников."""
    employees = ContactEmployee.objects.filter(is_visible=True)
    context = {
        'employees': employees,
        'address': 'г. Минск, пр-т Победителей, д. 9',
        'phone': '+375 (29) 111-22-33'
    }
    return render(request, 'cinema/contacts.html', context)


def reviews_view(request):
    """Страница с отзывами пользователей."""
    user_review = None
    can_review = False

    if request.user.is_authenticated:
        is_simple_user = not request.user.is_staff and not request.user.is_superuser and not hasattr(
            request.user, 'employee_contact'
        )
        if is_simple_user:
            can_review = True
            user_review = Review.objects.filter(user=request.user).first()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            logger.warning("Попытка оставить отзыв без авторизации")
            messages.error(request, "Необходимо войти в систему для отправки отзыва.")
            return redirect('login')

        if request.user.is_staff or request.user.is_superuser or hasattr(request.user, 'employee_contact'):
            logger.warning(f"Сотрудник {request.user.username} попытался оставить отзыв")
            messages.error(request, "Сотрудники и администраторы не могут оставлять отзывы.")
            return redirect('reviews')

        form = ReviewForm(request.POST, instance=user_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.save()
            logger.info(f"Пользователь {request.user.username} оставил отзыв с оценкой {review.rating}")
            messages.success(request, "Ваш отзыв успешно сохранен!")
            return redirect('reviews')
    else:
        form = ReviewForm(instance=user_review) if can_review else None

    all_reviews = Review.objects.all().order_by('-created_at_utc')
    if user_review:
        all_reviews = all_reviews.exclude(id=user_review.id)

    return render(request, 'cinema/reviews.html', {
        'reviews': all_reviews,
        'user_review': user_review,
        'form': form,
        'can_review': can_review,
    })


@login_required
def profile_view(request):
    """Личный кабинет пользователя с историей билетов или панелью администратора."""
    logger.debug(f"Загрузка профиля пользователя: {request.user.username}")

    user_profile = getattr(request.user, 'profile', None)
    context = {
        'profile': user_profile,
        'is_employee': request.user.is_staff or request.user.is_superuser,
    }

    if context['is_employee']:
        logger.debug(f"Загрузка расширенной статистики для сотрудника: {request.user.username}")

        clients_alphabetical = User.objects.filter(is_staff=False, is_superuser=False).order_by('username')

        movies_alphabetical = Movie.objects.annotate(
            total_sales=Sum('showtimes__tickets__showtime__ticket_price')
        ).order_by('title_ru')

        total_sales_sum = Ticket.objects.aggregate(
            total=Sum('showtime__ticket_price')
        )['total'] or 0

        active_ages = list(UserProfile.objects.filter(
            user__is_staff=False, user__is_superuser=False
        ).values_list('age', flat=True))
        active_ages = sorted([age for age in active_ages if age is not None])

        total_clients = len(active_ages)
        avg_age = round(sum(active_ages) / total_clients, 1) if total_clients > 0 else 0

        if total_clients > 0:
            mid = total_clients // 2
            median_age = (active_ages[mid - 1] + active_ages[mid]) / 2 if total_clients % 2 == 0 else active_ages[mid]
        else:
            median_age = 0

        top_movie_by_tickets = Movie.objects.annotate(
            tickets_count=Count('showtimes__tickets')
        ).order_by('-tickets_count').first()

        top_movie_by_revenue = Movie.objects.annotate(
            revenue=Sum('showtimes__tickets__showtime__ticket_price')
        ).order_by('-revenue').first()

        ticket_prices = sorted([float(p) for p in Ticket.objects.values_list(
            'showtime__ticket_price', flat=True
        ) if p is not None])
        total_tickets = len(ticket_prices)

        avg_ticket_cost = round(sum(ticket_prices) / total_tickets, 2) if total_tickets > 0 else 0

        if total_tickets > 0:
            mid_t = total_tickets // 2
            median_ticket_cost = (ticket_prices[mid_t - 1] + ticket_prices[mid_t]) / 2 if total_tickets % 2 == 0 else \
                ticket_prices[mid_t]
        else:
            median_ticket_cost = 0

        if total_tickets > 0:
            mode_data = Ticket.objects.values('showtime__ticket_price').annotate(
                count=Count('id')
            ).order_by('-count').first()
            mode_ticket_cost = mode_data['showtime__ticket_price'] if mode_data else 0
        else:
            mode_ticket_cost = 0

        chart_sales = ""
        chart_reviews = ""

        if total_tickets > 0:
            today = timezone.now().date()
            month_ago = today - timedelta(days=30)

            daily_revenue = Ticket.objects.filter(
                created_at_utc__date__gte=month_ago,
                created_at_utc__date__lte=today
            ).annotate(
                day=TruncDate('created_at_utc')
            ).values('day').annotate(
                daily_total=Sum('showtime__ticket_price')
            ).order_by('day')

            dates = []
            revenues = []
            for entry in daily_revenue:
                dates.append(entry['day'].strftime('%d.%m'))
                revenues.append(float(entry['daily_total']))

            if dates:
                plt.figure(figsize=(12, 6))
                plt.plot(dates, revenues, color='#1890ff', linewidth=2.5, marker='o',
                         markersize=8, markerfacecolor='#ff6b6b', markeredgecolor='#ff6b6b',
                         markeredgewidth=1.5, linestyle='-', alpha=0.9)
                plt.fill_between(range(len(dates)), revenues, alpha=0.2, color='#1890ff')

                for i, (date, rev) in enumerate(zip(dates, revenues)):
                    plt.annotate(f'{rev:.0f}', (date, rev), textcoords="offset points",
                                 xytext=(0, 10), ha='center', fontsize=9, color='#333')

                plt.title('Динамика прибыли за последний месяц (BYN)', fontsize=14, fontweight='bold', pad=15)
                plt.xlabel('Дата')
                plt.ylabel('Сумма (BYN)')
                plt.xticks(rotation=45, ha='right')
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()

                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                buffer.seek(0)
                chart_sales = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close()

            reviews = Review.objects.all()
            rating_counts = [reviews.filter(rating=i).count() for i in range(1, 6)]

            plt.figure(figsize=(6, 4))
            plt.bar(['1 ★', '2 ★', '3 ★', '4 ★', '5 ★'], rating_counts, color='#52c41a', alpha=0.8)
            plt.title('Распределение оценок пользователей', fontsize=12, fontweight='bold', pad=15)
            plt.ylabel('Количество отзывов')
            plt.grid(axis='y', linestyle='--', alpha=0.5)
            plt.tight_layout()

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150)
            buffer.seek(0)
            chart_reviews = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()

        context.update({
            'clients_alphabetical': clients_alphabetical,
            'movies_alphabetical': movies_alphabetical,
            'total_sales_sum': total_sales_sum,
            'avg_age': avg_age,
            'median_age': median_age,
            'top_movie_by_tickets': top_movie_by_tickets,
            'top_movie_by_revenue': top_movie_by_revenue,
            'avg_ticket_cost': avg_ticket_cost,
            'median_ticket_cost': median_ticket_cost,
            'mode_ticket_cost': mode_ticket_cost,
            'chart_sales': chart_sales,
            'chart_reviews': chart_reviews,
        })
    else:
        context['tickets'] = Ticket.objects.filter(
            customer=request.user
        ).select_related('showtime__movie', 'showtime__hall')

    return render(request, 'cinema/profile.html', context)


@login_required
def select_seats_view(request, showtime_id):
    """Страница интерактивного выбора мест для сеанса."""
    showtime = get_object_or_404(Showtime, id=showtime_id)
    hall = showtime.hall
    logger.debug(f"Пользователь {request.user.username} выбирает места: сеанс #{showtime_id}")

    booked_tickets = Ticket.objects.filter(showtime=showtime)
    booked_seats = {(t.row, t.seat): True for t in booked_tickets}

    hall_structure = []
    for r in range(1, hall.rows_count + 1):
        row_seats = []
        for s in range(1, hall.seats_per_row + 1):
            is_booked = (r, s) in booked_seats
            row_seats.append({'number': s, 'is_booked': is_booked})
        hall_structure.append({'row_number': r, 'seats': row_seats})

    context = {
        'showtime': showtime,
        'movie': showtime.movie,
        'hall': hall,
        'hall_structure': hall_structure,
    }
    return render(request, 'cinema/booking.html', context)


@login_required
def book_ticket_action(request, showtime_id):
    """Обработчик покупки выбранного места."""
    logger.info(f"Попытка бронирования: showtime_id={showtime_id}, user={request.user.username}")

    if request.method == 'POST':
        showtime = get_object_or_404(Showtime, id=showtime_id)

        try:
            row = int(request.POST.get('row'))
            seat = int(request.POST.get('seat'))
        except (ValueError, TypeError):
            logger.warning(f"Некорректные параметры бронирования: row={request.POST.get('row')}, seat={request.POST.get('seat')}")
            messages.error(request, "Некорректно выбраны ряд или место.")
            return redirect('select_seats', showtime_id=showtime.id)

        if Ticket.objects.filter(showtime=showtime, row=row, seat=seat).exists():
            logger.warning(f"Попытка забронировать занятое место: ряд {row}, место {seat}")
            messages.error(request, f"Ряд {row}, Место {seat} уже заняты!")
            return redirect('select_seats', showtime_id=showtime.id)

        try:
            Ticket.objects.create(showtime=showtime, customer=request.user, row=row, seat=seat)
            logger.info(f"Билет забронирован: user={request.user.username}, film={showtime.movie.title_ru}, row={row}, seat={seat}, price={showtime.ticket_price}")
            messages.success(
                request,
                f"Вы успешно забронировали билет на фильм «{showtime.movie.title_ru}»! Ряд {row}, Место {seat}."
            )
        except Exception as e:
            logger.error(f"Ошибка бронирования: {e}", exc_info=True)
            messages.error(request, "Произошла ошибка при бронировании. Попробуйте еще раз.")

    return redirect('profile')


@login_required
def delete_ticket_view(request, ticket_id):
    """Отмена бронирования билета."""
    ticket = get_object_or_404(Ticket, id=ticket_id, customer=request.user)
    movie_title = ticket.showtime.movie.title_ru
    ticket.delete()
    logger.info(f"Билет #{ticket_id} отменен пользователем {request.user.username}: фильм '{movie_title}'")
    messages.success(request, f"Билет на фильм «{movie_title}» успешно отменен.")
    return redirect('profile')


@login_required
def edit_ticket_seats_view(request, ticket_id):
    """Изменение места для уже оформленного билета."""
    ticket = get_object_or_404(Ticket, id=ticket_id, customer=request.user)
    showtime = ticket.showtime
    hall = showtime.hall
    logger.debug(f"Пользователь {request.user.username} редактирует билет #{ticket_id}")

    booked_tickets = Ticket.objects.filter(showtime=showtime).exclude(id=ticket.id)
    booked_seats = {(t.row, t.seat): True for t in booked_tickets}

    if request.method == 'POST':
        try:
            new_row = int(request.POST.get('row'))
            new_seat = int(request.POST.get('seat'))
        except (ValueError, TypeError):
            messages.error(request, "Некорректный выбор новых мест.")
            return redirect('edit_ticket', ticket_id=ticket.id)

        if (new_row, new_seat) in booked_seats:
            messages.error(request, f"Ряд {new_row}, Место {new_seat} уже заняты!")
        else:
            old_row, old_seat = ticket.row, ticket.seat
            ticket.row = new_row
            ticket.seat = new_seat
            ticket.save()
            logger.info(f"Билет #{ticket_id}: место изменено с ({old_row},{old_seat}) на ({new_row},{new_seat})")
            messages.success(request, f"Место успешно изменено на Ряд {new_row}, Место {new_seat}!")
            return redirect('profile')

    hall_structure = []
    for r in range(1, hall.rows_count + 1):
        row_seats = []
        for s in range(1, hall.seats_per_row + 1):
            is_booked = (r, s) in booked_seats
            is_current = (r == ticket.row and s == ticket.seat)
            row_seats.append({'number': s, 'is_booked': is_booked, 'is_current': is_current})
        hall_structure.append({'row_number': r, 'seats': row_seats})

    return render(request, 'cinema/edit_ticket.html', {
        'ticket': ticket,
        'showtime': showtime,
        'movie': showtime.movie,
        'hall_structure': hall_structure
    })


@login_required
@user_passes_test(is_staff_or_admin)
def news_create_view(request):
    """Создание новости."""
    if request.method == 'POST':
        title = request.POST.get('title')
        short_description = request.POST.get('short_description')
        content = request.POST.get('content')
        image = request.FILES.get('image')
        NewsArticle.objects.create(title=title, short_description=short_description, content=content, image=image)
        logger.info(f"Сотрудник {request.user.username} создал новость: '{title}'")
        return redirect('index')
    return render(request, 'cinema/news_form.html', {'action': 'Создать'})


@login_required
@user_passes_test(is_staff_or_admin)
def news_update_view(request, pk):
    """Редактирование новости."""
    article = get_object_or_404(NewsArticle, pk=pk)
    if request.method == 'POST':
        article.title = request.POST.get('title')
        article.short_description = request.POST.get('short_description')
        article.content = request.POST.get('content')
        if request.FILES.get('image'):
            article.image = request.FILES.get('image')
        article.save()
        logger.info(f"Сотрудник {request.user.username} обновил новость: '{article.title}'")
        return redirect('index')
    return render(request, 'cinema/news_form.html', {'article': article, 'action': 'Сохранить изменения'})


@login_required
@user_passes_test(is_staff_or_admin)
def news_delete_view(request, pk):
    """Удаление новости."""
    article = get_object_or_404(NewsArticle, pk=pk)
    if request.method == 'POST':
        title = article.title
        article.delete()
        logger.warning(f"Сотрудник {request.user.username} удалил новость: '{title}'")
        return redirect('index')
    return render(request, 'cinema/news_confirm_delete.html', {'article': article})


@login_required
@user_passes_test(is_staff_or_admin)
def showtime_create_view(request, movie_id):
    """Создание нового сеанса для фильма."""
    movie = get_object_or_404(Movie, id=movie_id)
    halls = CinemaHall.objects.all()

    if request.method == 'POST':
        hall_id = request.POST.get('hall')
        start_time = request.POST.get('start_time')
        ticket_price = request.POST.get('ticket_price')

        try:
            hall = CinemaHall.objects.get(id=hall_id)
            Showtime.objects.create(movie=movie, hall=hall, start_time=start_time, ticket_price=ticket_price)
            logger.info(f"Сотрудник {request.user.username} создал сеанс: {movie.title_ru} | {hall.name} | {start_time}")
            messages.success(request, f"Сеанс для фильма «{movie.title_ru}» успешно создан!")
        except Exception as e:
            logger.error(f"Ошибка создания сеанса: {e}", exc_info=True)
            messages.error(request, f"Ошибка при создании сеанса: {e}")

    return redirect('movie_detail', movie_id=movie.id)


@login_required
@user_passes_test(is_staff_or_admin)
def showtime_update_view(request, showtime_id):
    """Обновление существующего сеанса."""
    showtime = get_object_or_404(Showtime, id=showtime_id)
    halls = CinemaHall.objects.all()

    if request.method == 'POST':
        showtime.hall_id = request.POST.get('hall')
        showtime.start_time = request.POST.get('start_time')
        showtime.ticket_price = request.POST.get('ticket_price')
        showtime.save()
        logger.info(f"Сотрудник {request.user.username} обновил сеанс #{showtime_id}")
        messages.success(request, "Сеанс успешно обновлен!")
        return redirect('movie_detail', movie_id=showtime.movie.id)

    return render(request, 'cinema/showtime_form.html', {
        'showtime': showtime,
        'halls': halls,
        'movie': showtime.movie,
    })


@login_required
@user_passes_test(is_staff_or_admin)
def showtime_delete_view(request, showtime_id):
    """Удаление сеанса со всеми билетами."""
    showtime = get_object_or_404(Showtime, id=showtime_id)
    movie_id = showtime.movie.id
    movie_title = showtime.movie.title_ru

    if request.method == 'POST':
        tickets_count = Ticket.objects.filter(showtime=showtime).count()
        Ticket.objects.filter(showtime=showtime).delete()
        showtime.delete()
        logger.warning(f"Сотрудник {request.user.username} удалил сеанс: '{movie_title}' (удалено билетов: {tickets_count})")
        messages.success(request, f"Сеанс фильма «{movie_title}» успешно удален вместе со всеми билетами!")
        return redirect('movie_detail', movie_id=movie_id)

    tickets_count = Ticket.objects.filter(showtime=showtime).count()
    return render(request, 'cinema/showtime_confirm_delete.html', {
        'showtime': showtime,
        'tickets_count': tickets_count,
    })


def news_list_view(request):
    """Страница со списком всех новостей."""
    news = NewsArticle.objects.all().order_by('-created_at_utc')
    return render(request, 'cinema/news_list.html', {'news': news})


def faq_list_view(request):
    """Страница с часто задаваемыми вопросами."""
    faqs = FAQItem.objects.all()
    return render(request, 'cinema/faq_list.html', {'faqs': faqs})


def vacancies_list_view(request):
    """Страница с вакансиями."""
    vacancies = JobVacancy.objects.filter(is_active=True)
    return render(request, 'cinema/vacancies_list.html', {'vacancies': vacancies})


def privacy_policy_view(request):
    """Страница политики конфиденциальности."""
    policy = PrivacyPolicy.objects.first()
    return render(request, 'cinema/privacy_policy.html', {'policy': policy})


def promocodes_list_view(request):
    """Страница с промокодами."""
    active_promos = PromoCode.objects.filter(is_active=True)
    archived_promos = PromoCode.objects.filter(is_active=False)
    return render(request, 'cinema/promocodes_list.html', {
        'active_promos': active_promos,
        'archived_promos': archived_promos,
    })