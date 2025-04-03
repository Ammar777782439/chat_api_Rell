
from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

urlpatterns = [
    path('profile/', views.chat_view, name='chat'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('api/auth/google/', views.GoogleLoginView.as_view(), name='google_login'),
    path('api/auth/google/callback/', views.GoogleCallbackView.as_view(), name='google_callback'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/google-token/', views.GoogleUserTokenView.as_view(), name='google_user_token'),
]
