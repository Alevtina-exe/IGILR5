import logging
import zoneinfo

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger('cinema.models')


def validate_age(value):
    if value < 18:
        raise ValidationError("Возраст должен быть 18 или более лет!")


class TimeStampedModel(models.Model):
    """Абстрактная модель с автоматическим сохранением дат в UTC и локальной таймзоне."""

    created_at_utc = models.DateTimeField(null=True, blank=True, verbose_name="Дата создания (UTC)")
    created_at_local = models.DateTimeField(null=True, blank=True, verbose_name="Дата создания (Минск)")
    updated_at_utc = models.DateTimeField(null=True, blank=True, verbose_name="Дата изменения (UTC)")
    updated_at_local = models.DateTimeField(null=True, blank=True, verbose_name="Дата изменения (Минск)")

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        now_utc = timezone.now()
        minsk_tz = zoneinfo.ZoneInfo("Europe/Minsk")
        now_minsk = now_utc.astimezone(minsk_tz)

        if not self.pk:
            if not self.created_at_utc:
                self.created_at_utc = now_utc
            if not self.created_at_local:
                self.created_at_local = now_minsk
            logger.debug(f"Создание объекта {self.__class__.__name__}")

        if self.pk:
            self.updated_at_utc = now_utc
            self.updated_at_local = now_minsk
            logger.debug(f"Обновление объекта {self.__class__.__name__} id={self.pk}")

        super().save(*args, **kwargs)


class UserProfile(TimeStampedModel):
    """Расширенный профиль пользователя с возрастом, фото и телефоном."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age = models.IntegerField(default=18, validators=[validate_age], verbose_name="Возраст")
    photo = models.ImageField(upload_to='users_photos/', blank=True, null=True, verbose_name="Фото профиля")

    phone_regex = RegexValidator(
        regex=r'^\+375 \(\d{2}\) \d{3}-\d{2}-\d{2}$',
        message="Номер телефона должен быть в формате: +375 (XX) XXX-XX-XX"
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=19,
        blank=True,
        null=True,
        verbose_name="Номер телефона"
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создан профиль пользователя: {self.user.username}")
        else:
            logger.debug(f"Обновлен профиль пользователя: {self.user.username}")

    def __str__(self):
        return f"Профиль: {self.user.username} (Возраст: {self.age})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        logger.info(f"Автоматически создан профиль для нового пользователя: {instance.username}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class AboutCompany(TimeStampedModel):
    """Информация о компании: название, описание, логотип и реквизиты."""

    title = models.CharField(max_length=200, verbose_name="Название компании")
    description = models.TextField(verbose_name="Описание/История компании")
    logo = models.ImageField(upload_to='company/', blank=True, null=True, verbose_name="Логотип")
    requisites = models.TextField(verbose_name="Реквизиты")

    class Meta:
        verbose_name = "О компании"
        verbose_name_plural = "О компании"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создана информация о компании: {self.title}")

    def __str__(self):
        return self.title


class NewsArticle(TimeStampedModel):
    """Новостные статьи с заголовком, описанием, содержимым и изображением."""

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    short_description = models.TextField(verbose_name="Краткое описание")
    content = models.TextField(verbose_name="Полный текст статьи")
    image = models.ImageField(upload_to='news_photos/', blank=True, null=True, verbose_name="Фото новости")

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        ordering = ['-created_at_utc']

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создана новость: {self.title}")
        else:
            logger.info(f"Обновлена новость: {self.title}")

    def delete(self, *args, **kwargs):
        logger.warning(f"Удалена новость: {self.title}")
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.title


class FAQItem(TimeStampedModel):
    """Часто задаваемые вопросы и ответы."""

    question = models.CharField(max_length=255, verbose_name="Вопрос / Термин")
    answer = models.TextField(verbose_name="Ответ / Определение")

    class Meta:
        verbose_name = "Вопрос-ответ (FAQ)"
        verbose_name_plural = "Вопросы-ответы (FAQ)"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создан FAQ: {self.question}")

    def __str__(self):
        return self.question


class ContactEmployee(TimeStampedModel):
    """Контактная информация сотрудников, привязанная к пользователям."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee_contact',
        verbose_name="Пользователь (сотрудник)"
    )
    position = models.CharField(max_length=100, verbose_name="Должность / Выполняемая работа")
    is_visible = models.BooleanField(default=True, verbose_name="Отображать на сайте")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Рабочий телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="Рабочий email")
    photo = models.ImageField(upload_to="employees/", blank=True, null=True, verbose_name="Фото сотрудника")
    description = models.TextField(blank=True, null=True, verbose_name="Дополнительная информация")

    class Meta:
        verbose_name = "Контакт сотрудника"
        verbose_name_plural = "Контакты сотрудников"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создан контакт сотрудника: {self.get_full_name()} - {self.position}")

    def delete(self, *args, **kwargs):
        logger.warning(f"Удален контакт сотрудника: {self.get_full_name()}")
        super().delete(*args, **kwargs)

    def get_full_name(self):
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username

    def get_photo(self):
        if self.photo:
            return self.photo
        if hasattr(self.user, 'profile') and self.user.profile.photo:
            return self.user.profile.photo
        return None

    def get_phone(self):
        if self.phone:
            return self.phone
        if hasattr(self.user, 'profile') and self.user.profile.phone:
            return self.user.profile.phone
        return None

    def get_email(self):
        if self.email:
            return self.email
        return self.user.email

    def __str__(self):
        return f"{self.get_full_name()} - {self.position}"


class JobVacancy(TimeStampedModel):
    """Вакансии компании с описанием и зарплатой."""

    title = models.CharField(max_length=100, verbose_name="Название вакансии")
    description = models.TextField(verbose_name="Описание обязанностей и требований")
    salary = models.CharField(max_length=50, blank=True, verbose_name="Заработная плата")
    is_active = models.BooleanField(default=True, verbose_name="Вакансия открыта")

    class Meta:
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создана вакансия: {self.title}")

    def delete(self, *args, **kwargs):
        logger.warning(f"Удалена вакансия: {self.title}")
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.title


class PrivacyPolicy(TimeStampedModel):
    """Политика конфиденциальности."""

    title = models.CharField(max_length=100, default="Политика конфиденциальности")
    content = models.TextField(blank=True, verbose_name="Текст политики безопасности")

    class Meta:
        verbose_name = "Политика конфиденциальности"
        verbose_name_plural = "Политика конфиденциальности"

    def __str__(self):
        return self.title


class Country(TimeStampedModel):
    """Страны производства фильмов."""

    name = models.CharField(max_length=100, unique=True, verbose_name="Название страны")

    class Meta:
        verbose_name = "Страна"
        verbose_name_plural = "Страны"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.debug(f"Создана страна: {self.name}")

    def __str__(self):
        return self.name


class Genre(TimeStampedModel):
    """Жанры фильмов."""

    name = models.CharField(max_length=100, unique=True, verbose_name="Название жанра")

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.debug(f"Создан жанр: {self.name}")

    def __str__(self):
        return self.name


class Movie(TimeStampedModel):
    """Фильмы с метаданными, жанрами и странами."""

    title_ru = models.CharField(max_length=150, verbose_name="Название (РУС)")
    title_en = models.CharField(max_length=150, verbose_name="Название (ENG)")
    description = models.TextField(verbose_name="Описание фильма")
    duration = models.PositiveIntegerField(verbose_name="Длительность (в минутах)")
    budget = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Бюджет ($)")
    rating = models.FloatField(verbose_name="Рейтинг (0.0 - 10.0)")
    poster = models.ImageField(upload_to='posters/', verbose_name="Постер фильма")
    genres = models.ManyToManyField(Genre, related_name='movies', verbose_name="Жанры")
    countries = models.ManyToManyField(Country, verbose_name="Страны производители")

    class Meta:
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создан фильм: {self.title_ru} ({self.title_en})")
        else:
            logger.info(f"Обновлен фильм: {self.title_ru}")

    def delete(self, *args, **kwargs):
        logger.warning(f"Удален фильм: {self.title_ru} ({self.title_en})")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.title_ru} ({self.title_en})"


class CinemaHall(TimeStampedModel):
    """Кинозалы с количеством рядов, мест и автоматическим расчетом вместимости."""

    name = models.CharField(max_length=100, verbose_name="Название/Номер зала")
    rows_count = models.PositiveIntegerField(default=10, verbose_name="Количество рядов")
    seats_per_row = models.PositiveIntegerField(default=10, verbose_name="Количество мест в ряду")
    capacity = models.PositiveIntegerField(verbose_name="Вместимость (мест)", editable=False)

    class Meta:
        verbose_name = "Кинозал"
        verbose_name_plural = "Кинозалы"

    def save(self, *args, **kwargs):
        self.capacity = self.rows_count * self.seats_per_row
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создан кинозал: {self.name} (вместимость: {self.capacity})")
        else:
            logger.debug(f"Обновлен кинозал: {self.name} (вместимость: {self.capacity})")

    def delete(self, *args, **kwargs):
        logger.warning(f"Удален кинозал: {self.name}")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Рядов: {self.rows_count}, Мест в ряду: {self.seats_per_row}, Всего: {self.capacity})"


class Showtime(TimeStampedModel):
    """Сеансы фильмов с привязкой к залу, временем и ценой билета."""

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='showtimes', verbose_name="Фильм")
    hall = models.ForeignKey(CinemaHall, on_delete=models.CASCADE, related_name='showtimes', verbose_name="Зал")
    start_time = models.DateTimeField(verbose_name="Время начала сеанса")
    ticket_price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Цена билета (BYN)")

    class Meta:
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеансы"
        ordering = ['start_time']

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создан сеанс: {self.movie.title_ru} | {self.start_time.strftime('%d/%m/%Y %H:%M')} | {self.ticket_price} BYN")

    def delete(self, *args, **kwargs):
        logger.warning(f"Удален сеанс: {self.movie.title_ru} | {self.start_time.strftime('%d/%m/%Y %H:%M')}")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.movie.title_ru} | {self.hall.name} | {self.start_time.strftime('%d/%m/%Y %H:%M')}"


class Ticket(TimeStampedModel):
    """Билеты на сеансы с указанием ряда и места."""

    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name='tickets', verbose_name="Сеанс")
    customer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets', verbose_name="Покупатель"
    )
    row = models.PositiveIntegerField(verbose_name="Ряд")
    seat = models.PositiveIntegerField(verbose_name="Место")

    class Meta:
        verbose_name = "Билет"
        verbose_name_plural = "Билеты"
        constraints = [
            models.UniqueConstraint(fields=['showtime', 'row', 'seat'], name='unique_showtime_row_seat')
        ]

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            customer_name = self.customer.username if self.customer else "неизвестный"
            logger.info(f"Продан билет: {customer_name} | {self.showtime.movie.title_ru} | Ряд {self.row}, Место {self.seat} | {self.showtime.ticket_price} BYN")

    def delete(self, *args, **kwargs):
        customer_name = self.customer.username if self.customer else "неизвестный"
        logger.warning(f"Возврат билета #{self.id}: {customer_name} | {self.showtime.movie.title_ru} | Ряд {self.row}, Место {self.seat}")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Билет #{self.id} (Ряд {self.row}, Место {self.seat}) на {self.showtime.movie.title_ru}"


class PromoCode(TimeStampedModel):
    """Промокоды и купоны со статусом активности."""

    code = models.CharField(max_length=50, unique=True, verbose_name="Промокод")
    description = models.CharField(max_length=255, verbose_name="Описание скидки/акции")
    is_active = models.BooleanField(default=True, verbose_name="Действующий (Активен)")

    class Meta:
        verbose_name = "Промокод и купон"
        verbose_name_plural = "Промокоды и купоны"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создан промокод: {self.code} (активен: {self.is_active})")
        else:
            logger.info(f"Обновлен промокод: {self.code} (активен: {self.is_active})")

    def delete(self, *args, **kwargs):
        logger.warning(f"Удален промокод: {self.code}")
        super().delete(*args, **kwargs)

    def __str__(self):
        status = "Активен" if self.is_active else "В архиве"
        return f"{self.code} ({status})"


class Review(TimeStampedModel):
    """Отзывы пользователей с оценкой от 1 до 5."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Оценка (1-5)"
    )
    text = models.TextField(verbose_name="Текст отзыва")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at_utc']

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"Создан отзыв: {self.user.username} | Оценка: {self.rating}")
        else:
            logger.info(f"Обновлен отзыв: {self.user.username} | Оценка: {self.rating}")

    def delete(self, *args, **kwargs):
        logger.warning(f"Удален отзыв #{self.id}: {self.user.username} | Оценка: {self.rating}")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Отзыв от {self.user.username} (Оценка: {self.rating})"