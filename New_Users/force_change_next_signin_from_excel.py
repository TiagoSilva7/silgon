#!/usr/bin/env python3
"""
Read an Excel file with a column containing user logins and mark
`forceChangePasswordNextSignIn = true` via Microsoft Graph REST API.

Authentication: client credentials (app registration) OR environment variables.

Usage example:
  python force_change_next_signin_from_excel.py --excel users.xlsx \
    --login-col login --tenant-id <tenant> --client-id <id> --client-secret <secret>

Outputs a CSV with results.
"""
import argparse
import csv
import json
import logging
import os
import random
import string
import sys
import time

import pandas as pd
import requests
from msal import ConfidentialClientApplication

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def get_token(tenant_id, client_id, client_secret):
    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret,
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in token:
        raise RuntimeError(f"Failed to acquire token: {token}")
    return token["access_token"]


def generate_temp_password(length=12):
    # ensure complexity: upper, lower, digit, special
    specials = "!@#$%&*()-_=+"
    pwd = [random.choice(string.ascii_uppercase), random.choice(string.ascii_lowercase), random.choice(string.digits), random.choice(specials)]
    while len(pwd) < length:
        pwd.append(random.choice(string.ascii_letters + string.digits + specials))
    random.shuffle(pwd)
    return "".join(pwd)


def patch_user_force_change(token, user_principal_name, temp_password=None, timeout=10):
    url = f"{GRAPH_BASE}/users/{user_principal_name}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"passwordProfile": {"forceChangePasswordNextSignIn": True}}
    if temp_password:
        body["passwordProfile"]["password"] = temp_password
    r = requests.patch(url, headers=headers, data=json.dumps(body), timeout=timeout)
    return r


def process_excel(path, login_col, token, set_temp_password=False, output_csv="results_force_change.csv", sheet_name=None):
    df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    if login_col not in df.columns:
        raise ValueError(f"Column '{login_col}' not found in Excel. Available columns: {list(df.columns)}")

    logins = df[login_col].dropna().astype(str).str.strip().unique()
    results = []
    for login in logins:
        try:
            r = patch_user_force_change(token, login)
        except Exception as ex:
            results.append({"login": login, "status": "error", "detail": str(ex), "temp_password": ""})
            continue

        if r.status_code in (204, 200):
            results.append({"login": login, "status": "success", "detail": "forceChange marked, no password changed", "temp_password": ""})
            continue

        # If server requires a password when updating passwordProfile, optionally retry with a temp password
        if r.status_code >= 400 and set_temp_password:
            temp = generate_temp_password()
            try:
                r2 = patch_user_force_change(token, login, temp_password=temp)
            except Exception as ex:
                results.append({"login": login, "status": "error", "detail": f"retry failed: {ex}", "temp_password": ""})
                continue
            if r2.status_code in (200, 204):
                results.append({"login": login, "status": "success", "detail": "forceChange set with temp password", "temp_password": temp})
            else:
                detail = f"first:{r.status_code}:{r.text} second:{r2.status_code}:{r2.text}"
                results.append({"login": login, "status": "error", "detail": detail, "temp_password": ""})
        else:
            results.append({"login": login, "status": "error", "detail": f"{r.status_code}:{r.text}", "temp_password": ""})

        # be kind to the API
        time.sleep(0.15)

    # write results
    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["login", "status", "detail", "temp_password"])
        writer.writeheader()
        writer.writerows(results)

    return results


def main():
    parser = argparse.ArgumentParser(description="Force change password next sign-in for users listed in an Excel file")
    parser.add_argument("--excel", required=True, help="Path to Excel file")
    parser.add_argument("--sheet", default=None, help="Sheet name or index (optional)")
    parser.add_argument("--login-col", default="login", help="Column name that contains user principal name/login")
    parser.add_argument("--tenant-id", default=os.getenv("AZ_TENANT_ID"), help="Azure tenant id (or env AZ_TENANT_ID)")
    parser.add_argument("--client-id", default=os.getenv("AZ_CLIENT_ID"), help="Client (app) id (or env AZ_CLIENT_ID)")
    parser.add_argument("--client-secret", default=os.getenv("AZ_CLIENT_SECRET"), help="Client secret (or env AZ_CLIENT_SECRET)")
    parser.add_argument("--set-temp-password", action="store_true", help="If API requires a password when updating, retry with generated temp password")
    parser.add_argument("--output", default="results_force_change.csv", help="Output CSV file for results")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if not args.tenant_id or not args.client_id or not args.client_secret:
        print("Missing tenant/client credentials. Pass via args or set AZ_TENANT_ID, AZ_CLIENT_ID, AZ_CLIENT_SECRET env vars.")
        sys.exit(1)

    token = get_token(args.tenant_id, args.client_id, args.client_secret)
    print("Acquired access token, processing Excel...")
    results = process_excel(args.excel, args.login_col, token, set_temp_password=args.set_temp_password, output_csv=args.output, sheet_name=args.sheet)
    success = sum(1 for r in results if r["status"] == "success")
    failures = len(results) - success
    print(f"Done. Success: {success}, Failures: {failures}. See {args.output}")


if __name__ == "__main__":
    main()
