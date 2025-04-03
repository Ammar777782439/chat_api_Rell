from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


# نمط التصميم facory انشاء مسارات افتراضيه لل api 
router = DefaultRouter()
router.register(r'messages', views.MessageViewSet, basename='message')

urlpatterns = [
    path('', views.home_view, name='home'),
    path('api/', include(router.urls)),
    path('chat/<str:room_name>/', views.chat_room, name='chat'),
]

# للتنقل بين الرسائل
# http://127.0.0.1:8000/api/messages/?page=2