# JWT Authentication Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install djangorestframework-simplejwt
```

Or add to your `requirements.txt`:
```
djangorestframework-simplejwt>=5.3.0
```

### 2. Run Migrations

No migrations needed - JWT uses the existing User model.

### 3. Test the Endpoints

#### Register a User
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "password_confirm": "testpass123"
  }'
```

#### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

#### Use Token in Request
```bash
curl -X GET http://localhost:8000/api/some-endpoint/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Postman Collection

1. Import `JWT_Auth.postman_collection.json` into Postman
2. Set the `base_url` variable to your server URL (default: `http://localhost:8000`)
3. Run "Register User" or "Login" - tokens will be automatically saved to environment variables
4. Use "Example Protected Endpoint" to test authenticated requests

## Configuration

JWT settings are in `klikk_business_intelligence/settings.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # 1 hour
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # 7 days
    # ... more settings
}
```

## View Permissions

All views currently use `AllowAny` - they can be accessed without authentication.

To require authentication for a specific view:

```python
from rest_framework.permissions import IsAuthenticated

class MyView(APIView):
    permission_classes = [IsAuthenticated]  # Requires JWT token
```

## Troubleshooting

### Import Error: No module named 'rest_framework_simplejwt'
**Solution**: Install the package: `pip install djangorestframework-simplejwt`

### 401 Unauthorized
- Check that token is in format: `Authorization: Bearer <token>`
- Verify token hasn't expired (access tokens expire after 1 hour)
- Use refresh token to get new access token

### Token Not Saving in Postman
- Ensure you're using the collection's test scripts
- Check that environment variables are enabled in Postman

## Next Steps

1. Test registration and login endpoints
2. Import Postman collection
3. Update your frontend/client to use JWT tokens
4. Optionally add `IsAuthenticated` to views that need protection

