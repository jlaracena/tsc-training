from django.urls import path
from . import views

urlpatterns = [
    path('',                                    views.today,                  name='today'),
    path('save/',                               views.save_session,           name='save_session'),
    path('metrics/',                            views.save_metrics,           name='save_metrics'),
    path('history/',                            views.history,                name='history'),
    path('api/progress/<str:exercise_name>/',   views.exercise_progress_api,  name='exercise_progress'),
]
