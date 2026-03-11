# change_mstr_password.py
import os
import requests
import smtplib
from email.message import EmailMessage

# Configuration (can be set via environment variables)
MSTR_BASE = os.getenv("MSTR_BASE", "https://mstr-host:8443")
MSTR_ADMIN_USER = os.getenv("MSTR_ADMIN_USER", "admin")
MSTR_ADMIN_PASS = os.getenv("MSTR_ADMIN_PASS", "adminpass")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "no-reply@example.com")
SEND_PASSWORD_IN_EMAIL = os.getenv("SEND_PASSWORD_IN_EMAIL", "true").lower() in ("1", "true", "yes")

HEADERS = {"Content-Type": "application/json"}


def login():
    url = f"{MSTR_BASE}/api/auth/login"
    payload = {"username": MSTR_ADMIN_USER, "password": MSTR_ADMIN_PASS, "loginMode": 1}
    s = requests.Session()
    r = s.post(url, json=payload, headers=HEADERS, verify=True)
    r.raise_for_status()
    token = r.headers.get("X-MSTR-AuthToken")
    if token:
        s.headers.update({"X-MSTR-AuthToken": token})
    return s


def find_user(session, login_name):
    url = f"{MSTR_BASE}/api/users?loginName={login_name}"
    r = session.get(url)
    r.raise_for_status()
    data = r.json()
    users = data.get("users") or data.get("result") or data
    if isinstance(users, list) and users:
        return users[0]
    return None


def change_password(session, user_id, new_password):
    url = f"{MSTR_BASE}/api/users/{user_id}/password"
    payload = {"password": new_password}
    r = session.post(url, json=payload)
    if r.status_code not in (200, 204):
        r.raise_for_status()
    return True


def update_user_flags(session, user_id, enabled=True, force_change=True):
    url = f"{MSTR_BASE}/api/users/{user_id}"
    payload = {"isEnabled": enabled, "mustChangePassword": force_change}
    r = session.patch(url, json=payload)
    if r.status_code not in (200, 204):
        r.raise_for_status()
    return True


def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        if SMTP_USER and SMTP_PASS:
            smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)


def main(target_login, new_password, user_email):
    session = login()
    user = find_user(session, target_login)
    if not user:
        raise SystemExit("Usuário não encontrado. Verifique o login e a API.")
    user_id = user.get("id") or user.get("userId") or user.get("uid")
    if not user_id:
        raise SystemExit("Não foi possível obter user id do resultado da API.")
    change_password(session, user_id, new_password)
    update_user_flags(session, user_id, enabled=True, force_change=True)
    subject = "Senha alterada - MicroStrategy"
    if SEND_PASSWORD_IN_EMAIL:
        body = (
            f"Olá,\n\nSua senha foi alterada para: {new_password}\n"
            "Ao acessar pela primeira vez, será solicitado que altere a senha.\n\nAtenciosamente."
        )
    else:
        body = (
            "Olá,\n\nSua senha foi alterada. Por segurança a senha não foi enviada por email."
            "\nAo acessar pela primeira vez, será solicitado que altere a senha.\n\nAtenciosamente."
        )
    send_email(user_email, subject, body)
    print("Senha alterada, usuário habilitado e email enviado.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("login", help="login do usuário MicroStrategy")
    p.add_argument("new_password", help="nova senha")
    p.add_argument("email", help="email do usuário para notificação")
    args = p.parse_args()
    main(args.login, args.new_password, args.email)
