#!/usr/bin/env python3
"""
Para cada login (abreviação) em um arquivo Excel, consulta a API do
Strategy/MicroStrategy e, quando a API informar `enabled == false`, marca
essa linha no próprio Excel como `enabled = True`.

Uso:
  python update_enabled_excel.py --excel PATH

Opções:
  --no-backup   : não criar backup PATH.bak
  --no-auth     : não tentar autenticar antes das consultas

Observações:
  - O login é lido preferencialmente da coluna `abbreviation`, ou de
	`login`/`username`. Se nenhuma existir, usa a primeira coluna.
  - O script altera apenas o arquivo Excel; não muda nada na API.
"""
from __future__ import annotations
import argparse
import os
import shutil
import unicodedata
from typing import Optional, Tuple

import pandas as pd
import requests

# --- CONFIGURAÇÃO ---
BASE_URL = "http://10.14.203.158:8080/SEFAPRODLIB/api"
API_USER = "31071655817"
API_PASS = "Tera!7777"
DEFAULT_EXCEL = "Lista_Oficial_att_new_groups.xlsx"  # arquivo padrão na mesma pasta


def _normalize_col(name: str) -> str:
	name = str(name).strip().lower().replace(" ", "_")
	return ''.join(
		c for c in unicodedata.normalize('NFD', name)
		if unicodedata.category(c) != 'Mn'
	)


def normalize_login_value(s: str) -> str:
	if s is None:
		return ''
	s = str(s)
	s = unicodedata.normalize('NFKC', s)
	s = s.replace('\u00A0', ' ').replace('\u200B', '')
	s = s.strip()
	digits = ''.join(ch for ch in s if ch.isdigit())
	if digits:
		stripped = digits.lstrip('0')
		return stripped if stripped else '0'
	return s


def auth_get_token(session: requests.Session) -> Optional[str]:
	try:
		r = session.post(f"{BASE_URL.rstrip('/')}/auth/login",
						 json={"username": API_USER, "password": API_PASS}, timeout=12)
		if r.status_code in (200, 204):
			return r.headers.get('X-MSTR-AuthToken') or r.headers.get('x-mstr-authtoken')
	except Exception:
		pass
	return None


def find_user_by_abbreviation(session: requests.Session, abbreviation: str) -> Optional[dict]:
	try:
		target = normalize_login_value(abbreviation)
		r = session.get(f"{BASE_URL.rstrip('/')}/users", params={"searchPattern": target}, timeout=12)
		if r.status_code == 200:
			data = r.json()
			items = data if isinstance(data, list) else data.get('users') or data.get('items') or []
			for u in items:
				cand = str(u.get('abbreviation') or u.get('login') or u.get('username') or '')
				if normalize_login_value(cand) == target:
					return u
		r2 = session.get(f"{BASE_URL.rstrip('/')}/users", params={"search": target}, timeout=10)
		if r2.status_code == 200:
			data2 = r2.json()
			items2 = data2 if isinstance(data2, list) else data2.get('users') or data2.get('items') or []
			for u in items2:
				cand = str(u.get('abbreviation') or u.get('login') or u.get('username') or '')
				if normalize_login_value(cand) == target:
					return u
	except Exception:
		pass
	return None


def fetch_enabled_from_user_obj(session: requests.Session, user_obj: dict) -> Optional[bool]:
	if not user_obj:
		return None
	if 'enabled' in user_obj:
		return bool(user_obj.get('enabled'))
	user_id = user_obj.get('id') or user_obj.get('userId')
	if not user_id:
		return None
	try:
		r = session.get(f"{BASE_URL.rstrip('/')}/users/{user_id}", params={'fields': 'enabled'}, timeout=10)
		if r.status_code == 200:
			d = r.json()
			return bool(d.get('enabled')) if 'enabled' in d else None
	except Exception:
		pass
	return None


def update_user_enabled(session: requests.Session, user_id: str) -> bool:
	"""Atualiza usuário no Strategy definindo `enabled` para True.
	Retorna True se a API reportar sucesso.
	"""
	payload = {
		'operationList': [
			{
				'op': 'replace',
				'path': '/enabled',
				'value': True
			}
		]
	}
	headers = {'Content-Type': 'application/json'}
	try:
		r = session.patch(f"{BASE_URL.rstrip('/')}/users/{user_id}", json=payload, headers=headers, timeout=12)
		if r.status_code in (200, 204, 201, 202):
			return True
		# on failure, try to log response text for troubleshooting
		try:
			resp_text = r.text
		except Exception:
			resp_text = ''
		print(f"PATCH /users/{user_id} returned {r.status_code}: {resp_text}")
	except Exception as e:
		print(f"Erro ao chamar PATCH /users/{user_id}: {e}")
	return False


def process_file(path: str, backup: bool = True, try_auth: bool = True) -> Tuple[int, int, int, int, str]:
	"""Lê o Excel (apenas um arquivo), itera pelos logins (abbreviation),
	consulta a API e, quando necessário, atualiza o usuário via REST e
	escreve True no Excel.

	Retorna: (total_rows, matched_in_api, updated_api_count, updated_excel_count)
	"""
	if backup:
		shutil.copy2(path, path + '.bak')

	df = pd.read_excel(path, dtype=object)
	df.rename(columns=lambda c: _normalize_col(c), inplace=True)

	login_col = None
	for cand in ('abbreviation', 'login', 'username', 'user'):
		if cand in df.columns:
			login_col = cand
			break
	if login_col is None:
		login_col = df.columns[0]

	enabled_col = None
	for c in df.columns:
		if c == 'enabled' or c.endswith('enabled') or c.endswith('_enabled'):
			enabled_col = c
			break
	if enabled_col is None:
		df['enabled'] = False
		enabled_col = 'enabled'

	# construir lista de logins primeiro (leitura do Excel)
	logins = []
	for _, row in df.iterrows():
		raw_login = row.get(login_col)
		if pd.isna(raw_login) or str(raw_login).strip() == '':
			continue
		logins.append(str(raw_login).strip())

	session = requests.Session()
	token = None
	if try_auth:
		token = auth_get_token(session)
	if token:
		session.headers.update({'X-MSTR-AuthToken': token, 'Accept': 'application/json'})

	total = len(df)
	matched = 0
	updated_api = 0
	updated_excel = 0

	# preparar arquivo de log (no mesmo diretório do Excel)
	base, _ = os.path.splitext(path)
	log_path = base + '_update_log.txt'
	log_fp = open(log_path, 'w', encoding='utf-8')

	# iterar pelos logins e atuar via API
	for abbrev in logins:
		user_obj = find_user_by_abbreviation(session, abbrev)
		if not user_obj:
			line = f"{abbrev}: NÃO encontrado na API"
			print(line)
			log_fp.write(line + '\n')
			continue
		matched += 1

		# obter nome e status atual (preferir dados já retornados)
		name = user_obj.get('name') or user_obj.get('fullName') or ''
		enabled = fetch_enabled_from_user_obj(session, user_obj)
		before = enabled

		if enabled is False:
			user_id = user_obj.get('id') or user_obj.get('userId')
			if not user_id:
				line = f"{abbrev} | {name} | sem user id"
				print(line)
				log_fp.write(line + '\n')
				continue
			ok = update_user_enabled(session, user_id)
			if ok:
				updated_api += 1
				# refletir alteração no dataframe (todas as linhas com esse abbrev)
				for idx, row in df.iterrows():
					raw_login = row.get(login_col)
					if pd.isna(raw_login):
						continue
					if str(raw_login).strip() == abbrev:
						if not bool(row.get(enabled_col)):
							df.at[idx, enabled_col] = True
							updated_excel += 1
				line = f"{abbrev} | {name} | antes: {before} -> depois: True (API OK)"
				print(line)
				log_fp.write(line + '\n')
			else:
				line = f"{abbrev} | {name} | antes: {before} -> tentativa de update NAO teve sucesso na API"
				print(line)
				log_fp.write(line + '\n')
		elif enabled is True:
			line = f"{abbrev} | {name} | já habilitado: True (nenhuma alteração)"
			print(line)
			log_fp.write(line + '\n')
		else:
			# enabled pode ser None se não retornado
			line = f"{abbrev} | {name} | status desconhecido (não atualizado)"
			print(line)
			log_fp.write(line + '\n')

	# salvar alterações no Excel
	df.to_excel(path, index=False)
	# escrever sumário e fechar log
	summary_lines = [
		f"Total linhas no Excel: {total}",
		f"Logins encontrados na API: {matched}",
		f"Usuários atualizados via API: {updated_api}",
		f"Entradas atualizadas no Excel: {updated_excel}",
	]
	for l in summary_lines:
		print(l)
		log_fp.write(l + '\n')
	log_fp.close()

	return total, matched, updated_api, updated_excel, log_path


def main():
	parser = argparse.ArgumentParser(description='Verifica enabled na API e atualiza o Excel quando necessário.')
	parser.add_argument('--excel', '-e', required=False, help=f'Arquivo Excel único a ser processado (padrão: {DEFAULT_EXCEL})')
	parser.add_argument('--no-backup', dest='backup', action='store_false', help='Não criar backup .bak')
	parser.add_argument('--no-auth', dest='auth', action='store_false', help='Não tentar autenticar no Strategy')
	args = parser.parse_args()

	excel_path = args.excel or DEFAULT_EXCEL
	if not os.path.isabs(excel_path):
		script_dir = os.path.dirname(os.path.abspath(__file__))
		excel_path = os.path.join(script_dir, excel_path)
	if not os.path.exists(excel_path):
		print(f'Arquivo não encontrado: {excel_path}')
		return

	print(f'Processando: {excel_path}')
	total, matched, updated_api, updated_excel, log_path = process_file(excel_path, backup=args.backup, try_auth=args.auth)
	print(f'Total linhas no Excel: {total}')
	print(f'Logins encontrados na API: {matched}')
	print(f'Usuários atualizados via API: {updated_api}')
	print(f'Entradas atualizadas no Excel: {updated_excel}')
	print(f'Log salvo em: {log_path}')


if __name__ == '__main__':
	main()


