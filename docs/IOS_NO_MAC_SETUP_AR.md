# تجهيز وازن للآيفون

تحديث: 26 سبتمبر 2026.

## ما أصبح موجودًا

- `Validate WAZEN iOS`: يعمل عند تغيير مصادر الموبايل أو إعداد بناء iOS على `main`، ويمكن تشغيله يدويًا.
- ينشئ مشروع iOS من Flutter داخل macOS runner، ويضيف أذونات الكاميرا والصور والميكروفون والتعرف على الكلام وKeychain، ثم يشغّل الاختبارات ويبني release غير موقّع.
- يحفظ مشروع iOS الناتج وملف `.app` غير الموقع ونسخة اعتماديات Flutter كـGitHub Actions artifact لمدة سبعة أيام.
- هذا مخرج تحقق هندسي **لا يمكن تثبيته على آيفون كما هو**.

## نسخة موقعة للأجهزة المسجلة

تم إعداد `Build WAZEN iOS Ad Hoc` ليعمل يدويًا فقط. لم يُختبر مسار التوقيع الفعلي دون شهادات الحساب. يتحقق من مطابقة profile للفريق والتطبيق وصلاحيته ووجود أجهزة مسجلة، ويبني IPA ويحفظها دون نشر إلى المتجر أو الاستضافة.

المتطلبات الخارجية:

1. حساب Apple Developer صالح للتوزيع، وهوية فريقه.
2. Bundle ID مملوك للحساب؛ `ae.wazen.app` قيمة البناء غير الموقع فقط وليست إثبات ملكية.
3. Apple Distribution certificate مع المفتاح الخاص في ملف P12 وكلمة مروره.
4. Ad Hoc provisioning profile للتطبيق والفريق، يتضمن UDID للآيفون المقصود.
5. عنوان backend تجريبي مؤكد يعمل عبر HTTPS، واختبار الحساب وروابط البريد.

أدخل البيانات في **GitHub Settings → Secrets and variables → Actions**؛ لا تُرسل المفاتيح الخاصة أو كلمات المرور في المحادثة، ولا تضعها في الكود.

| النوع | الاسم |
| --- | --- |
| Secret | `APPLE_TEAM_ID` |
| Secret | `IOS_CERTIFICATE_P12_BASE64` |
| Secret | `IOS_CERTIFICATE_PASSWORD` |
| Secret | `IOS_PROVISIONING_PROFILE_BASE64` |
| Variable | `WAZEN_BUNDLE_ID` |
| Variable | `WAZEN_API_BASE_URL` |

بعد استكمالها: Actions → Build WAZEN iOS Ad Hoc → Run workflow على `main`.
الملف الناتج مخصص للأجهزة المدرجة في profile. تنزيل IPA من Safari وحده لا يثبت التطبيق؛ يلزم مسار تثبيت Ad Hoc مناسب أو الانتقال إلى TestFlight. TestFlight يحتاج إعداد App Store Connect ورفع البناء، ولم يُنفذ في هذه المرحلة.

## فحوص قبل توزيع نسخة للمستخدم

راجع `PRODUCT_PLAN_RECONCILIATION_AR.md`، خصوصًا مشكلة فقد حالة المغذيات المجهولة، وإكمال روابط التحقق واستعادة كلمة المرور على iOS. يجب اختبار هذه المتطلبات على جهاز فعلي قبل وصف النسخة بأنها جاهزة.

النشر على Railway/GitHub Pages لم يُستأنف. تعليمات PWA القديمة كانت تشير إلى workflow غير موجود؛ workflow الويب الحالي يتحقق من البناء فقط.

## المراجع التقنية

- https://docs.flutter.dev/deployment/ios
- https://docs.flutter.dev/platform-integration/ios/setup
- https://pub.dev/packages/speech_to_text
- https://pub.dev/packages/flutter_secure_storage/versions/9.2.4
