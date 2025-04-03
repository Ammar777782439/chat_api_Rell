from chat.models import Message
from django.shortcuts import render, redirect
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken

class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get('token')
        try:
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

            except Exception as e:
                # إذا فشل التحقق من ID token، حاول استخدام access token
                headers = {'Authorization': f'Bearer {token}'}
                userinfo_response = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers=headers)

                if not userinfo_response.ok:
                    raise ValueError('Invalid token or failed to get user info')

                userinfo = userinfo_response.json()
                email = userinfo['email']
                google_id = userinfo['sub']
                avatar = userinfo.get('picture')

            # إنشاء أو استرجاع المستخدم
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'google_id': google_id,
                    'avatar': avatar,
                }
            )

            # إنشاء رموز JWT
            refresh = RefreshToken.for_user(user)
            print(refresh)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GoogleCallbackView(APIView):
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({'error': 'No authorization code provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Exchange authorization code for access token
        token_url = 'https://oauth2.googleapis.com/token'
        data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': 'http://localhost:8000/users/api/auth/google/callback/',
            'grant_type': 'authorization_code'
        }

        response = requests.post(token_url, data=data)
        if not response.ok:
            return Response({'error': 'Failed to exchange code for token'}, status=status.HTTP_400_BAD_REQUEST)

        token_data = response.json()
        access_token = token_data.get('access_token')

        # Get user info using access token
        userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)

        if not userinfo_response.ok:
            return Response({'error': 'Failed to get user info'}, status=status.HTTP_400_BAD_REQUEST)

        userinfo = userinfo_response.json()

        # Get or create user
        user, created = CustomUser.objects.get_or_create(
            email=userinfo['email'],
            defaults={
                'username': userinfo['email'],
                'google_id': userinfo['sub'],
                'avatar': userinfo.get('picture'),
            }
        )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        print(refresh)
        # Redirect to home page with tokens as URL parameters
        redirect_url = f'/?access_token={str(refresh.access_token)}&refresh_token={str(refresh)}'
        return HttpResponseRedirect(redirect_url)

from django.contrib.auth.decorators import login_required

@login_required
def chat_view(request):
    messages = Message.objects.filter(deleted_at__isnull=True).order_by('-created_at')[:50]
    return render(request, 'chat.html', {'messages': messages})

def login_view(request):
    return render(request, 'login.html')
