# Force-change password next sign-in from Excel

This script reads an Excel file with a column containing user logins (userPrincipalName) and marks `forceChangePasswordNextSignIn = true` via Microsoft Graph REST API.

Requirements
- Python 3.8+
- packages: `pandas`, `openpyxl`, `requests`, `msal`

Install:
```powershell
python -m pip install pandas openpyxl requests msal
```

Usage
```powershell
python force_change_next_signin_from_excel.py --excel users.xlsx \
  --login-col login --tenant-id <tenant> --client-id <id> --client-secret <secret> \
  --set-temp-password
```

Options
- `--excel`: path to Excel file.
- `--login-col`: column name with the login (default `login`).
- `--tenant-id`, `--client-id`, `--client-secret`: app registration credentials. Can be provided via env vars `AZ_TENANT_ID`, `AZ_CLIENT_ID`, `AZ_CLIENT_SECRET`.
- `--set-temp-password`: if Graph returns an error requiring a password, the script retries generating a temporary password and sets it (use with caution).
- `--output`: CSV filename for results (default `results_force_change.csv`).
- `--sheet`: sheet name or index if needed.

Permissions
- The calling app needs `User.ReadWrite.All` (Application permission) with admin consent to update users.

Notes
- The script first attempts to set `forceChangePasswordNextSignIn` only. Some tenants may require providing a `password` in the `passwordProfile` when updating; use `--set-temp-password` to retry with a generated temporary password.
- Generated temporary passwords are written in the results CSV only when used. Keep that CSV secure.

Files
- [New_Users/force_change_next_signin_from_excel.py](New_Users/force_change_next_signin_from_excel.py)
