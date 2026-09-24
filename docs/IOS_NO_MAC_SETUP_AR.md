# تشغيل WAZEN على iPhone بدون Mac

## المسار الأسرع الآن: PWA
هذا المسار لا يحتاج Xcode ولا App Store ولا توقيع Apple.

1. ارفع المستودع إلى GitHub.
2. انشر الـBackend على Railway.
3. أضف في GitHub Repository Variables:
   - `WAZEN_API_BASE_URL` = رابط الـBackend وينتهي بـ `/api/v1`
4. شغّل Workflow: **WAZEN Web PWA**
5. افتح رابط GitHub Pages من Safari على الآيفون.
6. Share → Add to Home Screen → Open as Web App → Add.

## Native iOS بدون App Store
GitHub Actions يستطيع بناء التطبيق على macOS runner، لكن iPhone لن يثبت IPA غير موقع.

لـAd Hoc تحتاج:
- عضوية Apple Developer Program.
- Bundle ID، مثال: `ae.wazen.app`
- Apple Distribution certificate.
- UDID للآيفون مسجل في Apple Developer.
- Ad Hoc provisioning profile يحتوي جهازك.

أسرار GitHub المطلوبة:
- `APPLE_TEAM_ID`
- `IOS_CERTIFICATE_P12_BASE64`
- `IOS_CERTIFICATE_PASSWORD`
- `IOS_PROVISIONING_PROFILE_BASE64`
- `IOS_PROFILE_NAME`

Repository Variables:
- `WAZEN_BUNDLE_ID`
- `WAZEN_API_BASE_URL`

بعد ضبطها شغّل Workflow:
**WAZEN iOS Ad Hoc IPA**

الـWorkflow ينتج ملف `.ipa` موقّعًا خاصًا بالأجهزة المسجلة في الـprovisioning profile.
