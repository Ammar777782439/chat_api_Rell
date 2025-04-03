from chat.models import Message
from django.shortcuts import render
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import HttpResponseRedirect

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]  # السماح بالوصول بدون مصادقة

    def post(self, request):
        token = request.data.get('token')
        try:
            print(f"Received token: {token[:10]}...")
            # محاولة التحقق من ID token أولاً
            try:
                id_info = id_token.verify_oauth2_token(
                    token,
                    google_requests.Request(),
                    settings.GOOGLE_CLIENT_ID
                )
                if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise ValueError('Invalid issuer.')

                email = id_info['email']
                google_id = id_info['sub']
                avatar = id_info.get('picture')
                print(f"Verified ID token for: {email}")

            except Exception as e:
                print(f"ID token verification failed: {str(e)}")
                # إذا فشل التحقق من ID token، حاول استخدام access token
                headers = {'Authorization': f'Bearer {token}'}
                userinfo_response = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers=headers)

                if not userinfo_response.ok:
                    error_msg = f"Failed to get user info: {userinfo_response.status_code} - {userinfo_response.text}"
                    print(error_msg)
                    raise ValueError(error_msg)

                userinfo = userinfo_response.json()
                email = userinfo['email']
                google_id = userinfo['sub']
                avatar = userinfo.get('picture')
                print(f"Got user info using access token for: {email}")

            # إنشاء أو استرجاع المستخدم
            user, _ = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'google_id': google_id,
                    'avatar': avatar,
                }
            )
            print(f"User authenticated: {user.username} (ID: {user.id})")

            # تسجيل الدخول للمستخدم
            from django.contrib.auth import login
            login(request, user)
            print(f"User logged in: {user.username}")

            # إنشاء رموز JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            })
        except Exception as e:
            error_msg = f"Error in Google login: {str(e)}"
            print(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)



@method_decorator(csrf_exempt, name='dispatch')
class GoogleCallbackView(APIView):
    permission_classes = [AllowAny]  # السماح بالوصول بدون مصادقة
    authentication_classes = []  # لا تتطلب أي مصادقة
    def get(self, request):
        try:
            code = request.GET.get('code')
            if not code:
                return Response({'error': 'No authorization code provided'}, status=status.HTTP_400_BAD_REQUEST)

            print(f"Received authorization code: {code[:10]}...")

            # Exchange authorization code for access token
            token_url = 'https://oauth2.googleapis.com/token'
            data = {
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': 'http://localhost:8000/users/api/auth/google/callback/',
                'grant_type': 'authorization_code'
            }

            print("Exchanging code for token...")
            response = requests.post(token_url, data=data)
            if not response.ok:
                error_msg = f"Failed to exchange code for token: {response.status_code} - {response.text}"
                print(error_msg)
                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

            token_data = response.json()
            access_token = token_data.get('access_token')
            print(f"Received access token: {access_token[:10]}...")

            # Get user info using access token
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            print("Getting user info...")
            userinfo_response = requests.get(userinfo_url, headers=headers)

            if not userinfo_response.ok:
                error_msg = f"Failed to get user info: {userinfo_response.status_code} - {userinfo_response.text}"
                print(error_msg)
                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

            userinfo = userinfo_response.json()
            print(f"Received user info for: {userinfo.get('email')}")
        except Exception as e:
            error_msg = f"Error in OAuth callback: {str(e)}"
            print(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # Get or create user
            print(f"Creating or getting user with email: {userinfo['email']}")
            user, _ = CustomUser.objects.get_or_create(
                email=userinfo['email'],
                defaults={
                    'username': userinfo['email'],
                    'google_id': userinfo['sub'],
                    'avatar': userinfo.get('picture'),
                }
            )
            print(f"User authenticated: {user.username} (ID: {user.id})")

            # تسجيل الدخول للمستخدم باستخدام الجلسة
            from django.contrib.auth import login
            login(request, user)
            print(f"User logged in: {user.username}")

            # Find another user to chat with, or use the user's own username if no other users
            other_users = CustomUser.objects.exclude(id=user.id).first()
            chat_username = other_users.username if other_users else user.username
            print(f"Chat with: {chat_username}")

            # إنشاء URL مباشرة لصفحة الدردشة
            chat_url = f'/chat/{chat_username}/'
            print(f"Redirecting to: {chat_url}")

            # إعادة توجيه المستخدم إلى صفحة الدردشة
            return HttpResponseRedirect(chat_url)
        except Exception as e:
            error_msg = f"Error in user creation or login: {str(e)}"
            print(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.contrib.auth.decorators import login_required

@login_required
def chat_view(request):
    messages = Message.objects.filter(deleted_at__isnull=True).order_by('-created_at')[:50]
    return render(request, 'chat.html', {'messages': messages})

def login_view(request):
    return render(request, 'login.html')
