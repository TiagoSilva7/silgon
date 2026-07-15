import concurrent.futures
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACOES DE AMBIENTE ---
BASE_URL = "http://10.14.203.158:8080/SEFAPRODLIB/api"
PROJECT_ID = "239BC40211E8B1E3626F0080EF95EED2"
USERNAME = "31071655817"
PASSWORD = "Tera!7777"

# Tipos de objeto da API do Strategy
ATTRIBUTE_TYPE = 12
METRIC_TYPE = 4

DEFAULT_TIMEOUT = 60
DEFAULT_PAGE_SIZE = 1000
DEFAULT_WORKERS = 8
OUTPUT_FILE = Path(__file__).with_name("listagem_objetos_strategy.xlsx")


@dataclass(frozen=True)
class StrategyObject:
	object_type_label: str
	object_type_id: int
	object_id: str
	name: str
	description: str

	def to_row(self) -> Dict[str, str]:
		return {
			"Tipo do objeto": self.object_type_label,
			"ID do objeto": self.object_id,
			"Nome do objeto": self.name,
			"Descricao do objeto": self.description,
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

	def clone(self) -> "MstrClient":
		cloned = MstrClient(
			base_url=self.base_url,
			project_id=self.project_id,
			username=self.username,
			password=self.password,
			timeout=self.timeout,
		)
		cloned.session.headers.update(self.session.headers)
		return cloned


def get_search_results_paginated(
	client: MstrClient,
	object_type: int,
	page_size: int = DEFAULT_PAGE_SIZE,
) -> List[Dict[str, Any]]:
	offset = 0
	total_items: Optional[int] = None
	all_items: List[Dict[str, Any]] = []

	while True:
		response = client.get(
			"/searches/results",
			params={"type": object_type, "limit": page_size, "offset": offset},
		)
		payload = response.json()

		if not isinstance(payload, dict):
			raise RuntimeError(f"Resposta invalida em /searches/results para type={object_type}.")

		if total_items is None:
			total_items = int(payload.get("totalItems", 0))

		page_items = payload.get("result", [])
		if not isinstance(page_items, list) or not page_items:
			break

		all_items.extend(item for item in page_items if isinstance(item, dict))
		offset += page_size

		if total_items is not None and offset >= total_items:
			break

	return all_items


def extract_description(payload: Dict[str, Any]) -> str:
	for key in ("description", "desc", "information", "comments"):
		value = payload.get(key)
		if isinstance(value, str) and value.strip():
			return value.strip()
	return ""


def get_object_description(client: MstrClient, object_id: str, object_type: int) -> str:
	response = client.get(f"/objects/{object_id}", params={"type": object_type})
	payload = response.json()
	if not isinstance(payload, dict):
		return ""
	return extract_description(payload)


def build_strategy_objects(
	client: MstrClient,
	object_type: int,
	object_label: str,
	workers: int = DEFAULT_WORKERS,
) -> List[StrategyObject]:
	items = get_search_results_paginated(client, object_type=object_type)
	objects: List[StrategyObject] = []
	pending_description: List[int] = []

	for item in items:
		object_id = str(item.get("id", "")).strip()
		name = str(item.get("name", "")).strip()

		if not object_id or not name:
			continue

		description = extract_description(item)
		objects.append(
			StrategyObject(
				object_type_label=object_label,
				object_type_id=object_type,
				object_id=object_id,
				name=name,
				description=description,
			)
		)

		if not description:
			pending_description.append(len(objects) - 1)

	if pending_description:
		print(f"Resolvendo descricao de {len(pending_description)} {object_label.lower()}s...")

		def fetch_description(index: int) -> tuple[int, str]:
			row = objects[index]
			cloned_client = client.clone()
			try:
				description = get_object_description(cloned_client, row.object_id, row.object_type_id)
				return index, description
			finally:
				cloned_client.session.close()

		with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
			future_map = {
				executor.submit(fetch_description, index): index for index in pending_description
			}
			for future in concurrent.futures.as_completed(future_map):
				try:
					index, description = future.result()
				except Exception:
					continue
				row = objects[index]
				objects[index] = StrategyObject(
					object_type_label=row.object_type_label,
					object_type_id=row.object_type_id,
					object_id=row.object_id,
					name=row.name,
					description=description,
				)

	objects.sort(key=lambda item: (item.object_type_label, item.name.lower(), item.object_id))
	return objects


def export_to_excel(
	attributes: List[StrategyObject],
	metrics: List[StrategyObject],
	output_file: Path,
) -> None:
	output_file.parent.mkdir(parents=True, exist_ok=True)
	attributes_df = pd.DataFrame([item.to_row() for item in attributes])
	metrics_df = pd.DataFrame([item.to_row() for item in metrics])

	with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
		attributes_df.to_excel(writer, sheet_name="atributos", index=False)
		metrics_df.to_excel(writer, sheet_name="metricas", index=False)


def main() -> None:
	base_url = os.environ.get("MSTR_BASE_URL", BASE_URL)
	project_id = os.environ.get("MSTR_PROJECT_ID", PROJECT_ID)
	username = os.environ.get("MSTR_USERNAME", USERNAME)
	password = os.environ.get("MSTR_PASSWORD", PASSWORD)
	output_file = Path(os.environ.get("MSTR_OUTPUT_FILE", str(OUTPUT_FILE)))

	if username == "USER" or password == "PASSWORD":
		raise RuntimeError(
			"Defina USERNAME/PASSWORD no arquivo ou use as variaveis de ambiente "
			"MSTR_USERNAME e MSTR_PASSWORD antes de executar."
		)

	client = MstrClient(
		base_url=base_url,
		project_id=project_id,
		username=username,
		password=password,
	)

	try:
		print("Autenticando no Strategy...")
		client.login()

		print("Listando atributos...")
		attributes = build_strategy_objects(client, ATTRIBUTE_TYPE, "Atributo")

		print("Listando metricas...")
		metrics = build_strategy_objects(client, METRIC_TYPE, "Metrica")

		export_to_excel(attributes, metrics, output_file)

		print(
			f"Arquivo gerado com sucesso em: {output_file} | "
			f"Atributos: {len(attributes)} | Metricas: {len(metrics)}"
		)
	finally:
		client.logout()


if __name__ == "__main__":
	main()
