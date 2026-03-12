from django.urls import path, include

urlpatterns = [
    path('', include('workout.urls')),
]
