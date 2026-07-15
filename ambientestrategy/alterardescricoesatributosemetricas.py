import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACOES DE AMBIENTE ---
BASE_URL = "http://10.14.203.158:8080/SEFADEVLIB/api"
PROJECT_ID = "239BC40211E8B1E3626F0080EF95EED2"
USERNAME = "31071655817"
PASSWORD = "Tera!7777"

ATTRIBUTE_TYPE = 12
METRIC_TYPE = 4

DEFAULT_TIMEOUT = 60
INPUT_FILE = Path(__file__).with_name("listagem_objetos_strategy_alteracoes.xlsx")
LOG_FILE = Path(__file__).with_name("log_alteracoes_descricoes.xlsx")
VALID_SHEETS = {
	"atributos": ("Atributo", ATTRIBUTE_TYPE),
	"metricas": ("Metrica", METRIC_TYPE),
}


@dataclass(frozen=True)
class ExcelObjectRow:
	sheet_name: str
	object_type_label: str
	object_type_id: int
	object_id: str
	name: str
	description: str


@dataclass(frozen=True)
class UpdateLogRow:
	status: str
	object_type_label: str
	object_id: str
	name: str
	action: str
	previous_description: str
	new_description: str
	detail: str

	def to_row(self) -> Dict[str, str]:
		return {
			"Status": self.status,
			"Tipo do objeto": self.object_type_label,
			"ID do objeto": self.object_id,
			"Nome do objeto": self.name,
			"Acao": self.action,
			"Descricao anterior": self.previous_description,
			"Descricao nova": self.new_description,
			"Detalhe": self.detail,
		}


class MstrClient:
	def __init__(
		self,
		base_url: str,
		project_id: str,
		username: str,
		password: str,
		timeout: int = DEFAULT_TIMEOUT,
	) -> None:
		self.base_url = base_url.rstrip("/")
		self.project_id = project_id
		self.username = username
		self.password = password
		self.timeout = timeout
		self.session = requests.Session()
		self.session.verify = False

	def login(self) -> None:
		payload = {
			"username": self.username,
			"password": self.password,
			"loginMode": 1,
		}
		response = self.session.post(
			f"{self.base_url}/auth/login",
			json=payload,
			timeout=self.timeout,
		)
		response.raise_for_status()

		auth_token = response.headers.get("X-MSTR-AuthToken")
		if not auth_token:
			raise RuntimeError("A autenticacao nao retornou o cabecalho X-MSTR-AuthToken.")

		self.session.headers.update(
			{
				"X-MSTR-AuthToken": auth_token,
				"X-MSTR-ProjectID": self.project_id,
				"Accept": "application/json",
				"Content-Type": "application/json",
			}
		)

	def logout(self) -> None:
		try:
			self.session.post(f"{self.base_url}/auth/logout", timeout=self.timeout)
		except requests.RequestException:
			pass
		finally:
			self.session.close()

	def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
		response = self.session.get(
			f"{self.base_url}{endpoint}",
			timeout=kwargs.pop("timeout", self.timeout),
			**kwargs,
		)
		response.raise_for_status()
		return response

	def patch(self, endpoint: str, **kwargs: Any) -> requests.Response:
		response = self.session.patch(
			f"{self.base_url}{endpoint}",
			timeout=kwargs.pop("timeout", self.timeout),
			**kwargs,
		)
		return response

	def put(self, endpoint: str, **kwargs: Any) -> requests.Response:
		response = self.session.put(
			f"{self.base_url}{endpoint}",
			timeout=kwargs.pop("timeout", self.timeout),
			**kwargs,
		)
		return response


def normalize_column_name(name: str) -> str:
	return (
		str(name)
		.strip()
		.lower()
		.replace(" ", "_")
		.replace("ç", "c")
		.replace("ã", "a")
		.replace("á", "a")
		.replace("â", "a")
		.replace("é", "e")
		.replace("ê", "e")
		.replace("í", "i")
		.replace("ó", "o")
		.replace("ô", "o")
		.replace("õ", "o")
		.replace("ú", "u")
	)


def first_non_empty(row: pd.Series, candidates: Iterable[str]) -> str:
	for candidate in candidates:
		if candidate in row and pd.notna(row[candidate]):
			value = str(row[candidate]).strip()
			if value and value.lower() != "nan":
				return value
	return ""


def load_excel_rows(input_file: Path) -> List[ExcelObjectRow]:
	if not input_file.exists():
		raise FileNotFoundError(f"Arquivo Excel nao encontrado: {input_file}")

	worksheets = pd.read_excel(input_file, sheet_name=None)
	rows: List[ExcelObjectRow] = []

	for original_sheet_name, dataframe in worksheets.items():
		sheet_name = normalize_column_name(original_sheet_name)
		if sheet_name not in VALID_SHEETS:
			continue

		object_type_label, object_type_id = VALID_SHEETS[sheet_name]
		dataframe = dataframe.copy()
		dataframe.rename(columns=lambda value: normalize_column_name(value), inplace=True)

		for _, row in dataframe.iterrows():
			object_id = first_non_empty(row, ("id_do_objeto", "id"))
			name = first_non_empty(row, ("nome_do_objeto", "nome", "name"))
			description = first_non_empty(
				row,
				("descricao_do_objeto", "descricao", "description", "desc"),
			)

			if not object_id:
				continue

			rows.append(
				ExcelObjectRow(
					sheet_name=sheet_name,
					object_type_label=object_type_label,
					object_type_id=object_type_id,
					object_id=object_id,
					name=name,
					description=description,
				)
			)

	if not rows:
		raise RuntimeError(
			"Nenhuma linha valida foi encontrada nas abas 'atributos' e 'metricas' do Excel."
		)

	return rows


def extract_description(payload: Dict[str, Any]) -> str:
	for key in ("description", "desc", "information", "comments"):
		value = payload.get(key)
		if isinstance(value, str) and value.strip():
			return value.strip()
	return ""


def extract_name(payload: Dict[str, Any]) -> str:
	value = payload.get("name")
	if isinstance(value, str):
		return value.strip()
	return ""


def get_object(client: MstrClient, object_id: str, object_type: int) -> Dict[str, Any]:
	response = client.get(f"/objects/{object_id}", params={"type": object_type})
	payload = response.json()
	if not isinstance(payload, dict):
		raise RuntimeError(f"Resposta invalida ao buscar objeto {object_id}.")
	return payload


def build_operation_paths(payload: Dict[str, Any]) -> List[str]:
	candidate_paths: List[str] = []
	for key in payload.keys():
		lower_key = key.lower()
		if any(token in lower_key for token in ("desc", "comment", "information")):
			candidate_paths.append(f"/{key}")

	properties = payload.get("properties")
	if isinstance(properties, dict):
		for key in properties.keys():
			lower_key = key.lower()
			if any(token in lower_key for token in ("desc", "comment", "information")):
				candidate_paths.append(f"/properties/{key}")

	for fallback in ("/description", "/desc", "/comments", "/information"):
		if fallback not in candidate_paths:
			candidate_paths.append(fallback)

	return candidate_paths


def patch_object_description(
	client: MstrClient,
	object_id: str,
	object_type: int,
	new_description: str,
	payload: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
	direct_payloads = [
		{"description": new_description},
		{"desc": new_description},
		{"comments": new_description},
		{"information": new_description},
	]

	for patch_body in direct_payloads:
		response = client.put(f"/objects/{object_id}", params={"type": object_type}, json=patch_body)
		if response.status_code in (200, 204):
			return True, f"PUT direto com campo {next(iter(patch_body.keys()))}"

	if payload is None:
		payload = get_object(client, object_id, object_type)

	for path in build_operation_paths(payload):
		op_payload = {
			"operationList": [{"op": "replace", "path": path, "value": new_description}]
		}
		response = client.put(f"/objects/{object_id}", params={"type": object_type}, json=op_payload)
		if response.status_code in (200, 204):
			return True, f"PUT operationList path={path}"

	last_text = response.text if response is not None else "sem resposta"
	return False, last_text


def write_execution_log(
	log_file: Path,
	total: int,
	updated_rows: List[UpdateLogRow],
	skipped_rows: List[UpdateLogRow],
	error_rows: List[UpdateLogRow],
) -> None:
	log_file.parent.mkdir(parents=True, exist_ok=True)

	summary_df = pd.DataFrame(
		[
			{"Indicador": "Total lido no Excel", "Quantidade": total},
			{"Indicador": "Atualizados", "Quantidade": len(updated_rows)},
			{"Indicador": "Ignorados", "Quantidade": len(skipped_rows)},
			{"Indicador": "Erros", "Quantidade": len(error_rows)},
		]
	)
	updated_df = pd.DataFrame([row.to_row() for row in updated_rows])
	skipped_df = pd.DataFrame([row.to_row() for row in skipped_rows])
	error_df = pd.DataFrame([row.to_row() for row in error_rows])

	with pd.ExcelWriter(log_file, engine="openpyxl") as writer:
		summary_df.to_excel(writer, sheet_name="resumo", index=False)
		updated_df.to_excel(writer, sheet_name="alterados", index=False)
		skipped_df.to_excel(writer, sheet_name="ignorados", index=False)
		error_df.to_excel(writer, sheet_name="erros", index=False)


def update_descriptions(client: MstrClient, excel_rows: List[ExcelObjectRow], log_file: Path) -> None:
	total = len(excel_rows)
	success_count = 0
	skip_count = 0
	error_count = 0
	updated_rows: List[UpdateLogRow] = []
	skipped_rows: List[UpdateLogRow] = []
	error_rows: List[UpdateLogRow] = []

	for index, row in enumerate(excel_rows, start=1):
		print(f"[{index}/{total}] Processando {row.object_type_label}: {row.object_id} - {row.name}")

		if not row.description:
			skip_count += 1
			print("  AVISO: descricao vazia no Excel. Linha ignorada.")
			skipped_rows.append(
				UpdateLogRow(
					status="Ignorado",
					object_type_label=row.object_type_label,
					object_id=row.object_id,
					name=row.name,
					action="Sem descricao no Excel",
					previous_description="",
					new_description=row.description,
					detail="Descricao vazia no arquivo Excel.",
				)
			)
			continue

		try:
			current_object = get_object(client, row.object_id, row.object_type_id)
		except Exception as exc:
			error_count += 1
			print(f"  ERRO: nao foi possivel buscar o objeto no Strategy: {exc}")
			error_rows.append(
				UpdateLogRow(
					status="Erro",
					object_type_label=row.object_type_label,
					object_id=row.object_id,
					name=row.name,
					action="Falha ao buscar objeto",
					previous_description="",
					new_description=row.description,
					detail=str(exc),
				)
			)
			continue

		current_name = extract_name(current_object)
		current_description = extract_description(current_object)

		if row.name and current_name and row.name != current_name:
			print(f"  AVISO: nome no Excel difere do Strategy. Excel='{row.name}' | Strategy='{current_name}'")

		if current_description == row.description:
			skip_count += 1
			print("  INFO: descricao ja esta igual no Strategy. Nada a alterar.")
			skipped_rows.append(
				UpdateLogRow(
					status="Ignorado",
					object_type_label=row.object_type_label,
					object_id=row.object_id,
					name=current_name or row.name,
					action="Sem alteracao",
					previous_description=current_description,
					new_description=row.description,
					detail="Descricao do Excel ja estava igual no Strategy.",
				)
			)
			continue

		try:
			updated, detail = patch_object_description(
				client,
				row.object_id,
				row.object_type_id,
				row.description,
				payload=current_object,
			)
		except Exception as exc:
			error_count += 1
			print(f"  ERRO: falha ao atualizar descricao: {exc}")
			error_rows.append(
				UpdateLogRow(
					status="Erro",
					object_type_label=row.object_type_label,
					object_id=row.object_id,
					name=current_name or row.name,
					action="Falha ao atualizar",
					previous_description=current_description,
					new_description=row.description,
					detail=str(exc),
				)
			)
			continue

		if updated:
			success_count += 1
			print(f"  SUCESSO: descricao atualizada ({detail}).")
			action = "Descricao adicionada" if not current_description else "Descricao alterada"
			updated_rows.append(
				UpdateLogRow(
					status="Atualizado",
					object_type_label=row.object_type_label,
					object_id=row.object_id,
					name=current_name or row.name,
					action=action,
					previous_description=current_description,
					new_description=row.description,
					detail=detail,
				)
			)
		else:
			error_count += 1
			print(f"  ERRO: API nao aceitou a atualizacao. Detalhe: {detail}")
			error_rows.append(
				UpdateLogRow(
					status="Erro",
					object_type_label=row.object_type_label,
					object_id=row.object_id,
					name=current_name or row.name,
					action="API nao aceitou a atualizacao",
					previous_description=current_description,
					new_description=row.description,
					detail=detail,
				)
			)

	print("\nResumo da execucao")
	print(f"  Total lido no Excel: {total}")
	print(f"  Atualizados: {success_count}")
	print(f"  Ignorados: {skip_count}")
	print(f"  Erros: {error_count}")

	write_execution_log(log_file, total, updated_rows, skipped_rows, error_rows)
	print(f"  Log gerado em: {log_file}")


def main() -> None:
	base_url = os.environ.get("MSTR_BASE_URL", BASE_URL)
	project_id = os.environ.get("MSTR_PROJECT_ID", PROJECT_ID)
	username = os.environ.get("MSTR_USERNAME", USERNAME)
	password = os.environ.get("MSTR_PASSWORD", PASSWORD)
	input_file = Path(os.environ.get("MSTR_INPUT_FILE", str(INPUT_FILE)))
	log_file = Path(os.environ.get("MSTR_LOG_FILE", str(LOG_FILE)))

	if username == "USER" or password == "PASSWORD":
		raise RuntimeError(
			"Defina USERNAME/PASSWORD no arquivo ou use as variaveis de ambiente "
			"MSTR_USERNAME e MSTR_PASSWORD antes de executar."
		)

	excel_rows = load_excel_rows(input_file)
	client = MstrClient(
		base_url=base_url,
		project_id=project_id,
		username=username,
		password=password,
	)

	try:
		print("Autenticando no Strategy...")
		client.login()
		update_descriptions(client, excel_rows, log_file)
	finally:
		client.logout()


if __name__ == "__main__":
	main()