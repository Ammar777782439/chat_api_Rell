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
# Import csrf_exempt and method_decorator if they are not already imported elsewhere
# (Assuming they might be needed for GoogleCallbackView as well)
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class GoogleLoginView(APIView):
    """
    API view for handling Google OAuth login.

    This view accepts a Google OAuth token and returns JWT tokens for authentication.

    Endpoints:
        POST /users/api/auth/google/: Authenticate with Google OAuth token
            - Required fields: token (Google OAuth token)
            - Returns: refresh token, access token, and user information
    """
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
            # The following code was unreachable because it came after 'return Response'
            # other_users = CustomUser.objects.exclude(id=user.id).first()
            # chat_username = other_users.username if other_users else user.username
            # print(f"Chat with: {chat_username}")
            #
            # # إنشاء URL مباشرة لصفحة الدردشة
            # chat_url = f'/chat/{chat_username}/'
            # print(f"Redirecting to: {chat_url}")
            #
            # # إعادة توجيه المستخدم إلى صفحة الدردشة
            # return HttpResponseRedirect(chat_url)
        except Exception as e:
            error_msg = f"Error in Google login: {str(e)}"
            print(error_msg)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)



@method_decorator(csrf_exempt, name='dispatch')
class GoogleCallbackView(APIView):
    """
    API view for handling Google OAuth callback.

    This view handles the callback from Google OAuth authentication process.
    It exchanges the authorization code for an access token, retrieves user information,
    creates or retrieves the user, and redirects to the chat page.

    Endpoints:
        GET /users/api/auth/google/callback/: Handle Google OAuth callback
            - Required query parameters: code (authorization code from Google)
            - Redirects to: /chat/{username}/ after successful authentication
    """
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
            print(access_token)
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
    """
    View function for rendering the chat interface.

    This view displays the chat interface with the most recent messages.
    It requires the user to be authenticated.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered chat.html template with context data.
    """
    messages = Message.objects.filter(deleted_at__isnull=True).order_by('-created_at')[:50]
    return render(request, 'chat.html', {'messages': messages})

def login_view(request):
    """
    View function for rendering the login page.

    This view displays the login page with options to authenticate using Google OAuth.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered login.html template.
    """
    return render(request, 'login.html')

class GoogleUserTokenView(APIView):
    """
    API view to get tokens for Google-authenticated users using their email.

    This view allows Google-authenticated users to obtain JWT tokens by providing their email.
    It verifies that the user was previously authenticated via Google before issuing tokens.

    Endpoints:
        POST /users/api/google-token/: Get JWT tokens using email
            - Required fields: email (user's email address)
            - Returns: refresh token, access token, and user information
    """
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find the user by email
            user = CustomUser.objects.get(email=email)

            # Check if the user has a google_id (was authenticated via Google)
            if not user.google_id:
                return Response({'error': 'User was not authenticated via Google'},
                               status=status.HTTP_400_BAD_REQUEST)

            # Generate tokens
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
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
