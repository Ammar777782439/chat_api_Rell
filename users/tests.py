from django.test import TestCase, Client  # استيراد أدوات الاختبار حق Django
from django.contrib.auth.models import User  # استيراد نموذج المستخدم الأساسي
from django.contrib.messages import get_messages  # استيراد الرسائل اللي بتظهر للمستخدم

class UserViewsTest(TestCase):
    def setUp(self):
        """هنا بجهز البيانات اللي بستخدمها في الاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client = Client()  # هذا الكلاينت بيحاكي المستخدم اللي بيزور الموقع

    def test_login_page_get(self):
        """اختبار هل صفحة تسجيل الدخول تفتح عادي"""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)  # لازم الصفحة تفتح بدون مشاكل
        self.assertTemplateUsed(response, 'login.html')  # يتأكد إنها تستخدم القالب الصح

    def test_login_page_post_valid(self):
        """اختبار تسجيل الدخول بمعلومات صحيحة"""
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'testpassword'
        })
        self.assertEqual(response.status_code, 302)  # المفروض يعيد التوجيه بعد تسجيل الدخول
        self.assertRedirects(response, f'/chat/{self.user.username}/')  # لازم يروح لصفحة الشات

    def test_login_page_post_invalid(self):
        """اختبار تسجيل الدخول بكلمة مرور غلط"""
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # بيبقى بنفس الصفحة
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)  # لازم تظهر رسالة خطأ
        self.assertIn('Invalid', str(messages[0]))  # نشوف الرسالة إذا فيها "Invalid"

    def test_login_page_authenticated_user(self):
        """إذا المستخدم مسجل دخوله، لازم ما يخليه يروح صفحة تسجيل الدخول"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 302)  # لازم يرجعه من صفحة تسجيل الدخول
        self.assertRedirects(response, f'/chat/{self.user.username}/')

    def test_home_view_authenticated(self):
        """اختبار الصفحة الرئيسية إذا كان المستخدم مسجل دخول"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/chat/{self.user.username}/')

    def test_home_view_unauthenticated(self):
        """إذا المستخدم مش مسجل دخول، لازم يرجعه لصفحة تسجيل الدخول"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login/')

    def test_signup_view_get(self):
        """اختبار هل صفحة التسجيل تفتح عادي"""
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_signup_view_post_valid(self):
        """اختبار التسجيل بمعلومات صحيحة"""
        response = self.client.post('/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User'
        })
        self.assertEqual(response.status_code, 302)  # لازم يعيد التوجيه بعد التسجيل
        self.assertTrue(User.objects.filter(username='newuser').exists())  # نشوف إذا المستخدم انضاف

    def test_signup_view_post_password_mismatch(self):
        """اختبار لما يكون الباسوردات مش متطابقين"""
        response = self.client.post('/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'password123',
            'password2': 'differentpassword',
        })
        self.assertEqual(response.status_code, 200)  # المفروض يبقى في نفس الصفحة
        self.assertFalse(User.objects.filter(username='newuser').exists())  # ما يضيف المستخدم
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn('Passwords do not match', str(messages[0]))  # نشوف إذا الرسالة صح

    def test_signup_view_authenticated_user(self):
        """المفروض المستخدم المسجل ما يخليه يروح صفحة التسجيل"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/chat/{self.user.username}/')

    def test_signup_view_post_existing_username(self):
        """اختبار لما المستخدم يحاول يسجل بنفس الاسم اللي موجود"""
        response = self.client.post('/register/', {
            'username': 'testuser',  # الاسم هذا موجود أساسًا
            'email': 'another@example.com',
            'password1': 'password123',
            'password2': 'password123',
        })
        self.assertEqual(response.status_code, 200)  # المفروض يبقى في نفس الصفحة
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn('duplicate key value', str(messages[0]))  # لازم تظهر رسالة الخطأ

    def test_logout_view(self):
        """اختبار تسجيل الخروج"""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post('/logout/')  # تسجيل الخروج عبر POST
        self.assertEqual(response.status_code, 302)  # المفروض يعيد التوجيه
        self.assertRedirects(response, '/login/')  # لازم يوجهه لصفحة تسجيل الدخول
        self.assertFalse('_auth_user_id' in self.client.session)  # تأكد إنه خرج


