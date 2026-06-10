import secrets
print("SITE SECRET:")
print(secrets.token_urlsafe(48))
print()
print("API SECRET:")
print("DZKP_API_" + secrets.token_hex(32))
