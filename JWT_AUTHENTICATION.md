# JWT Authentication Guide

## Overview

This application uses **JWT (JSON Web Tokens)** for authentication. JWT tokens provide a stateless, secure way to authenticate API requests without requiring server-side session storage.

## Installation

The JWT authentication is already configured. If you need to install dependencies:

```bash
pip install djangorestframework-simplejwt
```

## API Endpoints

### Base URL
All authentication endpoints are prefixed with `/api/auth/`

### 1. User Registration

**Endpoint:** `POST /api/auth/register/`

**Description:** Creates a new user account and returns JWT tokens.

**Request Body:**
```json
{
    "username": "user123",
    "email": "user@example.com",
    "password": "securepassword123",
    "password_confirm": "securepassword123",
    "first_name": "John",  // Optional
    "last_name": "Doe"      // Optional
}
```

**Success Response (201 Created):**
```json
{
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "username": "user123",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    },
    "tokens": {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
}
```

**Error Responses:**
- `400 Bad Request`: Missing required fields, passwords don't match, username/email already exists, weak password
- `500 Internal Server Error`: Server error during user creation

### 2. User Login

**Endpoint:** `POST /api/auth/login/`

**Description:** Authenticates user credentials and returns JWT tokens.

**Request Body:**
```json
{
    "username": "user123",  // or "email": "user@example.com"
    "password": "securepassword123"
}
```

**Note:** You can use either `username` or `email` field to login.

**Success Response (200 OK):**
```json
{
    "message": "Login successful",
    "user": {
        "id": 1,
        "username": "user123",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    },
    "tokens": {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
}
```

**Error Responses:**
- `400 Bad Request`: Missing username/email or password
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: User account is inactive

### 3. Refresh Access Token

**Endpoint:** `POST /api/auth/refresh/`

**Description:** Refreshes an expired access token using a valid refresh token.

**Request Body:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Success Response (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Error Responses:**
- `400 Bad Request`: Missing refresh token
- `401 Unauthorized`: Invalid or expired refresh token

### 4. Verify Token (Built-in)

**Endpoint:** `POST /api/auth/token/verify/`

**Description:** Verifies if a token is valid.

**Request Body:**
```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Success Response (200 OK):**
```json
{}
```

**Error Response (401 Unauthorized):**
```json
{
    "detail": "Token is invalid or expired"
}
```

## Using JWT Tokens in API Requests

### Authorization Header

Include the JWT access token in the `Authorization` header of your requests:

```
Authorization: Bearer <access_token>
```

### Example cURL Request

```bash
curl -X GET http://localhost:8000/api/some-endpoint/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Example Python Request

```python
import requests

headers = {
    'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...'
}

response = requests.get('http://localhost:8000/api/some-endpoint/', headers=headers)
```

### Example JavaScript/Fetch

```javascript
fetch('http://localhost:8000/api/some-endpoint/', {
    method: 'GET',
    headers: {
        'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...',
        'Content-Type': 'application/json'
    }
})
.then(response => response.json())
.then(data => console.log(data));
```

## Token Lifetime

- **Access Token**: Valid for **1 hour** (60 minutes)
- **Refresh Token**: Valid for **7 days**

When the access token expires, use the refresh token to get a new access token.

## Token Refresh Flow

1. User logs in → Receives `access` and `refresh` tokens
2. Use `access` token for API requests
3. When `access` token expires (after 1 hour):
   - Call `/api/auth/refresh/` with the `refresh` token
   - Receive a new `access` token
   - Continue using the new `access` token
4. When `refresh` token expires (after 7 days):
   - User must login again

## View Permissions

**Important:** All views currently use `AllowAny` permission class, meaning they can be accessed without authentication. This is intentional for development/testing purposes.

To require authentication for specific views, add:

```python
from rest_framework.permissions import IsAuthenticated

class MyView(APIView):
    permission_classes = [IsAuthenticated]  # Requires JWT token
    # ...
```

## Security Best Practices

1. **Store tokens securely**: Never store tokens in localStorage if your app is vulnerable to XSS attacks. Consider httpOnly cookies for web apps.

2. **Use HTTPS**: Always use HTTPS in production to protect tokens in transit.

3. **Token expiration**: Access tokens expire after 1 hour. Implement automatic token refresh in your client application.

4. **Refresh token rotation**: The app is configured to rotate refresh tokens, meaning old refresh tokens are blacklisted after use.

5. **Password requirements**: Passwords must meet Django's password validators:
   - Minimum length (default: 8 characters)
   - Not too similar to user attributes
   - Not a common password
   - Not entirely numeric

## Error Handling

### Common Errors

| Status Code | Error | Description |
|------------|-------|-------------|
| 400 | Bad Request | Missing required fields, validation errors |
| 401 | Unauthorized | Invalid credentials or expired token |
| 403 | Forbidden | User account is inactive |
| 500 | Internal Server Error | Server error |

### Error Response Format

```json
{
    "error": "Error message here",
    "details": ["Additional error details"]  // Optional
}
```

## Testing

### Using Postman

See the included Postman collection (`JWT_Auth.postman_collection.json`) for pre-configured requests.

### Using Django Shell

```python
from apps.user.models import User
from rest_framework_simplejwt.tokens import RefreshToken

# Create a user
user = User.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='testpass123'
)

# Generate tokens
refresh = RefreshToken.for_user(user)
print(f"Access Token: {refresh.access_token}")
print(f"Refresh Token: {refresh}")
```

## Configuration

JWT settings are configured in `settings.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    # ... more settings
}
```

To modify token lifetimes or other settings, edit the `SIMPLE_JWT` dictionary in `settings.py`.

## Migration from Token Authentication

If you're migrating from the old token authentication:

1. **Old endpoint**: `POST /api-token-auth/` (still available for backward compatibility)
2. **New endpoint**: `POST /api/auth/login/` (returns JWT tokens)

Both authentication methods are supported simultaneously. Views can accept either:
- Old token: `Authorization: Token <token>`
- JWT token: `Authorization: Bearer <jwt_token>`

## Django Admin Access

**Important**: Users created via the registration API are **regular users** by default and **cannot log into Django admin**. 

To grant admin access to a user:

### Option 1: Using Management Command (Recommended)

```bash
# Grant staff status (allows admin login)
python manage.py promote_user <username> --staff

# Grant superuser status (all permissions)
python manage.py promote_user <username> --superuser

# Grant both
python manage.py promote_user <username> --staff --superuser
```

### Option 2: Using Django Admin

1. Log into Django admin with a superuser account
2. Go to Users section
3. Find the user and edit
4. Check "Staff status" checkbox
5. Optionally check "Superuser status" for full permissions
6. Save

### Option 3: Using Django Shell

```python
from apps.user.models import User

user = User.objects.get(username='your_username')
user.is_staff = True  # Allows admin login
user.is_superuser = True  # Optional: gives all permissions
user.save()
```

## Troubleshooting

### Cannot Log into Django Admin
**Problem**: User created via API cannot log into Django admin console

**Solution**: Users created via registration API don't have `is_staff=True` by default. Use one of the methods above to promote the user:
```bash
python manage.py promote_user <username> --staff
```

### Token Expired
**Error**: `401 Unauthorized` with message about expired token

**Solution**: Use the refresh token to get a new access token:
```bash
POST /api/auth/refresh/
{
    "refresh": "your_refresh_token"
}
```

### Invalid Token Format
**Error**: `401 Unauthorized` with authentication failed

**Solution**: Ensure you're using the correct header format:
```
Authorization: Bearer <token>
```
Not:
```
Authorization: Token <token>  # This is for old token auth
```

### User Not Found
**Error**: `401 Unauthorized` with invalid credentials

**Solution**: 
- Verify username/email and password are correct
- Check if user account is active (`is_active=True`)
- Ensure user exists in database

## Additional Resources

- [djangorestframework-simplejwt Documentation](https://django-rest-framework-simplejwt.readthedocs.io/)
- [JWT.io](https://jwt.io/) - JWT token decoder and debugger
- [Django REST Framework Authentication](https://www.django-rest-framework.org/api-guide/authentication/)

