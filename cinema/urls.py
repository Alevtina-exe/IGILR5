from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.index_view, name='index'),
    re_path(r'^about/$', views.about_view, name='about'),
    re_path(r'^movies/$', views.movies_list_view, name='movies_list'),
    re_path(r'^dashboard/$', views.dashboard_view, name='dashboard'),
    re_path(r'^contacts/$', views.contacts_view, name='contacts'),
    re_path(r'^reviews/$', views.reviews_view, name='reviews'),
    re_path(r'^login/$', views.login_view, name='login'),
    re_path(r'^logout/$', views.logout_view, name='logout'),
    re_path(r'^register/$', views.register_view, name='register'),
    re_path(r'^movies/(?P<movie_id>\d+)/$', views.movie_detail_view, name='movie_detail'),
    re_path(r'^news/add/$', views.news_create_view, name='news_create'),
    re_path(r'^news/(?P<pk>\d+)/edit/$', views.news_update_view, name='news_update'),
    re_path(r'^news/(?P<pk>\d+)/delete/$', views.news_delete_view, name='news_delete'),
    re_path(r'^profile/$', views.profile_view, name='profile'),
    re_path(r'^showtime/(?P<showtime_id>\d+)/booking/$', views.select_seats_view, name='select_seats'),

    # 2. Обработчик формы бронирования (POST-запрос)
    re_path(r'^showtime/(?P<showtime_id>\d+)/book/$', views.book_ticket_action, name='book_ticket_action'),

    # 3. Удаление билета из личного кабинета
    re_path(r'^ticket/(?P<ticket_id>\d+)/delete/$', views.delete_ticket_view, name='delete_ticket'),

    # 4. Редактирование места в билете
    re_path(r'^ticket/(?P<ticket_id>\d+)/edit/$', views.edit_ticket_seats_view, name='edit_ticket'),
]