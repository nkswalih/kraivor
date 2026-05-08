# Sign-In Module

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/signin/identify/` | POST | Identify user by email |
| `/signin/password/` | POST | Sign in with password |
| `/signin/otp/send/` | POST | Send OTP to email |
| `/signin/otp/verify/` | POST | Verify OTP and return tokens |
| `/refresh/` | POST | Refresh access token |

## Token Management

- **Access Token**: 15-minute expiry, returned in JSON response
- **Refresh Token**: 30-day expiry, HttpOnly cookie

## Security

- Redis lockout: 5 failed attempts → 15 minute lockout
- OTP: 6-digit, 5-minute expiry
- Rate limiting on all auth endpoints