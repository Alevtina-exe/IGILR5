import logging
import zoneinfo

from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils import timezone

from .models import *

logger = logging.getLogger('cinema.admin')

MINSK_TZ = zoneinfo.ZoneInfo("Europe/Minsk")
UTC_TZ = zoneinfo.ZoneInfo("UTC")


def format_minsk(dt):
    if not dt:
        return "-"
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, UTC_TZ)
    return dt.astimezone(MINSK_TZ).strftime("%d/%m/%Y %H:%M:%S")


def format_utc(dt):
    if not dt:
        return "-"
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, UTC_TZ)
    return dt.astimezone(UTC_TZ).strftime("%d/%m/%Y %H:%M:%S UTC")


class TimeStampedAdminMixin:
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if hasattr(self.model, 'created_at_utc'):
            readonly_fields.extend([
                'display_created_utc_widget',
                'display_created_minsk_widget',
                'display_updated_utc_widget',
                'display_updated_minsk_widget'
            ])
        return readonly_fields

    def display_created_utc_widget(self, obj):
        if obj and obj.created_at_utc:
            return format_utc(obj.created_at_utc)
        return "-"

    def display_created_minsk_widget(self, obj):
        if obj and obj.created_at_local:
            return format_minsk(obj.created_at_local)
        return "-"

    def display_updated_utc_widget(self, obj):
        if obj and obj.updated_at_utc:
            return format_utc(obj.updated_at_utc)
        return "-"

    def display_updated_minsk_widget(self, obj):
        if obj and obj.updated_at_local:
            return format_minsk(obj.updated_at_local)
        return "-"

    def display_created(self, obj):
        if hasattr(obj, 'created_at_local') and obj.created_at_local:
            return format_minsk(obj.created_at_local)
        return "-"

    display_created_utc_widget.short_description = "Дата создания (UTC)"
    display_created_minsk_widget.short_description = "Дата создания (Минск)"
    display_updated_utc_widget.short_description = "Дата изменения (UTC)"
    display_updated_minsk_widget.short_description = "Дата изменения (Минск)"
    display_created.short_description = "Дата создания"
    display_created.admin_order_field = 'created_at_local'


class UserProfileAdminForm(forms.ModelForm):
    username = forms.CharField(label="Имя пользователя (Логин)", max_length=150)
    email = forms.EmailField(label="Электронная почта", required=False)
    first_name = forms.CharField(label="Имя", max_length=150, required=False)
    last_name = forms.CharField(label="Фамилия", max_length=150, required=False)
    is_active = forms.BooleanField(label="Активен", required=False, initial=True)
    is_staff = forms.BooleanField(label="Статус персонала (Сотрудник)", required=False)
    is_superuser = forms.BooleanField(label="Статус суперпользователя (Админ)", required=False)

    class Meta:
        model = UserProfile
        fields = ['photo', 'age', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'phone' in self.fields:
            self.fields['phone'].widget.attrs.update({
                'placeholder': '+375 (XX) XXX-XX-XX',
                'oninput': "let matrix = '+375 (__) ___-__-__', i = 0, def = matrix.replace(/\\D/g, ''), val = this.value.replace(/\\D/g, ''); if (def.length >= val.length) val = def; this.value = matrix.replace(/./g, function(a) { return /[_\\d]/.test(a) && i < val.length ? val.charAt(i++) : i >= val.length ? '' : a; });"
            })

        if self.instance and self.instance.pk:
            try:
                if hasattr(self.instance, 'user') and self.instance.user:
                    user = self.instance.user
                    self.fields['username'].initial = user.username
                    self.fields['email'].initial = user.email
                    self.fields['first_name'].initial = user.first_name
                    self.fields['last_name'].initial = user.last_name
                    self.fields['is_active'].initial = user.is_active
                    self.fields['is_staff'].initial = user.is_staff
                    self.fields['is_superuser'].initial = user.is_superuser
            except (User.DoesNotExist, AttributeError):
                pass

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if self.instance and self.instance.pk:
            if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
                logger.warning(f"Попытка использовать занятый логин: {username}")
                raise forms.ValidationError("Пользователь с таким логином уже существует.")
        else:
            if User.objects.filter(username=username).exists():
                logger.warning(f"Попытка создать пользователя с существующим логином: {username}")
                raise forms.ValidationError("Пользователь с таким логином уже существует.")
        return username


@admin.register(UserProfile)
class UserProfileAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('get_username', 'get_email', 'phone', 'age', 'display_created')
    search_fields = ('user__username', 'user__email', 'phone')
    list_filter = ('age',)
    fieldsets = (
        ('Данные учетной записи', {'fields': ('username', 'email', 'first_name', 'last_name')}),
        ('Личные данные', {'fields': ('photo', 'age', 'phone')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('get_date_joined', 'get_last_login')

    def save_model(self, request, obj, form, change):
        username = form.cleaned_data.get('username')
        email = form.cleaned_data.get('email', '')
        first_name = form.cleaned_data.get('first_name', '')
        last_name = form.cleaned_data.get('last_name', '')
        is_active = form.cleaned_data.get('is_active', True)
        is_staff = form.cleaned_data.get('is_staff', False)
        is_superuser = form.cleaned_data.get('is_superuser', False)

        if change:
            user = obj.user
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = is_active
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()
            logger.info(f"Администратор {request.user.username}: профиль обновлен: {username}")
        else:
            post_save.disconnect(create_user_profile, sender=User)
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=is_active,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )
                obj.user = user
                logger.info(f"Администратор {request.user.username}: создан новый профиль: {username}")
            except Exception as e:
                logger.error(f"Ошибка создания пользователя {username}: {e}", exc_info=True)
                raise
            finally:
                post_save.connect(create_user_profile, sender=User)

        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        username = obj.user.username if hasattr(obj, 'user') else 'unknown'
        logger.warning(f"Администратор {request.user.username}: удаление профиля: {username}")
        obj.user.delete()

    def get_username(self, obj):
        try:
            return obj.user.username
        except User.DoesNotExist:
            return "—"

    def get_email(self, obj):
        try:
            return obj.user.email
        except User.DoesNotExist:
            return "—"

    def get_date_joined(self, obj):
        try:
            return format_minsk(obj.user.date_joined)
        except User.DoesNotExist:
            return "—"

    def get_last_login(self, obj):
        try:
            return format_minsk(obj.user.last_login)
        except User.DoesNotExist:
            return "—"

    get_username.short_description = 'Логин'
    get_email.short_description = 'Email'
    get_date_joined.short_description = "Дата регистрации"
    get_last_login.short_description = "Последний вход"

    class Media:
        js = ('https://cdnjs.cloudflare.com/ajax/libs/imask/6.4.3/imask.min.js',)


@admin.register(NewsArticle)
class NewsArticleAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('title', 'display_created')
    search_fields = ('title',)
    fieldsets = (
        ('Основная информация', {'fields': ('title', 'short_description', 'content', 'image')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        action = "обновлена" if change else "создана"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: новость '{obj.title}' {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление новости '{obj.title}'")
        super().delete_model(request, obj)


@admin.register(Review)
class ReviewAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'rating', 'display_created')
    search_fields = ('user__username', 'text')
    list_filter = ('rating',)
    fieldsets = (
        ('Информация об отзыве', {'fields': ('user', 'rating', 'text')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        action = "обновлен" if change else "создан"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: отзыв пользователя {obj.user.username} {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление отзыва #{obj.id}")
        super().delete_model(request, obj)


@admin.register(Ticket)
class TicketAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'showtime', 'customer', 'row', 'seat', 'display_created')
    search_fields = ('customer__username', 'showtime__movie__title_ru')
    list_filter = ('showtime',)
    fieldsets = (
        ('Информация о билете', {'fields': ('showtime', 'customer', 'row', 'seat')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        action = "обновлен" if change else "создан"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: билет #{obj.id} {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление билета #{obj.id}")
        super().delete_model(request, obj)


@admin.register(PromoCode)
class PromoCodeAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'is_active', 'display_created')
    search_fields = ('code', 'description')
    list_filter = ('is_active',)
    fieldsets = (
        ('Информация о промокоде', {'fields': ('code', 'description', 'is_active')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        action = "обновлен" if change else "создан"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: промокод '{obj.code}' {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление промокода '{obj.code}'")
        super().delete_model(request, obj)


@admin.register(Movie)
class MovieAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('title_ru', 'title_en', 'duration', 'rating', 'display_created')
    search_fields = ('title_ru', 'title_en')
    list_filter = ('genres', 'countries')
    filter_horizontal = ('genres', 'countries')
    fieldsets = (
        ('Основная информация', {
            'fields': ('title_ru', 'title_en', 'description', 'duration', 'budget', 'rating', 'poster')
        }),
        ('Категории', {'fields': ('genres', 'countries')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        action = "обновлен" if change else "создан"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: фильм '{obj.title_ru}' {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление фильма '{obj.title_ru}'")
        super().delete_model(request, obj)


@admin.register(Showtime)
class ShowtimeAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('movie', 'hall', 'start_time', 'ticket_price', 'display_created')
    search_fields = ('movie__title_ru', 'hall__name')
    list_filter = ('hall', 'start_time')
    fieldsets = (
        ('Информация о сеансе', {'fields': ('movie', 'hall', 'start_time', 'ticket_price')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        action = "обновлен" if change else "создан"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: сеанс фильма '{obj.movie.title_ru}' {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление сеанса #{obj.id}")
        super().delete_model(request, obj)


@admin.register(CinemaHall)
class CinemaHallAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'rows_count', 'seats_per_row', 'capacity', 'display_created')
    fieldsets = (
        ('Информация о зале', {'fields': ('name', 'rows_count', 'seats_per_row', 'capacity')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('capacity',)

    def save_model(self, request, obj, form, change):
        action = "обновлен" if change else "создан"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: зал '{obj.name}' {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление зала '{obj.name}'")
        super().delete_model(request, obj)


@admin.register(ContactEmployee)
class ContactEmployeeAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('display_full_name', 'position', 'display_email', 'display_phone', 'is_visible', 'display_created')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position', 'user__email')
    list_filter = ('is_visible', 'position')
    fieldsets = (
        ('Сотрудник', {'fields': ('user', 'position', 'is_visible')}),
        ('Контактная информация', {
            'fields': ('phone', 'email', 'photo'),
            'description': 'Оставьте пустыми, чтобы использовать данные из профиля пользователя'
        }),
        ('Дополнительно', {'fields': ('description',)}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('display_full_name', 'display_email', 'display_phone')

    def save_model(self, request, obj, form, change):
        action = "обновлен" if change else "создан"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: контакт сотрудника '{obj.get_full_name()}' {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление контакта '{obj.get_full_name()}'")
        super().delete_model(request, obj)

    def display_full_name(self, obj):
        return obj.get_full_name()

    def display_email(self, obj):
        return obj.get_email() or "—"

    def display_phone(self, obj):
        return obj.get_phone() or "—"

    display_full_name.short_description = 'ФИО Сотрудника'
    display_full_name.admin_order_field = 'user__last_name'
    display_email.short_description = 'Email'
    display_phone.short_description = 'Телефон'


@admin.register(JobVacancy)
class JobVacancyAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('title', 'salary', 'is_active', 'display_created')
    search_fields = ('title', 'description')
    list_filter = ('is_active',)
    fieldsets = (
        ('Информация о вакансии', {'fields': ('title', 'description', 'salary', 'is_active')}),
        ('Даты создания и изменения', {
            'fields': ('display_created_minsk_widget', 'display_created_utc_widget',
                       'display_updated_minsk_widget', 'display_updated_utc_widget'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        action = "обновлена" if change else "создана"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: вакансия '{obj.title}' {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление вакансии '{obj.title}'")
        super().delete_model(request, obj)


@admin.register(AboutCompany, PrivacyPolicy, Country, Genre, FAQItem)
class GeneralAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        action = "обновлен(а)" if change else "создан(а)"
        super().save_model(request, obj, form, change)
        logger.info(f"Администратор {request.user.username}: {self.model._meta.verbose_name} '{obj}' {action}")

    def delete_model(self, request, obj):
        logger.warning(f"Администратор {request.user.username}: удаление {self.model._meta.verbose_name} '{obj}'")
        super().delete_model(request, obj)