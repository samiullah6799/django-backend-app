from django.urls import path
from routing import views

urlpatterns = [
    path("api/route/", views.route_view),
    path("map/", views.map_view),

]