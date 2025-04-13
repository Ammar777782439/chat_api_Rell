# توثيق مشروع واجهة برمجة تطبيقات الدردشة في الوقت الفعلي

## نظرة عامة على المشروع

تم تطوير تطبيق دردشة في الوقت الفعلي باستخدام Django وDjango Channels مع دعم مصادقة Google OAuth. يوفر التطبيق واجهة برمجة تطبيقات RESTful للرسائل مع إمكانية البث في الوقت الفعلي باستخدام WebSockets.

## المتطلبات التقنية المنفذة

### 1. قاعدة البيانات

- **نوع قاعدة البيانات**: تم استخدام PostgreSQL كما هو مطلوب
- **الترحيلات والبذور**: تم استخدام نظام الترحيلات في Django لإنشاء هيكل قاعدة البيانات وتم إنشاء أمر مخصص لإنشاء بيانات وهمية
- **جداول قاعدة البيانات**:
  - جدول `Message` مع الحقول: content, sender (user_id), receiver (user_id), timestamp (created_at), مع دعم soft delete من خلال حقل deleted_at
  - استخدام جدول `User` المدمج في Django مع توسيعه حسب الحاجة
  - تم إنشاء العلاقات المناسبة بين الجداول

#### تكوين قاعدة البيانات PostgreSQL

تم تكوين قاعدة البيانات في ملف `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'chatApp',  # اسم قاعدة البيانات
        'USER': 'postgres',    # اسم المستخدم
        'PASSWORD': 'your_password',  # كلمة المرور
        'HOST': 'localhost',   # المضيف
        'PORT': '5432',        # المنفذ
    }
}
```

### 2. نقاط نهاية واجهة برمجة التطبيقات (API Endpoints)

#### نقاط نهاية الرسائل

- **GET /api/messages/**
  - جلب أحدث الرسائل مع دعم التقسيم إلى صفحات (10 رسائل لكل صفحة)
  - دعم التصفية حسب المستخدمين من خلال معلمة الاستعلام `user`
  - ترتيب الرسائل حسب الأحدث أولاً
  - مثال: `GET /api/messages/?user=username&page=1&page_size=10`

- **POST /api/messages/**
  - إرسال رسالة جديدة
  - التحقق من صحة المحتوى (مطلوب)
  - تعيين المرسل تلقائيًا إلى المستخدم الحالي
  - مثال للبيانات المرسلة:
    ```json
    {
      "receiver": "username",
      "content": "Hello, this is a test message"
    }
    ```

- **POST /api/messages/{id}/update_message/**
  - تحديث محتوى رسالة موجودة
  - التحقق من أن المستخدم هو مرسل الرسالة
  - التحقق من صحة المحتوى الجديد

- **DELETE /api/messages/{id}/delete_message/**
  - حذف رسالة موجودة
  - التحقق من أن المستخدم هو مرسل الرسالة

#### نقاط نهاية المصادقة (OAuth)

- **GET /accounts/google/login/**
  - بدء عملية تسجيل الدخول باستخدام Google OAuth
  - إعادة توجيه المستخدم إلى صفحة مصادقة Google

- **GET /accounts/google/callback/**
  - معالجة استجابة مصادقة Google
  - التحقق من صحة البيانات لمنع التزوير
  - إنشاء جلسة للمستخدم

### 3. البث في الوقت الفعلي

- تم استخدام Django Channels وWebSockets لبث الرسائل الجديدة في الوقت الفعلي
- تم تنفيذ `ChatConsumer` للتعامل مع اتصالات WebSocket
- يتم بث الرسائل الجديدة والمحدثة تلقائيًا إلى جميع العملاء المتصلين في نفس غرفة الدردشة
- تم تنفيذ آلية لإنشاء اسم فريد لكل غرفة دردشة بناءً على المستخدمين المشاركين

### 4. الأمان والتحقق من الصحة

- تم حماية جميع نقاط نهاية الدردشة باستخدام وسيط المصادقة
- تم التأكد من أن المستخدمين يمكنهم فقط حذف/تعديل رسائلهم الخاصة
- تم التحقق من بيانات استجابة Google OAuth لمنع التزوير
- تم تنفيذ التحقق من صحة البيانات المدخلة في جميع نقاط النهاية

### 5. الاختبار

- تم تحقيق تغطية اختبار وحدة بنسبة 80% كما هو مطلوب
- تم كتابة اختبارات شاملة لـ:
  - النماذج (Models)
  - المشاهدات (Views)
  - واجهة برمجة التطبيقات (API)
  - المستهلكين (Consumers)
  - المسلسلات (Serializers)
- يمكن تشغيل الاختبارات باستخدام الأمر: `python manage.py test`
- يمكن قياس تغطية الاختبار باستخدام: `coverage run --source=chat manage.py test`

### 6. جودة الكود وقابلية الصيانة

- **توثيق الكود**: تم توثيق جميع الفئات والدوال بشكل شامل باستخدام docstrings
- **التزامات Git التقليدية**: تم استخدام نمط الالتزامات التقليدية في Git
- **أنماط التصميم**: تم استخدام أنماط التصميم المناسبة مثل Repository Pattern وFactory Pattern
- **تقليل الاعتماديات**: تم استخدام أقل عدد ممكن من المكتبات الخارجية

## هيكل المشروع

```
chat_app/
├── chat/                   # التطبيق الرئيسي
│   ├── management/         # أوامر الإدارة المخصصة
│   │   └── commands/       # أوامر مخصصة مثل create_dummy_data
│   ├── migrations/         # ترحيلات قاعدة البيانات
│   ├── models.py           # نماذج البيانات
│   ├── serializers.py      # مسلسلات API
│   ├── consumers.py        # مستهلكي WebSocket
│   ├── views.py            # المشاهدات ونقاط نهاية API
│   └── tests.py            # مجموعة الاختبارات
├── templates/              # قوالب HTML
│   └── chat.html           # واجهة الدردشة الرئيسية
├── static/                 # الملفات الثابتة (CSS، JS)
├── chat_app/               # حزمة المشروع الرئيسية
│   ├── settings.py         # إعدادات المشروع
│   ├── urls.py             # تكوين URL
│   ├── asgi.py             # تكوين ASGI (للـ WebSockets)
│   └── wsgi.py             # تكوين WSGI
├── manage.py               # سكريبت إدارة Django
└── requirements.txt        # قائمة الاعتماديات
```

## تكوين مصادقة Google OAuth

تم تكوين مصادقة Google OAuth في ملف `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'django.contrib.auth',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # ...
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# إعدادات مزود Google
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': 'YOUR_GOOGLE_CLIENT_ID',
            'secret': 'YOUR_GOOGLE_CLIENT_SECRET',
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}
```

## تثبيت وإعداد المشروع

### المتطلبات المسبقة

- Python 3.8+
- PostgreSQL
- pip
- virtualenv (موصى به)

### خطوات الإعداد

1. استنساخ المستودع:
   ```bash
   git clone https://github.com/yourusername/chat-application.git
   cd chat-application
   ```

2. إنشاء وتفعيل بيئة افتراضية:
   ```bash
   python -m venv venv
   source venv/bin/activate  # على Windows: venv\Scripts\activate
   ```

3. تثبيت الاعتماديات:
   ```bash
   pip install -r requirements.txt
   ```

4. إنشاء قاعدة بيانات PostgreSQL:
   ```bash
   createdb chatAppMin
   ```

5. تطبيق الترحيلات:
   ```bash
   python manage.py migrate
   ```

6. إنشاء مستخدم مشرف:
   ```bash
   python manage.py createsuperuser
   ```

7. إنشاء بيانات وهمية (اختياري):
   ```bash
   python manage.py create_dummy_data --users 15 --messages 300
   ```

8. تشغيل خادم التطوير:
   ```bash
   python manage.py runserver
   ```

9. الوصول إلى التطبيق على http://127.0.0.1:8000/

## استخدام واجهة برمجة التطبيقات

### مصادقة

قبل استخدام واجهة برمجة التطبيقات، يجب على المستخدمين تسجيل الدخول باستخدام Google OAuth:

1. توجيه المستخدم إلى: `GET /accounts/google/login/`
2. بعد المصادقة الناجحة، سيتم إعادة توجيه المستخدم إلى التطبيق مع رمز مصادقة

### استخدام نقاط نهاية الرسائل

#### جلب الرسائل

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" "http://your-domain.com/api/messages/?user=john&page=1&page_size=10"
```

#### إرسال رسالة جديدة

```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d '{"receiver": "john", "content": "Hello!"}' "http://your-domain.com/api/messages/"
```

#### تحديث رسالة

```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d '{"content": "Updated message"}' "http://your-domain.com/api/messages/123/update_message/"
```

#### حذف رسالة

```bash
curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" "http://your-domain.com/api/messages/123/delete_message/"
```

## الاختبارات

### تشغيل الاختبارات

```bash
python manage.py test
```

### قياس تغطية الاختبار

```bash
coverage run --source=chat manage.py test
coverage report
```

## التحديات والحلول

### تحدي: تكامل مصادقة Google OAuth
**الحل**: استخدام مكتبة django-allauth لتبسيط عملية التكامل مع Google OAuth، مع التحقق الإضافي من البيانات المستلمة لمنع التزوير.

### تحدي: البث في الوقت الفعلي
**الحل**: استخدام Django Channels لإدارة اتصالات WebSocket، مع تنفيذ آلية لإنشاء غرف دردشة فريدة لكل محادثة.

### تحدي: أمان الرسائل
**الحل**: تنفيذ سياسات تضمن أن المستخدمين يمكنهم فقط تعديل أو حذف رسائلهم الخاصة، مع التحقق من الصلاحيات في كل من واجهة برمجة التطبيقات ومستهلكي WebSocket.

## الخلاصة

تم تنفيذ جميع متطلبات المشروع بنجاح، مع التركيز على الأمان وقابلية الصيانة وجودة الكود. يوفر التطبيق واجهة برمجة تطبيقات RESTful للرسائل مع دعم البث في الوقت الفعلي باستخدام WebSockets ومصادقة Google OAuth.

---

## ملحق: قائمة الاعتماديات

```
Django>=3.2,<4.0
channels>=3.0.0
daphne>=3.0.0
djangorestframework>=3.12.0
django-allauth>=0.45.0
psycopg2-binary>=2.9.0
Faker>=8.0.0
coverage>=5.5
pytest>=6.2.0
pytest-django>=4.4.0
pytest-asyncio>=0.15.0
```
