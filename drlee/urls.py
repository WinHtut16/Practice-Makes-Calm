from django.contrib import admin
from django.urls import path

from study import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("researcher/", views.researcher, name="researcher"),
    path("researcher/new/", views.researcher_new, name="researcher_new"),
    path("researcher/<str:pid>/", views.monitor, name="monitor"),
    path("s/<str:pid>/", views.session, name="session"),
    path("s/<str:pid>/api/chat/", views.api_chat, name="api_chat"),
    path("s/<str:pid>/api/timeout/", views.api_timeout, name="api_timeout"),
]
