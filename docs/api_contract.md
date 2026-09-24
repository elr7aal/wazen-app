# WAZEN API Contract — Alpha 0.3

Base: `/api/v1`

## Authentication
- `POST /auth/register`
- `POST /auth/login`

Authenticated endpoints use `Authorization: Bearer <token>`.

## User profile
- `GET /users/me`
- `PATCH /users/me`

Stores nutrition targets, budget and severe allergen rules.

## Food log
- `POST /food-log`
- `GET /food-log/today`
- `DELETE /food-log/{log_id}`

Every persisted food-log change updates the user's live daily state.

## Nutrition Today
- `GET /nutrition/today`

Returns persisted totals plus remaining calories/macros.

## Craving Parser
`POST /cravings/parse`

Example:
```json
{"text":"أبي برغر من KFC تحت 600 سعرة"}
```

## Personalized Recommendations
`POST /recommendations/for-me`

Example:
```json
{"vendor":"KFC UAE","category":"BURGERS","max_calories":600}
```

The endpoint automatically uses the authenticated user's food log, nutrition targets, budget and severe allergens.

## Stateless compatibility endpoints
- `POST /daily-state/calculate`
- `POST /recommendations/now`
- `POST /recommendations/make-it-fit`
- `POST /day/rebalance`

These remain useful for isolated engine tests and prototyping.
