# Authentication Module

## KRV-011: Multi-Step Sign-In

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/signin/identify/` | POST | Identify user by email |
| `/signin/password/` | POST | Sign in with password |
| `/signin/otp/send/` | POST | Send OTP to email |
| `/signin/otp/verify/` | POST | Verify OTP and return tokens |
| `/refresh/` | POST | Refresh access token (KRV-013) |
| `/logout/` | POST | Single device logout |
| `/logout/all/` | POST | All devices logout |

## KRV-013: Refresh Token Rotation

### Security Features

- **Token Rotation**: Every refresh request issues a new refresh token and invalidates the old one
- **Token Hashing**: Refresh tokens are hashed (SHA-256) before storage in database
- **Replay Attack Detection**: If a reused refresh token is detected, ALL active sessions are invalidated
- **Session Management**: Users can revoke individual or all sessions

### Token Flow

1. User signs in with password or OTP
2. Server returns access token (JSON) + refresh token (HttpOnly cookie)
3. On token refresh:
   - Validate refresh token against database
   - Invalidate old refresh token
   - Issue new access + refresh token pair
4. If reused token detected:
   - Invalidate all user sessions
   - Return security alert

### Token Storage

```
RefreshToken Model:
- user: ForeignKey to User
- token_hash: SHA-256 hash of token (not plain token)
- device_id: Device identifier
- ip_address: Client IP
- expires_at: Expiration datetime
- revoked: Boolean flag
```

### Security Headers

Refresh token cookie settings:
- `httponly=True` - Prevents JavaScript access
- `secure=True` - HTTPS only in production
- `samesite=Strict` - CSRF protection
- `path=/auth/` - Auth endpoint scope

## KRV-011: Original Features

### Multi-Step Authentication

1. **Identify**: User submits email, returns next step
2. **Password**: Traditional password verification
3. **OTP**: Time-based one-time password

### Security

- Redis lockout: 5 failed attempts → 15 minute lockout
- OTP: 6-digit, 5-minute expiry
- Rate limiting on all auth endpoints
- Constant-time password comparison
- Device fingerprinting

## Services

| Service | Purpose |
|---------|---------|
| `tokens.py` | Token generation, validation, rotation (KRV-013) |
| `jwt.py` | Legacy JWT utilities (backward compatibility) |
| `otp.py` | OTP generation, storage, verification |
| `security.py` | Login lockout, password verification |
| `jwks.py` | Public key endpoint for JWT verification |

## Token Expiry

- Access Token: 15 minutes
- Refresh Token: 30 days