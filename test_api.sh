#!/bin/bash
# test_api.sh — Diagnose API authentication failures

API="https://api.simplylovely.ng/api"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc4MDA3MTYyMywianRpIjoiMWMyMmI3YTYtZWIyMi00OTJjLWEzZjctODMxYWQxMDlhNDA5IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6ImphbWVzY2hyaXN0bzk2MkBnbWFpbC5jb20iLCJuYmYiOjE3ODAwNzE2MjMsImNzcmYiOiJiYzhlMDY3MC1iMWRjLTQxZTItYjBkMi1hOTcwNTJkMzc0NTciLCJleHAiOjE3ODA5MzU2MjMsImlkIjoxLCJuYW1lIjoiZGV2ZWxvcGVyIiwidXNlcm5hbWUiOiJkZXZlbG9wZXIiLCJlbWFpbCI6ImphbWVzY2hyaXN0bzk2MkBnbWFpbC5jb20iLCJwaG9uZSI6IjA3MDI2NTYxMzI3IiwiYWJvdXRfbWUiOm51bGwsImNyZWF0ZWRfYXQiOiJTYXQsIDA4IEZlYiAyMDI1IDE3OjMzOjQxIEdNVCIsInVwZGF0ZWRfYXQiOiJTYXQsIDA4IEZlYiAyMDI1IDE4OjI3OjI2IEdNVCIsInN1YnNjcmlwdGlvbnMiOlt7ImlkIjoyLCJzdGF0dXMiOiJhY3RpdmUiLCJ0b3RhbF91bml0cyI6MTkwLCJuYW1lIjoiRkFNSUxZIFBMQU4gMiIsImNyZWF0ZWRfYXQiOiJXZWQsIDI2IEZlYiAyMDI1IDA4OjQ4OjUyIEdNVCJ9XSwicm9sZXMiOlsiZGV2IiwiYWRtaW4iXSwidG9rZW5fdHlwZSI6ImFjY2VzcyJ9.RwHtjUbKM5NgLYUEzFn4jcZ05a_2guFakYTUcKBStQc"

echo "=========================================="
echo "API Diagnostic Script"
echo "API: $API"
echo "Token length: ${#TOKEN}"
echo "=========================================="
echo ""

# Test 1: Public endpoint (no auth)
echo ">>> TEST 1: GET /plans (public, no auth)"
curl -s -w "\nHTTP_CODE: %{http_code}\nTIME: %{time_total}s\n" \
  --max-time 10 \
  "$API/plans" | head -20
echo ""

# Test 2: Authenticated endpoint — users/current
echo ">>> TEST 2: GET /users/current (with Bearer token)"
curl -s -w "\nHTTP_CODE: %{http_code}\nTIME: %{time_total}s\n" \
  --max-time 10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$API/users/current" | head -30
echo ""

# Test 3: Authenticated endpoint — usage/statistics
echo ">>> TEST 3: GET /usage/statistics (with Bearer token)"
curl -s -w "\nHTTP_CODE: %{http_code}\nTIME: %{time_total}s\n" \
  --max-time 10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$API/usage/statistics" | head -30
echo ""

# Test 4: Authenticated endpoint — users list
echo ">>> TEST 4: GET /users?page=1&page_size=10 (with Bearer token)"
curl -s -w "\nHTTP_CODE: %{http_code}\nTIME: %{time_total}s\n" \
  --max-time 10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$API/users?page=1&page_size=10" | head -30
echo ""

# Test 5: Authenticated endpoint — user subscriptions
echo ">>> TEST 5: GET /user/subscriptions/detailed (with Bearer token)"
curl -s -w "\nHTTP_CODE: %{http_code}\nTIME: %{time_total}s\n" \
  --max-time 10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$API/user/subscriptions/detailed?page=1&per_page=6" | head -30
echo ""

# Test 6: Decode token payload (diagnostic only)
echo ">>> TEST 6: Token payload decode"
echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Could not decode"
echo ""

# Test 7: Check if token is expired
echo ">>> TEST 7: Token expiry check"
EXP=$(echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('exp','no exp'))")
NOW=$(date +%s)
if [ "$EXP" != "no exp" ] && [ "$EXP" -lt "$NOW" ]; then
  echo "TOKEN IS EXPIRED! exp=$EXP, now=$NOW"
elif [ "$EXP" != "no exp" ]; then
  echo "Token valid. exp=$EXP, now=$NOW, diff=$((EXP - NOW))s remaining"
else
  echo "No exp claim found"
fi
echo ""

echo "=========================================="
echo "Done. Check HTTP_CODE lines above."
echo "200 = OK | 401/422 = Auth issue | 500 = Server crash | 000 = Network timeout"
echo "=========================================="