import os
import requests
import unicodedata

MSTR_URL = "http://10.14.203.158:8080/SEFADEVLIB/api"
ADMIN_USER = os.environ.get("MSTR_ADMIN_USER", "31071655817")
ADMIN_PASS = os.environ.get("MSTR_ADMIN_PASS", "Tera!7777")


def _norm_abbrev(s: str) -> str:
    if s is None:
        return ''
    s = str(s).strip()
    s = unicodedata.normalize('NFKC', s)
    digits = ''.join(ch for ch in s if ch.isdigit())
    if digits:
        stripped = digits.lstrip('0')
        return stripped if stripped else '0'
    return s.lower()


def _extract_member_id(m):
    if isinstance(m, dict):
        for k in ("id", "Id", "ID", "user", "userId", "user_id", "memberId"):
            v = m.get(k)
            if v is None:
                continue
            if isinstance(v, dict) and v.get("id") is not None:
                return str(v.get("id"))
            return str(v)
        if "user" in m and isinstance(m["user"], dict) and m["user"].get("id"):
            return str(m["user"]["id"])
        return str(m)
    return str(m)


def main():
    login_to_check = "3704886360"
    group_prefix = "200"

    session = requests.Session()
    try:
        r = session.post(f"{MSTR_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print("AUTH ERROR:", e)
        return

    token = r.headers.get("X-MSTR-AuthToken") or r.headers.get('x-mstr-authtoken')
    if not token:
        print("No token returned")
        return
    session.headers.update({"X-MSTR-AuthToken": token, "Accept": "application/json"})

    # find group by prefix
    try:
        grp_resp = session.get(f"{MSTR_URL}/usergroups", params={"limit": "-1", "fields": "id,name"}, timeout=30)
        grp_resp.raise_for_status()
        groups = grp_resp.json()
    except Exception as e:
        print("Failed to get groups:", e)
        return

    def _norm(s: str) -> str:
        if s is None:
            return ""
        s = str(s)
        s = s.replace('"', '').replace("'", '').replace('`', '')
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        s = ' '.join(s.split()).strip().lower()
        return s

    target_group = None
    for g in groups:
        name = g.get('name', '')
        prefix = name.split('-')[0].strip() if '-' in name else name.strip()
        if prefix.startswith(group_prefix):
            target_group = g
            break

    if not target_group:
        print('Group with prefix', group_prefix, 'not found')
        return

    group_id = target_group.get('id')
    print('Found group:', target_group.get('name'), 'id=', group_id)

    # find user id by abbreviation
    try:
        users_resp = session.get(f"{MSTR_URL}/users", params={"limit": "-1", "fields": "id,abbreviation"}, timeout=30)
        users_resp.raise_for_status()
        users = users_resp.json()
    except Exception as e:
        print('Failed to get users:', e)
        return

    users_map = { _norm_abbrev(u.get('abbreviation')): str(u.get('id')) for u in users }
    user_norm = _norm_abbrev(login_to_check)
    user_id = users_map.get(user_norm)
    print('User', login_to_check, 'normalized->', user_norm, 'id=', user_id)

    # get members of group
    try:
        mem_resp = session.get(f"{MSTR_URL}/usergroups/{group_id}/members", timeout=30)
        mem_resp.raise_for_status()
        members = mem_resp.json()
    except Exception as e:
        print('Failed to get members:', e)
        members = []

    parsed = [_extract_member_id(m) for m in members]
    print('Parsed member ids (first 50):', parsed[:50])

    if user_id and str(user_id) in parsed:
        print(f'User {login_to_check} (id={user_id}) IS member according to API response')
    else:
        print(f'User {login_to_check} (id={user_id}) is NOT member according to API response')

    # logout (will be done after additional checks)
    try:
        session.post(f"{MSTR_URL}/auth/logout", timeout=10)
    except Exception:
        pass

    # Additional checks: re-authenticate and fetch user object and try user->groups endpoints
    try:
        # re-auth because previous logout may have invalidated session
        r_auth = session.post(f"{MSTR_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=30)
        r_auth.raise_for_status()
        token2 = r_auth.headers.get("X-MSTR-AuthToken") or r_auth.headers.get('x-mstr-authtoken')
        if token2:
            session.headers.update({"X-MSTR-AuthToken": token2, "Accept": "application/json"})
    except Exception:
        pass

    try:
        if user_id:
            print('\nGET /users/{id} ->')
            ur = session.get(f"{MSTR_URL}/users/{user_id}", timeout=20)
            print('status', ur.status_code)
            try:
                print(ur.json())
            except Exception:
                print(ur.text[:1000])

            for alt in (f"{MSTR_URL}/users/{user_id}/groups", f"{MSTR_URL}/users/{user_id}/usergroups"):
                try:
                    r2 = session.get(alt, timeout=20)
                    print('\nGET', alt, 'status', r2.status_code)
                    try:
                        print(r2.json())
                    except Exception:
                        print(r2.text[:1000])
                except Exception as e:
                    print('Err on', alt, e)
    except Exception:
        pass


if __name__ == '__main__':
    main()
