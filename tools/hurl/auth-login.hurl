# Login smoke for AUTH_MODE=local. Requires a seeded owner account.
# Does not print or persist the token beyond this file's capture scope.
POST {{host}}/auth/login
Content-Type: application/json
{
  "email": "{{email}}",
  "password": "{{password}}"
}
HTTP 200
[Captures]
token: jsonpath "$.access_token"
[Asserts]
jsonpath "$.token_type" == "bearer"
jsonpath "$.email" == "{{email}}"
jsonpath "$.access_token" isString
