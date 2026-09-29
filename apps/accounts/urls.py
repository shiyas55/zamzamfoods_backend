from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CookieLoginView,
    CookieTokenRefreshView,
    CookieLogoutView,
    UserProfileView,
    MySessionsView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    # Cookie-based & Bearer auth endpoints
    path("login/",   CookieLoginView.as_view(),        name="cookie_login"),
    path("refresh/", CookieTokenRefreshView.as_view(),  name="cookie_refresh"),
    path("logout/",  CookieLogoutView.as_view(),        name="cookie_logout"),
    path("token/",   CookieLoginView.as_view(),        name="token_obtain_pair"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),

    # User profile & session management
    path("me/",      UserProfileView.as_view(),         name="user_profile"),
    path("sessions/",           MySessionsView.as_view(), name="my_sessions"),
    path("sessions/<uuid:session_id>/", MySessionsView.as_view(), name="revoke_session"),

    # User CRUD (Owner only)
    path("", include(router.urls)),
]
