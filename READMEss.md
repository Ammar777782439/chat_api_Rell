# تطبيق دردشة في الوقت الفعلي

## نظرة عامة

تطبيق دردشة في الوقت الفعلي تم تطويره باستخدام Django وDjango Channels مع دعم مصادقة Google OAuth. يوفر التطبيق واجهة برمجة تطبيقات RESTful لإدارة الرسائل مع إمكانية البث في الوقت الفعلي باستخدام WebSockets لعرض الرسائل الجديدة فور وصولها.

## الميزات الرئيسية

*   **دردشة في الوقت الفعلي:** استخدام WebSockets (عبر Django Channels) لتحديث الرسائل مباشرة دون الحاجة لتحديث الصفحة.
*   **واجهة برمجة تطبيقات RESTful:** نقاط نهاية API لإدارة الرسائل (جلب، إرسال، تحديث، حذف).
*   **مصادقة المستخدمين:**
    *   تسجيل الدخول/إنشاء حساب باستخدام اسم المستخدم وكلمة المرور.
    *   تسجيل الدخول باستخدام حساب Google (Google OAuth).
    *   مصادقة API باستخدام التوكن أو الجلسات.
*   **قاعدة بيانات PostgreSQL:** استخدام قاعدة بيانات PostgreSQL لتخزين بيانات المستخدمين والرسائل.
*   **حذف ناعم (Soft Delete):** إمكانية حذف الرسائل دون إزالتها فعليًا من قاعدة البيانات.
*   **اختبارات شاملة:** تغطية اختبار عالية لضمان جودة الكود واستقراره.
*   **بيانات وهمية:** أمر مخصص لإنشاء بيانات تجريبية (مستخدمين ورسائل).

## التقنيات المستخدمة

*   **الواجهة الخلفية:** Python, Django, Django REST Framework, Django Channels
*   **قاعدة البيانات:** PostgreSQL
*   **المصادقة:** Django Allauth (لـ Google OAuth), DRF Token Authentication, Session Authentication
*   **الوقت الفعلي:** WebSockets, Daphne (ASGI Server)
*   **الاختبار:** Pytest, Coverage.py
*   **أخرى:** Faker (لتوليد البيانات الوهمية)

## هيكل المشروع

```
chat_app-main-main/
├── chat/                   # التطبيق الرئيسي للدردشة
│   ├── management/         # أوامر الإدارة المخصصة
│   ├── migrations/         # ترحيلات قاعدة البيانات
│   ├── models.py           # نماذج البيانات (User, Message)
│   ├── serializers.py      # مسلسلات API
│   ├── consumers.py        # مستهلكي WebSocket للدردشة
│   ├── views.py            # المشاهدات ونقاط نهاية API
│   ├── urls.py             # روابط URL الخاصة بتطبيق chat
│   └── tests.py            # مجموعة الاختبارات
├── users/                  # تطبيق إدارة المستخدمين (إذا كان منفصلاً)
│   └── ...
├── templates/              # قوالب HTML (لواجهة المستخدم)
│   ├── base.html
│   ├── chat.html
│   ├── home.html
│   ├── login.html
│   └── ...
├── chat_app/               # حزمة المشروع الرئيسية
│   ├── settings.py         # إعدادات المشروع (Database, Auth, etc.)
│   ├── urls.py             # تكوين URL الرئيسي للمشروع
│   ├── asgi.py             # تكوين ASGI (للـ WebSockets)
│   └── wsgi.py             # تكوين WSGI
├── .gitignore              # الملفات والمجلدات التي يتجاهلها Git
├── docker-compose.yml      # (إذا كنت تستخدم Docker)
├── manage.py               # سكريبت إدارة Django
├── requirements.txt        # قائمة الاعتماديات
├── API_USAGE.md            # توثيق API باللغة العربية
├── API_USAGE_EN.md         # توثيق API باللغة الإنجليزية
└── project_documentation.md # توثيق المشروع التفصيلي
```

## الإعداد والتثبيت

### المتطلبات المسبقة

*   Python 3.8+
*   PostgreSQL
*   pip
*   virtualenv (موصى به)

### خطوات الإعداد

1.  **استنساخ المستودع:**
    ```bash
    git clone <your-repository-url>
    cd chat_app-main-main
    ```

2.  **إنشاء وتفعيل بيئة افتراضية:**
    ```bash
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```

3.  **تثبيت الاعتماديات:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **إعداد قاعدة بيانات PostgreSQL:**
    *   تأكد من أن PostgreSQL يعمل.
    *   قم بإنشاء قاعدة بيانات (اسمها الافتراضي في `settings.py` هو `chatApp`، تأكد من مطابقته أو تعديله).
        ```sql
        -- مثال باستخدام psql
        CREATE DATABASE chatApp;
        ```
    *   قم بتحديث بيانات اعتماد قاعدة البيانات (اسم المستخدم، كلمة المرور، المضيف، المنفذ) في ملف `chat_app/settings.py` إذا لزم الأمر.

5.  **تطبيق الترحيلات:**
    ```bash
    python manage.py migrate
    ```

6.  **إنشاء مستخدم مشرف (اختياري):**
    ```bash
    python manage.py createsuperuser
    ```

7.  **إنشاء بيانات وهمية (اختياري):**
    ```bash
    # إنشاء 15 مستخدم و 300 رسالة
    python manage.py create_dummy_data --users 15 --messages 300
    ```

8.  **إعداد Google OAuth (مهم):**
    *   اذهب إلى [Google Cloud Console](https://console.cloud.google.com/).
    *   أنشئ مشروعًا جديدًا أو استخدم مشروعًا موجودًا.
    *   اذهب إلى "APIs & Services" -> "Credentials".
    *   أنشئ "OAuth client ID" جديدًا من نوع "Web application".
    *   أضف `http://127.0.0.1:8000/accounts/google/login/callback/` (أو عنوان URL الخاص بك إذا كان مختلفًا) إلى "Authorized redirect URIs".
    *   احصل على `Client ID` و `Client Secret`.
    *   قم بتحديث هذه القيم في ملف `chat_app/settings.py` ضمن `SOCIALACCOUNT_PROVIDERS['google']['APP']`.

## الاستخدام

1.  **تشغيل خادم التطوير:**
    ```bash
    python manage.py runserver
    ```
2.  **الوصول إلى التطبيق:** افتح المتصفح وانتقل إلى `http://127.0.0.1:8000/`.
3.  **استخدام واجهة برمجة التطبيقات (API):**
    *   للحصول على تفاصيل حول كيفية المصادقة واستخدام نقاط نهاية الـ API والـ WebSocket، يرجى الرجوع إلى ملفات التوثيق التالية:
        *   [دليل استخدام API (العربية)](API_USAGE.md)
        *   [API Usage Guide (English)](API_USAGE_EN.md)

## الاختبار

*   **تشغيل جميع الاختبارات:**
    ```bash
    python manage.py test
    ```
*   **قياس تغطية الاختبار:**
    ```bash
    coverage run --source='.' manage.py test
    coverage report -m
    ```
    (تأكد من تثبيت `coverage`: `pip install coverage`)
