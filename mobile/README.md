# WAZEN Mobile Alpha v6

Flutter Arabic-first mobile client for the WAZEN backend.

## Implemented flow
1. Login / Alpha registration
2. Home dashboard with daily state
3. “شو آكل الحين؟” natural-language craving input
4. Recommendation results from `/api/v1/golden-flow`
5. Food detail from `/api/v1/foods/{food_id}`
6. Add selected food to today using `/api/v1/food-log/from-catalog`
7. Return to Home and refresh remaining calories/macros

## Run
```bash
cd mobile
flutter pub get
flutter run
```

Backend:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API URL notes
- iOS simulator on macOS: `http://127.0.0.1:8000`
- Android emulator: `http://10.0.2.2:8000`
- Physical phone: use the computer's LAN IP, e.g. `http://192.168.1.50:8000`

## Alpha UI principles
- Arabic RTL by default
- No guilt language
- Wazen Match is personalized suitability, not a universal health score
- Source confidence remains visible
- Severe-allergy exclusions remain enforced by backend before ranking

## Environment limitation
The generated project is structurally complete, but Flutter SDK is not installed in the artifact environment used to assemble this package. Backend regression tests are run separately; run `flutter analyze` and `flutter test` on a machine with Flutter installed before deployment.
