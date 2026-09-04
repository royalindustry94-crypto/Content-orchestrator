# Defensive readiness check: local auth must advertise its mode.
GET {{host}}/auth/mode
HTTP 200
[Asserts]
jsonpath "$.auth_mode" exists
