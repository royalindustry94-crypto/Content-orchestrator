# Human Review Gate list: membership-scoped, never auto-publishes.
# Requires token + workspace_id from a prior authenticated session.
GET {{host}}/workspaces/{{workspace_id}}/review-gates
Authorization: Bearer {{token}}
HTTP 200
[Asserts]
jsonpath "$" isCollection
