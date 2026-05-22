import re

from django import forms
from django.contrib import admin

from .models import *

logger = logging.getLogger('cinema.admin')


def format_local(dt):
    if not dt: return "-"
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt.astimezone(timezone.get_default_timezone()).strftime("%d/%m/%Y %H:%M:%S")

def format_utc(dt):
    if not dt: return "-"
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")


class TimeStampedAdminMixin:
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        readonly_fields.extend(['created_local', 'updated_local'])
        return readonly_fields

    def created_local(self, obj):
        return format_local(obj.created_at_utc)
    created_local.short_description = "Дата создания"

    def updated_local(self, obj):
        if obj.updated_at_utc:
            return format_local(obj.updated_at_utc)
        return "-"
    updated_local.short_description = "Дата изменения"

    def display_created(self, obj):
        return format_local(obj.created_at_utc)
    display_created.short_description = "Дата создания"
    display_created.admin_order_field = 'created_at_utc'


class UserProfileAdminForm(forms.ModelForm):
    username = forms.CharField(
        label="Имя пользователя (Логин)",
        max_length=150,
        validators=[RegexValidator(r'^[a-zA-Z0-9_@+.]+$', 'Только латиница, цифры, @ . + - _')]
    )
    email = forms.EmailField(label="Электронная почта", required=False)
    first_name = forms.CharField(label="Имя", max_length=150, required=False)
    last_name = forms.CharField(label="Фамилия", max_length=150, required=False)
    birth_date = forms.DateField(
        label="Дата рождения",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    is_active = forms.BooleanField(label="Активен", required=False, initial=True)
    is_staff = forms.BooleanField(label="Статус персонала", required=False)
    is_superuser = forms.BooleanField(label="Статус суперпользователя", required=False)

    class Meta:
        model = UserProfile
        fields = ['photo', 'phone']

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
                    self.fields['birth_date'].initial = self.instance.birth_date
                    self.fields['is_active'].initial = user.is_active
                    self.fields['is_staff'].initial = user.is_staff
                    self.fields['is_superuser'].initial = user.is_superuser
            except (User.DoesNotExist, AttributeError):
                pass

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError("Логин обязателен.")
        if not re.match(r'^[a-zA-Z0-9_@+.]+$', username):
            raise forms.ValidationError("Логин только на латинице.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise forms.ValidationError("Пользователь с таким логином уже существует.")
        return username

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 18:
                raise forms.ValidationError("Возраст должен быть 18 или более лет!")
        return birth_date


@admin.register(UserProfile)
class UserProfileAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('get_username', 'get_email', 'phone', 'get_age_display', 'display_created')
    search_fields = ('user__username__icontains', 'user__email__icontains', 'phone')
    list_filter = ('birth_date',)
    ordering = ('user__username',)
    fieldsets = (
        ('Данные учетной записи', {'fields': ('username', 'email', 'first_name', 'last_name')}),
        ('Личные данные', {'fields': ('photo', 'birth_date', 'age_display', 'phone')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('get_date_joined', 'get_last_login', 'age_display')

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            queryset |= self.model.objects.filter(
                user__username__icontains=search_term
            ) | self.model.objects.filter(
                user__email__icontains=search_term
            )
        return queryset, use_distinct

    def age_display(self, obj):
        if obj.age is not None:
            return f"{obj.age} лет"
        return "—"
    age_display.short_description = "Возраст"

    def get_age_display(self, obj):
        if obj.age is not None:
            return f"{obj.age} лет"
        return "—"
    get_age_display.short_description = "Возраст"
    get_age_display.admin_order_field = 'birth_date'

    def save_model(self, request, obj, form, change):
        username = form.cleaned_data.get('username')
        email = form.cleaned_data.get('email', '')
        first_name = form.cleaned_data.get('first_name', '')
        last_name = form.cleaned_data.get('last_name', '')
        birth_date = form.cleaned_data.get('birth_date')
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
            obj.birth_date = birth_date
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
                obj.birth_date = birth_date
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
    get_username.short_description = 'Логин'
    get_username.admin_order_field = 'user__username'

    def get_email(self, obj):
        try:
            return obj.user.email
        except User.DoesNotExist:
            return "—"
    get_email.short_description = 'Email'

    def get_date_joined(self, obj):
        try:
            return format_local(obj.user.date_joined)
        except User.DoesNotExist:
            return "—"
    get_date_joined.short_description = "Дата регистрации"

    def get_last_login(self, obj):
        try:
            return format_local(obj.user.last_login)
        except User.DoesNotExist:
            return "—"
    get_last_login.short_description = "Последний вход"

    class Media:
        js = ('https://cdnjs.cloudflare.com/ajax/libs/imask/6.4.3/imask.min.js',)


@admin.register(NewsArticle)
class NewsArticleAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('title', 'display_created')
    search_fields = ('title',)
    fieldsets = (
        ('Основная информация', {'fields': ('title', 'short_description', 'content', 'image')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Review)
class ReviewAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'rating', 'display_created')
    search_fields = ('user__username', 'text')
    list_filter = ('rating',)
    fieldsets = (
        ('Информация об отзыве', {'fields': ('user', 'rating', 'text')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Ticket)
class TicketAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'showtime', 'customer', 'row', 'seat', 'display_created')
    search_fields = ('customer__username', 'showtime__movie__title_ru')
    list_filter = ('showtime',)
    fieldsets = (
        ('Информация о билете', {'fields': ('showtime', 'customer', 'row', 'seat')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PromoCode)
class PromoCodeAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('code', 'is_active', 'display_created')
    search_fields = ('code', 'description')
    list_filter = ('is_active',)
    fieldsets = (
        ('Информация о промокоде', {'fields': ('code', 'description', 'is_active')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


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
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Showtime)
class ShowtimeAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('movie', 'hall', 'start_time', 'ticket_price', 'display_created')
    search_fields = ('movie__title_ru', 'hall__name')
    list_filter = ('hall', 'start_time')
    fieldsets = (
        ('Информация о сеансе', {'fields': ('movie', 'hall', 'start_time', 'ticket_price')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CinemaHall)
class CinemaHallAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'rows_count', 'seats_per_row', 'capacity', 'display_created')
    fieldsets = (
        ('Информация о зале', {'fields': ('name', 'rows_count', 'seats_per_row', 'capacity')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('capacity',)


@admin.register(ContactEmployee)
class ContactEmployeeAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('display_full_name', 'position', 'display_email', 'display_phone', 'is_visible', 'display_created')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position', 'user__email')
    list_filter = ('is_visible', 'position')
    ordering = ('user__username',)
    fieldsets = (
        ('Сотрудник', {'fields': ('user', 'position', 'is_visible')}),
        ('Контактная информация', {
            'fields': ('phone', 'email', 'photo'),
            'description': 'Оставьте пустыми — данные возьмутся из профиля'
        }),
        ('Дополнительно', {'fields': ('description',)}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            queryset |= self.model.objects.filter(
                user__username__icontains=search_term
            ) | self.model.objects.filter(
                user__first_name__icontains=search_term
            ) | self.model.objects.filter(
                user__last_name__icontains=search_term
            )
        return queryset, use_distinct

    def display_full_name(self, obj):
        return obj.get_full_name()
    display_full_name.short_description = 'ФИО Сотрудника'
    display_full_name.admin_order_field = 'user__last_name'

    def display_email(self, obj):
        return obj.get_email() or "—"
    display_email.short_description = 'Email'

    def display_phone(self, obj):
        return obj.get_phone() or "—"
    display_phone.short_description = 'Телефон'


@admin.register(JobVacancy)
class JobVacancyAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ('title', 'salary', 'is_active', 'display_created')
    search_fields = ('title', 'description')
    list_filter = ('is_active',)
    fieldsets = (
        ('Информация о вакансии', {'fields': ('title', 'description', 'salary', 'is_active')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AboutCompany)
class AboutCompanyAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'description', 'logo', 'requisites')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'content')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Country)
class CountryAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('name',)}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Genre)
class GenreAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('name',)}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FAQItem)
class FAQItemAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('question', 'answer')}),
        ('Даты', {
            'fields': ('created_local', 'updated_local'),
            'classes': ('collapse',)
        }),
    )