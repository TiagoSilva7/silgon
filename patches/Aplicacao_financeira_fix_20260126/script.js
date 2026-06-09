const STORAGE_KEY = 'controle_financeiro_lancamentos_v1';
const POUPANCA_RATES_CACHE_KEY = 'controle_financeiro_poupanca_rates_cache_v1';
const BUDGETS_KEY = 'controle_financeiro_orcamentos_v1';
const INITIAL_BALANCES_KEY = 'controle_financeiro_saldos_iniciais_v1';
const CREDIT_CARDS_KEY = 'controle_financeiro_credit_cards_v1';

const APP_VERSION = '2.3.3';

const PORTABLE_INIT_FLAG_KEY = `controle_financeiro_portable_init_${APP_VERSION.replace(/\./g, '_')}`;

function maybePortableFirstRunReset() {
	try {
		const url = new URL(window.location.href);
		const isPortable = url.searchParams.get('portable') === '1';
		if (!isPortable) return;

		const forceReset = url.searchParams.get('reset') === '1';

		if (!forceReset && localStorage.getItem(PORTABLE_INIT_FLAG_KEY) === '1') return;

		const keysToClear = [
			'controle_financeiro_lancamentos_v1',
			'controle_financeiro_orcamentos_v1',
			'controle_financeiro_saldos_iniciais_v1',
			'controle_financeiro_poupanca_rates_cache_v1',
			'controle_financeiro_credit_cards_v1',
		];

		keysToClear.forEach((k) => {
			try {
				localStorage.removeItem(k);
			} catch (_) {
				// ignore
			}
		});

		localStorage.setItem(PORTABLE_INIT_FLAG_KEY, '1');
	} catch (_) {
		// ignore
	}
}
const BACKUP_SCHEMA_VERSION = 1;

let expenseChart = null;
let incomeChart = null;

let lastCardStatementRows = [];

function monthNamesPtBr() {
	return [
		'Janeiro',
		'Fevereiro',
		'Março',
		'Abril',
		'Maio',
		'Junho',
		'Julho',
		'Agosto',
		'Setembro',
		'Outubro',
		'Novembro',
		'Dezembro',
	];
}

function toIsoDate(d) {
	const yyyy = d.getFullYear();
	const mm = String(d.getMonth() + 1).padStart(2, '0');
	const dd = String(d.getDate()).padStart(2, '0');
	return `${yyyy}-${mm}-${dd}`;
}

function parseIsoDate(dateString) {
	const s = String(dateString || '').trim();
	if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
	const [y, m, d] = s.split('-').map(Number);
	const dt = new Date(y, m - 1, d);
	if (Number.isNaN(dt.getTime())) return null;
	return dt;
}

function getPrevYearMonth(yearValue, monthValue) {
	const y = parseInt(String(yearValue), 10);
	const m = parseInt(String(monthValue), 10);
	if (!isFinite(y) || !isFinite(m) || m < 1 || m > 12) return null;
	if (m === 1) return { year: y - 1, month: 12 };
	return { year: y, month: m - 1 };
}

function sumExpensesByCategoryForTransactions(transactions) {
	const totals = new Map();
	(transactions || []).forEach((t) => {
		if (!t || t.type !== 'expense') return;
		const value = Math.abs(Number(t.amount) || 0);
		if (value <= 0) return;
		const cat = getExpenseCategory(t);
		totals.set(cat, (totals.get(cat) || 0) + value);
	});
	return totals;
}

function sumMapValues(map) {
	let total = 0;
	(map || new Map()).forEach((v) => {
		total += Number(v) || 0;
	});
	return total;
}

function formatDelta(current, previous) {
	const cur = Number(current) || 0;
	const prev = Number(previous) || 0;
	const diff = cur - prev;
	const sign = diff > 0 ? '+' : '';
	if (prev <= 0) {
		return `${sign}${formatCurrency(diff)} (—)`;
	}
	const pct = (diff / prev) * 100;
	const pctText = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
	return `${sign}${formatCurrency(diff)} (${pctText})`;
}

// Para comparativo de GASTOS: positivo significa que gastou MENOS (economizou).
function formatSpendingVariation(currentSpend, previousSpend) {
	const cur = Math.abs(Number(currentSpend) || 0);
	const prev = Math.abs(Number(previousSpend) || 0);
	const diff = prev - cur;
	const sign = diff > 0 ? '+' : '';
	if (prev <= 0) {
		return `${sign}${formatCurrency(diff)} (—)`;
	}
	const pct = (diff / prev) * 100;
	const pctText = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
	return `${sign}${formatCurrency(diff)} (${pctText})`;
}

function safeJsonParse(raw, fallback) {
	try {
		if (!raw) return fallback;
		const parsed = JSON.parse(raw);
		return parsed ?? fallback;
	} catch (e) {
		return fallback;
	}
}

function loadObjectFromStorage(key, fallback = {}) {
	const parsed = safeJsonParse(localStorage.getItem(key), fallback);
	return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : fallback;
}

function loadArrayFromStorage(key, fallback = []) {
	const parsed = safeJsonParse(localStorage.getItem(key), fallback);
	return Array.isArray(parsed) ? parsed : fallback;
}

function saveArrayToStorage(key, value) {
	localStorage.setItem(key, JSON.stringify(Array.isArray(value) ? value : []));
}

function loadCreditCards() {
	return loadArrayFromStorage(CREDIT_CARDS_KEY, []);
}

function saveCreditCards(cards) {
	saveArrayToStorage(CREDIT_CARDS_KEY, cards || []);
}

function normalizeCardName(name) {
	return String(name || '').trim();
}

function getCreditCardById(cards, id) {
	const target = String(id || '').trim();
	return (cards || []).find((c) => c && String(c.id) === target) || null;
}

function saveObjectToStorage(key, value) {
	localStorage.setItem(key, JSON.stringify(value || {}));
}

function downloadTextFile(filename, text, mimeType = 'application/octet-stream') {
	const blob = new Blob([text], { type: mimeType });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
}

function normalizeText(value) {
	return String(value || '')
		.trim()
		.toLowerCase()
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '');
}

function isCreditCardTransaction(t) {
	if (!t || t.type !== 'expense') return false;
	const normalized = normalizeText(t.description);
	return normalized.includes('cartao') && normalized.includes('credito');
}

function getExpenseCategory(t) {
	const raw = String((t && t.description) || '').trim();
	if (!raw) return 'Outros';

	const normalized = normalizeText(raw);
	const isCreditCard = normalized.includes('cartao') && normalized.includes('credito');
	if (isCreditCard) return 'Cartão de crédito';

	// Remove sufixos comuns (parcelas/recorrente)
	const cleaned = raw
		.replace(/\s*\(parc\.[^)]+\)\s*$/i, '')
		.replace(/\s*\(recorrente\)\s*$/i, '')
		.trim();

	// Se houver "Categoria - detalhe", usa a parte anterior ao hífen.
	const dashIdx = cleaned.indexOf(' - ');
	if (dashIdx > 0) {
		return cleaned.slice(0, dashIdx).trim() || cleaned;
	}

	return cleaned;
}

function loadSelicRates() {
	try {
		```javascript
		const STORAGE_KEY = 'controle_financeiro_lancamentos_v1';
		const POUPANCA_RATES_CACHE_KEY = 'controle_financeiro_poupanca_rates_cache_v1';
		const BUDGETS_KEY = 'controle_financeiro_orcamentos_v1';
		const INITIAL_BALANCES_KEY = 'controle_financeiro_saldos_iniciais_v1';
		const CREDIT_CARDS_KEY = 'controle_financeiro_credit_cards_v1';

		const APP_VERSION = '2.3.2';

		const PORTABLE_INIT_FLAG_KEY = `controle_financeiro_portable_init_${APP_VERSION.replace(/\./g, '_')}`;

		function maybePortableFirstRunReset() {
			try {
				const url = new URL(window.location.href);
				const isPortable = url.searchParams.get('portable') === '1';
				if (!isPortable) return;

				const forceReset = url.searchParams.get('reset') === '1';

				if (!forceReset && localStorage.getItem(PORTABLE_INIT_FLAG_KEY) === '1') return;

				const keysToClear = [
					'controle_financeiro_lancamentos_v1',
					'controle_financeiro_orcamentos_v1',
					'controle_financeiro_saldos_iniciais_v1',
					'controle_financeiro_poupanca_rates_cache_v1',
					'controle_financeiro_credit_cards_v1',
				];

				keysToClear.forEach((k) => {
					try {
						localStorage.removeItem(k);
					} catch (_) {
						// ignore
					}
				});

				localStorage.setItem(PORTABLE_INIT_FLAG_KEY, '1');
			} catch (_) {
				// ignore
			}
		}
		const BACKUP_SCHEMA_VERSION = 1;

		let expenseChart = null;
		let incomeChart = null;

		let lastCardStatementRows = [];

		function monthNamesPtBr() {
			return [
				'Janeiro',
				'Fevereiro',
				'Março',
				'Abril',
				'Maio',
				'Junho',
				'Julho',
				'Agosto',
				'Setembro',
				'Outubro',
				'Novembro',
				'Dezembro',
			];
		}

		function toIsoDate(d) {
			const yyyy = d.getFullYear();
			const mm = String(d.getMonth() + 1).padStart(2, '0');
			const dd = String(d.getDate()).padStart(2, '0');
			return `${yyyy}-${mm}-${dd}`;
		}

		function parseIsoDate(dateString) {
			const s = String(dateString || '').trim();
			if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
			const [y, m, d] = s.split('-').map(Number);
			const dt = new Date(y, m - 1, d);
			if (Number.isNaN(dt.getTime())) return null;
			return dt;
		}

		function getPrevYearMonth(yearValue, monthValue) {
			const y = parseInt(String(yearValue), 10);
			const m = parseInt(String(monthValue), 10);
			if (!isFinite(y) || !isFinite(m) || m < 1 || m > 12) return null;
			if (m === 1) return { year: y - 1, month: 12 };
			return { year: y, month: m - 1 };
		}

		function sumExpensesByCategoryForTransactions(transactions) {
			const totals = new Map();
			(transactions || []).forEach((t) => {
				if (!t || t.type !== 'expense') return;
				const value = Math.abs(Number(t.amount) || 0);
				if (value <= 0) return;
				const cat = getExpenseCategory(t);
				totals.set(cat, (totals.get(cat) || 0) + value);
			});
			return totals;
		}

		function sumMapValues(map) {
			let total = 0;
			(map || new Map()).forEach((v) => {
				total += Number(v) || 0;
			});
			return total;
		}

		function formatDelta(current, previous) {
			const cur = Number(current) || 0;
			const prev = Number(previous) || 0;
			const diff = cur - prev;
			const sign = diff > 0 ? '+' : '';
			if (prev <= 0) {
				return `${sign}${formatCurrency(diff)} (—)`;
			}
			const pct = (diff / prev) * 100;
			const pctText = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
			return `${sign}${formatCurrency(diff)} (${pctText})`;
		}

		// Para comparativo de GASTOS: positivo significa que gastou MENOS (economizou).
		function formatSpendingVariation(currentSpend, previousSpend) {
			const cur = Math.abs(Number(currentSpend) || 0);
			const prev = Math.abs(Number(previousSpend) || 0);
			const diff = prev - cur;
			const sign = diff > 0 ? '+' : '';
			if (prev <= 0) {
				return `${sign}${formatCurrency(diff)} (—)`;
			}
			const pct = (diff / prev) * 100;
			const pctText = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
			return `${sign}${formatCurrency(diff)} (${pctText})`;
		}

		function safeJsonParse(raw, fallback) {
			try {
				if (!raw) return fallback;
				const parsed = JSON.parse(raw);
				return parsed ?? fallback;
			} catch (e) {
				return fallback;
			}
		}

		function loadObjectFromStorage(key, fallback = {}) {
			const parsed = safeJsonParse(localStorage.getItem(key), fallback);
			return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : fallback;
		}

		function loadArrayFromStorage(key, fallback = []) {
			const parsed = safeJsonParse(localStorage.getItem(key), fallback);
			return Array.isArray(parsed) ? parsed : fallback;
		}

		function saveArrayToStorage(key, value) {
			localStorage.setItem(key, JSON.stringify(Array.isArray(value) ? value : []));
		}

		function loadCreditCards() {
			return loadArrayFromStorage(CREDIT_CARDS_KEY, []);
		}

		function saveCreditCards(cards) {
			saveArrayToStorage(CREDIT_CARDS_KEY, cards || []);
		}

		function normalizeCardName(name) {
			return String(name || '').trim();
		}

		function getCreditCardById(cards, id) {
			const target = String(id || '').trim();
			return (cards || []).find((c) => c && String(c.id) === target) || null;
		}

		function saveObjectToStorage(key, value) {
			localStorage.setItem(key, JSON.stringify(value || {}));
		}

		function downloadTextFile(filename, text, mimeType = 'application/octet-stream') {
			const blob = new Blob([text], { type: mimeType });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = filename;
			document.body.appendChild(a);
			a.click();
			a.remove();
			URL.revokeObjectURL(url);
		}

		function normalizeText(value) {
			return String(value || '')
				.trim()
				.toLowerCase()
				.normalize('NFD')
				.replace(/[\u0300-\u036f]/g, '');
		}

		function isCreditCardTransaction(t) {
			if (!t || t.type !== 'expense') return false;
			const normalized = normalizeText(t.description);
			return normalized.includes('cartao') && normalized.includes('credito');
		}

		function getExpenseCategory(t) {
			const raw = String((t && t.description) || '').trim();
			if (!raw) return 'Outros';

			const normalized = normalizeText(raw);
			const isCreditCard = normalized.includes('cartao') && normalized.includes('credito');
			if (isCreditCard) return 'Cartão de crédito';

			// Remove sufixos comuns (parcelas/recorrente)
			const cleaned = raw
				.replace(/\s*\(parc\.[^)]+\)\s*$/i, '')
				.replace(/\s*\(recorrente\)\s*$/i, '')
				.trim();

			// Se houver "Categoria - detalhe", usa a parte anterior ao hífen.
			const dashIdx = cleaned.indexOf(' - ');
			if (dashIdx > 0) {
				return cleaned.slice(0, dashIdx).trim() || cleaned;
			}

			return cleaned;
		}

		function loadSelicRates() {
			try {
				const raw = localStorage.getItem(POUPANCA_RATES_CACHE_KEY);
				if (!raw) return {};
				const parsed = JSON.parse(raw);
				return parsed && typeof parsed === 'object' ? parsed : {};
			} catch (e) {
				return {};
			}
		}

		function saveSelicRates(rates) {
			localStorage.setItem(POUPANCA_RATES_CACHE_KEY, JSON.stringify(rates || {}));
		}

		function getPeriodKey(year, month) {
			const yy = String(year || '').trim();
			const mm = String(month || '').trim();
			if (!yy || !mm) return '';
			const paddedMonth = String(parseInt(mm, 10)).padStart(2, '0');
			return `${yy}-${paddedMonth}`;
		}

		function getCachedPoupancaRatesForPeriod(year, month) {
			const key = getPeriodKey(year, month);
			if (!key) return null;
			const cache = loadSelicRates();
			const item = cache[key];
			if (!item || typeof item !== 'object') return null;

			const selicPercent = Number(item.selicAnnualPercent);
			const trPercent = Number(item.trMonthlyPercent);
			if (!isFinite(selicPercent) || !isFinite(trPercent)) return null;

			return {
				selicAnnual: selicPercent / 100,
				trMonthly: trPercent / 100,
			};
		}

		function fetchPoupancaRatesForPeriod(year, month) {
			return (async function () {
				const key = getPeriodKey(year, month);
				if (!key) return null;

				const cached = getCachedPoupancaRatesForPeriod(year, month);
				if (cached !== null) return cached;

				try {
					const url = `/api/selic?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`;
					const res = await fetch(url, { cache: 'no-store' });
					if (!res.ok) throw new Error(`HTTP ${res.status}`);
					const json = await res.json();
					const selicAnnualPercent = Number(json && json.selic && json.selic.annualPercent);
					const trMonthlyPercent = Number(json && json.tr && json.tr.monthlyPercent);
					if (!isFinite(selicAnnualPercent) || !isFinite(trMonthlyPercent)) {
						throw new Error('Resposta inválida de SELIC/TR');
					}

					const cache = loadSelicRates();
					cache[key] = {
						selicAnnualPercent: selicAnnualPercent,
						trMonthlyPercent: trMonthlyPercent,
					};
					saveSelicRates(cache);

					return {
						selicAnnual: selicAnnualPercent / 100,
						trMonthly: trMonthlyPercent / 100,
					};
				} catch (e) {
					return { selicAnnual: 0, trMonthly: 0 };
				}
			})();
		}

		function estimatePoupancaMonthlyRate(selicAnnual, trMonthly) {
			const selic = Number(selicAnnual);
			const tr = Number(trMonthly);
			if (!isFinite(selic) || selic < 0) return 0;

			const fixedMonthly = selic > 0.085 ? 0.005 : (0.70 * selic) / 12;
			const trMonthlySafe = isFinite(tr) && tr > 0 ? tr : 0;
			return (1 + fixedMonthly) * (1 + trMonthlySafe) - 1;
		}

		function roundToCents(value) {
			return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
		}

		function clampPercent(value) {
			const n = Number(value);
			if (!isFinite(n)) return 0;
			return Math.min(100, Math.max(0, n));
		}

		function normalizePersonName(value) {
			const v = String(value || '').trim().replace(/\s+/g, ' ');
			return v;
		}

		function splitAmountByPercent(amount, myPercent) {
			const total = Math.abs(Number(amount) || 0);
			const pct = clampPercent(myPercent);
			const totalCents = Math.round(total * 100);
			const mineCents = Math.round((totalCents * pct) / 100);
			const otherCents = totalCents - mineCents;
			return {
				mine: mineCents / 100,
				other: otherCents / 100,
				percent: pct,
			};
		}

		function formatCurrency(value) {
			return value.toLocaleString('pt-BR', {
				style: 'currency',
				currency: 'BRL',
				minimumFractionDigits: 2,
			});
		}

		function formatDate(dateString) {
			if (!dateString) return '';
			const [year, month, day] = dateString.split('-');
			return `${day}/${month}/${year}`;
		}

		function parseBrazilianNumber(value) {
			if (typeof value !== 'string') {
				return Number(value);
			}

			const raw = value.trim().replace(/\s+/g, '');
			if (raw === '') return NaN;

			const hasComma = raw.includes(',');
			const hasDot = raw.includes('.');

			let normalized = raw;

			if (hasComma && hasDot) {
				normalized = raw.replace(/\./g, '').replace(',', '.');
			} else if (hasComma && !hasDot) {
				normalized = raw.replace(',', '.');
			} else {
				normalized = raw;
			}

			return Number(normalized);
		}

		function formatBrazilianDecimal(value) {
			const n = Number(value);
			if (!isFinite(n)) return '';
			return n.toFixed(2).replace('.', ',');
		}

		function loadTransactions() {
			try {
				const raw = localStorage.getItem(STORAGE_KEY);
				if (!raw) return [];
				const parsed = JSON.parse(raw);
				return Array.isArray(parsed) ? parsed : [];
			} catch (e) {
				console.error('Erro ao carregar dados do localStorage', e);
				return [];
			}
		}

		function saveTransactions(transactions) {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(transactions));
		}

		function setStatusMessage(elementId, text, type) {
			const el = document.getElementById(elementId);
			if (!el) return;

			el.textContent = text;
			el.classList.remove('status-success', 'status-error');

			if (type === 'success') {
				el.classList.add('status-success');
			} else if (type === 'error') {
				el.classList.add('status-error');
			}
		}

		function renderExpenseTable(transactions) {
			renderTable(transactions, {
				tbodyId: 'transaction-table-body',
				monthFilterId: 'transactions-month-filter',
				yearFilterId: 'transactions-year-filter',
				typeFilter: 'expense',
				statusElementId: 'transaction-status',
				includeTypeColumn: true,
				enableRecurringActions: true,
				emptyText: 'Nenhuma despesa cadastrada.',
			});
		}

		function renderIncomeTable(transactions) {
			renderTable(transactions, {
				tbodyId: 'income-table-body',
				monthFilterId: 'incomes-month-filter',
				yearFilterId: 'incomes-year-filter',
				typeFilter: 'income',
				statusElementId: 'income-status',
				includeTypeColumn: false,
				enableRecurringActions: true,
				emptyText: 'Nenhuma entrada cadastrada.',
			});
		}

		function refreshAllViews(transactions) {
			renderExpenseTable(transactions);
			renderIncomeTable(transactions);
			populateYearFilter(transactions);
			populateTransactionsYearFilter(transactions);
			populateIncomesYearFilter(transactions);
			populateBudgetCategorySelect(transactions);
			populateCardStatementFilters(transactions);
			populateReportsFilters(transactions);
			renderReports(transactions);
			updateOverview(transactions);
		}

		// (Remaining code identical to the current Aplicacao_financeira/script.js)
		```
		const statusEl = document.getElementById('transaction-status');
		if (statusEl) setStatusMessage('transaction-status', 'TEST ERROR: ' + String(e.message || e), 'error');
	}
}

// Trigger test if requested via query param
try {
	const params = new URLSearchParams(window.location.search);
	if (params.get('run_test') === '1') {
		// run shortly after init to ensure UI functions are ready
		setTimeout(() => { runDeletionScenarioTest(); }, 800);
	}
} catch (e) {
	// ignore
}