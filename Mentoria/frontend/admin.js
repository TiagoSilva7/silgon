const loginForm = document.getElementById('login-form');
const loginMensagemEl = document.getElementById('login-mensagem');
const adminLoginEl = document.getElementById('admin-login');
const adminConfigEl = document.getElementById('admin-config');

const dataBloqueioInput = document.getElementById('data-bloqueio');
const slotsBloqueioEl = document.getElementById('slots-bloqueio');

const listaConteudoAdminEl = document.getElementById('lista-conteudo-admin');
const filtroMesAdminEl = document.getElementById('filtro-mes-admin');
const filtroDiaAdminEl = document.getElementById('filtro-dia-admin');
const btnExportarXlsxEl = document.getElementById('btn-exportar-xlsx');
const listaResumoBloqueiosEl = document.getElementById('lista-resumo-bloqueios');
const btnAtualizarResumoBloqueiosEl = document.getElementById('btn-atualizar-resumo-bloqueios');
const filtroMesBloqueiosEl = document.getElementById('filtro-mes-bloqueios');
const adminCalGridEl = document.getElementById('admin-cal-grid');
const adminCalMonthLabelEl = document.getElementById('admin-cal-month-label');
const adminCalPrevBtn = document.getElementById('admin-cal-prev');
const adminCalNextBtn = document.getElementById('admin-cal-next');

let agendamentosOriginaisAdmin = [];
let resumoBloqueiosOriginais = [];
let ultimaDataBloqueioValida = '';
let adminCalCurrentYear;
let adminCalCurrentMonth; // 0-11

function obterAgendamentosFiltradosAdmin() {
  if (!Array.isArray(agendamentosOriginaisAdmin) || agendamentosOriginaisAdmin.length === 0) {
    return [];
  }

  const mesSelecionado = filtroMesAdminEl.value;
  const diaSelecionado = filtroDiaAdminEl.value;

  return agendamentosOriginaisAdmin.filter((item) => {
    const partes = (item.data || '').split('-');
    if (partes.length !== 3) return false;
    const [ano, mes, dia] = partes;
    const chaveMes = `${ano}-${mes}`;

    if (mesSelecionado && chaveMes !== mesSelecionado) {
      return false;
    }

    if (diaSelecionado && dia !== diaSelecionado) {
      return false;
    }

    return true;
  });
}

function gerarHorariosPossiveis() {
  const horarios = [];
  // Manhã: 09:00 até 11:00, de 1 em 1 hora
  for (let minutos = 9 * 60; minutos <= 11 * 60; minutos += 60) {
    const h = String(Math.floor(minutos / 60)).padStart(2, '0');
    const m = String(minutos % 60).padStart(2, '0');
    horarios.push(`${h}:${m}`);
  }
  // Tarde: 13:00 até 17:00, de 1 em 1 hora
  for (let minutos = 13 * 60; minutos <= 17 * 60; minutos += 60) {
    const h = String(Math.floor(minutos / 60)).padStart(2, '0');
    const m = String(minutos % 60).padStart(2, '0');
    horarios.push(`${h}:${m}`);
  }
  return horarios;
}

async function carregarBloqueios(dataISO) {
  slotsBloqueioEl.innerHTML = '<span class="hora-msg">Carregando horários...</span>';

  try {
    const response = await fetch(`/api/bloqueios?data=${encodeURIComponent(dataISO)}`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.mensagem || 'Erro ao buscar bloqueios.');
    }

    const bloqueios = Array.isArray(payload.bloqueios) ? payload.bloqueios : [];
    const todosHorarios = gerarHorariosPossiveis();

    slotsBloqueioEl.innerHTML = '';

    todosHorarios.forEach((hora) => {
      const slot = document.createElement('div');
      slot.className = 'hora-slot';
      slot.textContent = hora;
      slot.dataset.hora = hora;

      if (bloqueios.includes(hora)) {
        slot.classList.add('bloqueado-admin');
      }

      slot.addEventListener('click', async () => {
        if (!dataBloqueioInput.value) return;

        const estaBloqueado = slot.classList.contains('bloqueado-admin');

        try {
          if (!estaBloqueado) {
            // Bloquear horário
            const resp = await fetch('/api/bloqueios', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ data: dataISO, horas: [hora] }),
            });

            const dados = await resp.json();
            if (!resp.ok) {
              throw new Error(dados.mensagem || 'Erro ao salvar bloqueio.');
            }

            slot.classList.add('bloqueado-admin');
            if (typeof carregarResumoBloqueios === 'function') {
              carregarResumoBloqueios();
            }
          } else {
            // Desbloquear horário
            const resp = await fetch('/api/bloqueios', {
              method: 'DELETE',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ data: dataISO, hora }),
            });

            const dados = await resp.json();
            if (!resp.ok) {
              throw new Error(dados.mensagem || 'Erro ao remover bloqueio.');
            }

            slot.classList.remove('bloqueado-admin');
            if (typeof carregarResumoBloqueios === 'function') {
              carregarResumoBloqueios();
            }
          }
        } catch (error) {
          alert(error.message || 'Erro ao atualizar bloqueio.');
        }
      });

      slotsBloqueioEl.appendChild(slot);
    });
  } catch (error) {
    slotsBloqueioEl.innerHTML = `<span class="hora-msg">${error.message || 'Erro ao carregar horários.'}</span>`;
  }
}

function inicializarCalendarioAdmin() {
  if (!adminCalGridEl || !adminCalMonthLabelEl) return;

  const hoje = new Date();
  adminCalCurrentYear = hoje.getFullYear();
  adminCalCurrentMonth = hoje.getMonth();
  renderizarCalendarioAdmin();

  if (adminCalPrevBtn) {
    adminCalPrevBtn.addEventListener('click', () => {
      if (adminCalCurrentMonth === 0) {
        adminCalCurrentMonth = 11;
        adminCalCurrentYear -= 1;
      } else {
        adminCalCurrentMonth -= 1;
      }
      renderizarCalendarioAdmin();
    });
  }

  if (adminCalNextBtn) {
    adminCalNextBtn.addEventListener('click', () => {
      if (adminCalCurrentMonth === 11) {
        adminCalCurrentMonth = 0;
        adminCalCurrentYear += 1;
      } else {
        adminCalCurrentMonth += 1;
      }
      renderizarCalendarioAdmin();
    });
  }
}

function renderizarCalendarioAdmin() {
  if (!adminCalGridEl || !adminCalMonthLabelEl) return;

  const nomesMeses = [
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

  adminCalMonthLabelEl.textContent = `${nomesMeses[adminCalCurrentMonth]} de ${adminCalCurrentYear}`;

  adminCalGridEl.innerHTML = '';

  const nomesDias = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S'];
  nomesDias.forEach((d) => {
    const el = document.createElement('div');
    el.textContent = d;
    el.className = 'calendar-day-name';
    adminCalGridEl.appendChild(el);
  });

  const primeiroDiaMes = new Date(adminCalCurrentYear, adminCalCurrentMonth, 1);
  const diaSemanaPrimeiro = primeiroDiaMes.getDay(); // 0 (Dom) - 6 (Sáb)
  const diasNoMes = new Date(adminCalCurrentYear, adminCalCurrentMonth + 1, 0).getDate();

  const selecionadaISO = dataBloqueioInput ? dataBloqueioInput.value : '';
  const hoje = new Date();
  const hojeISO = hoje.toISOString().slice(0, 10);

  for (let i = 0; i < diaSemanaPrimeiro; i += 1) {
    const vazio = document.createElement('div');
    vazio.className = 'calendar-day outside-month';
    adminCalGridEl.appendChild(vazio);
  }

  for (let dia = 1; dia <= diasNoMes; dia += 1) {
    const cell = document.createElement('div');
    cell.textContent = String(dia);
    cell.className = 'calendar-day';

    const dataISO = `${adminCalCurrentYear}-${String(adminCalCurrentMonth + 1).padStart(2, '0')}-${String(dia).padStart(2, '0')}`;
    const diaSemana = new Date(adminCalCurrentYear, adminCalCurrentMonth, dia).getDay(); // 0 (Dom) - 6 (Sáb)

    if (diaSemana === 0 || diaSemana === 6) {
      cell.classList.add('weekend');
      cell.dataset.bloqueado = 'true';
    } else {
      cell.dataset.dateIso = dataISO;
      cell.dataset.bloqueado = 'false';
    }

    if (dataISO === hojeISO) {
      cell.classList.add('today');
    }

    if (selecionadaISO === dataISO) {
      cell.classList.add('selected');
    }

    cell.addEventListener('click', () => {
      if (cell.dataset.bloqueado === 'true' || !cell.dataset.dateIso) {
        return;
      }

      const novaDataISO = cell.dataset.dateIso;
      if (!novaDataISO) return;

      if (dataBloqueioInput) {
        dataBloqueioInput.value = novaDataISO;
      }
      ultimaDataBloqueioValida = novaDataISO;
      carregarBloqueios(novaDataISO);

      // Atualiza seleção visual
      adminCalGridEl.querySelectorAll('.calendar-day.selected').forEach((el) => el.classList.remove('selected'));
      cell.classList.add('selected');
    });

    adminCalGridEl.appendChild(cell);
  }
}

function atualizarOpcoesMesBloqueios() {
  if (!filtroMesBloqueiosEl) return;

  const mesesMap = new Map();
  resumoBloqueiosOriginais.forEach((item) => {
    const partes = (item.data || '').split('-');
    if (partes.length !== 3) return;
    const [ano, mes] = partes;
    const chave = `${ano}-${mes}`;
    if (!mesesMap.has(chave)) {
      mesesMap.set(chave, { ano, mes });
    }
  });

  const mesesOrdenados = Array.from(mesesMap.values()).sort((a, b) => {
    const chaveA = `${a.ano}-${a.mes}`;
    const chaveB = `${b.ano}-${b.mes}`;
    return chaveA.localeCompare(chaveB);
  });

  let opcoes = '<option value="">Todos os meses</option>';
  mesesOrdenados.forEach(({ ano, mes }) => {
    opcoes += `<option value="${ano}-${mes}">${mes}/${ano}</option>`;
  });

  filtroMesBloqueiosEl.innerHTML = opcoes;
  filtroMesBloqueiosEl.disabled = mesesOrdenados.length === 0;
}

function renderizarResumoBloqueios() {
  if (!listaResumoBloqueiosEl) return;

  if (!Array.isArray(resumoBloqueiosOriginais) || resumoBloqueiosOriginais.length === 0) {
    listaResumoBloqueiosEl.innerHTML = '<p class="mensagem-lista">Nenhum horário bloqueado.</p>';
    return;
  }

  const filtroMes = filtroMesBloqueiosEl ? filtroMesBloqueiosEl.value : '';

  // Agrupa por data, respeitando filtro de mês
  const mapaPorData = new Map();
  resumoBloqueiosOriginais.forEach((b) => {
    if (!b.data || !b.hora) return;
    const partes = b.data.split('-');
    if (partes.length !== 3) return;
    const [ano, mes] = partes;
    const chaveMes = `${ano}-${mes}`;
    if (filtroMes && chaveMes !== filtroMes) return;

    if (!mapaPorData.has(b.data)) {
      mapaPorData.set(b.data, []);
    }
    mapaPorData.get(b.data).push(b.hora);
  });

  if (mapaPorData.size === 0) {
    listaResumoBloqueiosEl.innerHTML = '<p class="mensagem-lista">Nenhum horário bloqueado para o filtro selecionado.</p>';
    return;
  }

  const datasOrdenadas = Array.from(mapaPorData.keys()).sort((a, b) => a.localeCompare(b));

  const html = datasOrdenadas
    .map((dataIso) => {
      const horas = mapaPorData
        .get(dataIso)
        .slice()
        .sort((a, b) => a.localeCompare(b));
      const dataBr = formatarDataBr(dataIso);

      const linhasHoras = horas
        .map(
          (hora) =>
            `<span class="tag-bloqueio">${hora} <button type="button" class="btn-remover-bloqueio" data-data="${dataIso}" data-hora="${hora}">x</button></span>`
        )
        .join(' ');

      return `<div class="item-resumo-bloqueio">
              <div class="resumo-data">${dataBr}</div>
              <div class="resumo-horas">${linhasHoras}</div>
            </div>`;
    })
    .join('');

  listaResumoBloqueiosEl.innerHTML = html;

  // Listeners para remover bloqueios a partir do resumo
  const botoesRemover = listaResumoBloqueiosEl.querySelectorAll('.btn-remover-bloqueio');
  botoesRemover.forEach((btn) => {
    btn.addEventListener('click', async () => {
      const dataIso = btn.dataset.data;
      const hora = btn.dataset.hora;
      if (!dataIso || !hora) return;

      const confirmar = window.confirm(`Remover bloqueio de ${hora} em ${formatarDataBr(dataIso)}?`);
      if (!confirmar) return;

      try {
        const resp = await fetch('/api/bloqueios', {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ data: dataIso, hora }),
        });

        const dados = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          throw new Error(dados.mensagem || 'Erro ao remover bloqueio.');
        }

        // Atualiza resumo e, se a data estiver selecionada à esquerda, atualiza os slots também
        await carregarResumoBloqueios();
        if (dataBloqueioInput && dataBloqueioInput.value === dataIso) {
          carregarBloqueios(dataIso);
        }
      } catch (error) {
        alert(error.message || 'Erro ao remover bloqueio.');
      }
    });
  });
}

async function carregarResumoBloqueios() {
  if (!listaResumoBloqueiosEl) return;

  listaResumoBloqueiosEl.innerHTML = '<p class="mensagem-lista">Carregando resumo de bloqueios...</p>';

  try {
    const response = await fetch('/api/bloqueios/todos');
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.mensagem || 'Erro ao buscar resumo de bloqueios.');
    }

    const bloqueios = Array.isArray(payload.bloqueios) ? payload.bloqueios : [];
    resumoBloqueiosOriginais = bloqueios;

    atualizarOpcoesMesBloqueios();
    renderizarResumoBloqueios();
  } catch (error) {
    listaResumoBloqueiosEl.innerHTML = `<p class="mensagem-lista">${error.message || 'Erro ao carregar resumo de bloqueios.'}</p>`;
  }
}

function formatarDataBr(dataIso) {
  if (!dataIso) return '';
  const partes = dataIso.split('-');
  if (partes.length !== 3) return dataIso;
  const [ano, mes, dia] = partes;
  return `${dia}/${mes}/${ano}`;
}

function atualizarOpcoesMesAdmin() {
  const mesesMap = new Map();

  agendamentosOriginaisAdmin.forEach((item) => {
    const partes = (item.data || '').split('-');
    if (partes.length !== 3) return;
    const [ano, mes] = partes;
    const chave = `${ano}-${mes}`;
    if (!mesesMap.has(chave)) {
      mesesMap.set(chave, { ano, mes });
    }
  });

  const mesesOrdenados = Array.from(mesesMap.values()).sort((a, b) => {
    const chaveA = `${a.ano}-${a.mes}`;
    const chaveB = `${b.ano}-${b.mes}`;
    return chaveA.localeCompare(chaveB);
  });

  let opcoes = '<option value="">Todos os meses</option>';
  mesesOrdenados.forEach(({ ano, mes }) => {
    opcoes += `<option value="${ano}-${mes}">${mes}/${ano}</option>`;
  });

  filtroMesAdminEl.innerHTML = opcoes;
  filtroMesAdminEl.disabled = mesesOrdenados.length === 0;
}

function atualizarOpcoesDiaAdmin() {
  const mesSelecionado = filtroMesAdminEl.value;

  if (!mesSelecionado) {
    filtroDiaAdminEl.innerHTML = '<option value="">Todos os dias</option>';
    filtroDiaAdminEl.disabled = true;
    return;
  }

  const diasSet = new Set();

  agendamentosOriginaisAdmin.forEach((item) => {
    const partes = (item.data || '').split('-');
    if (partes.length !== 3) return;
    const [ano, mes, dia] = partes;
    const chaveMes = `${ano}-${mes}`;
    if (chaveMes === mesSelecionado) {
      diasSet.add(dia);
    }
  });

  const diasOrdenados = Array.from(diasSet.values()).sort((a, b) => a.localeCompare(b));

  let opcoes = '<option value="">Todos os dias</option>';
  diasOrdenados.forEach((dia) => {
    opcoes += `<option value="${dia}">${dia}</option>`;
  });

  filtroDiaAdminEl.innerHTML = opcoes;
  filtroDiaAdminEl.disabled = diasOrdenados.length === 0;
}

function renderizarTabelaAdmin() {
  if (!Array.isArray(agendamentosOriginaisAdmin) || agendamentosOriginaisAdmin.length === 0) {
    listaConteudoAdminEl.innerHTML = '<p class="mensagem-lista">Nenhum agendamento encontrado.</p>';
    return;
  }

  const filtrados = obterAgendamentosFiltradosAdmin();

  if (filtrados.length === 0) {
    listaConteudoAdminEl.innerHTML = '<p class="mensagem-lista">Nenhum agendamento para o filtro selecionado.</p>';
    return;
  }

  const linhas = filtrados
    .map((item) => {
      const dataBr = formatarDataBr(item.data);
      const hora = item.hora;
      const nome = item.nome_completo;
      const assunto = item.assunto;
      const id = item.id;

      return `<tr>
                <td>${dataBr}</td>
                <td>${hora}</td>
                <td>${nome}</td>
          <td>${assunto}</td>
          <td><button type="button" class="btn-cancelar" data-id="${id}">Cancelar</button></td>
              </tr>`;
    })
    .join('');

  listaConteudoAdminEl.innerHTML = `
    <table class="tabela-agendamentos">
      <thead>
        <tr>
          <th>Data</th>
          <th>Hora</th>
          <th>Nome</th>
        <th>Assunto</th>
        <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        ${linhas}
      </tbody>
    </table>
  `;

  // Adiciona listeners de cancelamento
  const botoesCancelar = listaConteudoAdminEl.querySelectorAll('.btn-cancelar');
  botoesCancelar.forEach((botao) => {
    botao.addEventListener('click', async () => {
      const id = botao.dataset.id;
      if (!id) return;

      const confirmar = window.confirm('Deseja realmente cancelar este agendamento?');
      if (!confirmar) return;

      try {
        const resp = await fetch(`/api/mentorias/${id}`, {
          method: 'DELETE',
        });
        const dados = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          throw new Error(dados.mensagem || 'Erro ao cancelar agendamento.');
        }

        // Remove do array original e re-renderiza
        agendamentosOriginaisAdmin = agendamentosOriginaisAdmin.filter((item) => String(item.id) !== String(id));
        atualizarOpcoesMesAdmin();
        atualizarOpcoesDiaAdmin();
        renderizarTabelaAdmin();
      } catch (error) {
        alert(error.message || 'Erro ao cancelar agendamento.');
      }
    });
  });
}

async function carregarAgendamentosAdmin() {
  listaConteudoAdminEl.innerHTML = '<p class="mensagem-lista">Carregando agendamentos...</p>';

  try {
    const response = await fetch('/api/mentorias');
    const dados = await response.json();

    if (!response.ok) {
      throw new Error('Erro ao buscar agendamentos.');
    }

    if (!Array.isArray(dados) || dados.length === 0) {
      agendamentosOriginaisAdmin = [];
      filtroMesAdminEl.disabled = true;
      filtroDiaAdminEl.disabled = true;
      listaConteudoAdminEl.innerHTML = '<p class="mensagem-lista">Nenhum agendamento encontrado.</p>';
      return;
    }

    agendamentosOriginaisAdmin = dados.slice().sort((a, b) => {
      if (a.data === b.data) {
        return (a.hora || '').localeCompare(b.hora || '');
      }
      return (a.data || '').localeCompare(b.data || '');
    });

    atualizarOpcoesMesAdmin();
    atualizarOpcoesDiaAdmin();
    renderizarTabelaAdmin();
  } catch (error) {
    listaConteudoAdminEl.innerHTML = `<p class="mensagem-lista">${error.message || 'Erro ao carregar agendamentos.'}</p>`;
  }
}

loginForm.addEventListener('submit', (event) => {
  event.preventDefault();

  loginMensagemEl.textContent = '';
  loginMensagemEl.className = 'mensagem';

  const usuario = document.getElementById('usuario').value.trim();
  const senha = document.getElementById('senha').value.trim();

  if (usuario === 'admin' && senha === 'admin') {
    adminLoginEl.classList.add('oculto');
    adminConfigEl.classList.remove('oculto');
    loginMensagemEl.textContent = '';

    carregarAgendamentosAdmin();
    if (typeof carregarResumoBloqueios === 'function') {
      carregarResumoBloqueios();
    }
	if (typeof inicializarCalendarioAdmin === 'function') {
		inicializarCalendarioAdmin();
	}
  } else {
    loginMensagemEl.textContent = 'Usuário ou senha inválidos.';
    loginMensagemEl.classList.add('erro');
  }
});

if (dataBloqueioInput) {
  dataBloqueioInput.addEventListener('change', () => {
    const dataISO = dataBloqueioInput.value;
    if (!dataISO) {
      slotsBloqueioEl.innerHTML = '<span class="hora-msg">Selecione uma data para carregar os horários.</span>';
      return;
    }

    // Bloquear fins de semana (sábado e domingo) também na tela de admin
    const dataObj = new Date(`${dataISO}T00:00:00`);
    const diaSemana = dataObj.getDay(); // 0 (Dom) - 6 (Sáb)
    if (diaSemana === 0 || diaSemana === 6) {
      alert('Fins de semana não podem ser configurados para bloqueio. Escolha um dia útil.');
      // Volta para a última data válida (se existir) ou limpa
      if (ultimaDataBloqueioValida) {
        dataBloqueioInput.value = ultimaDataBloqueioValida;
        carregarBloqueios(ultimaDataBloqueioValida);
      } else {
        dataBloqueioInput.value = '';
        slotsBloqueioEl.innerHTML = '<span class="hora-msg">Selecione uma data para carregar os horários.</span>';
      }
      return;
    }

    ultimaDataBloqueioValida = dataISO;
    carregarBloqueios(dataISO);
  });
}

if (btnAtualizarResumoBloqueiosEl) {
  btnAtualizarResumoBloqueiosEl.addEventListener('click', () => {
    carregarResumoBloqueios();
  });
}

if (filtroMesBloqueiosEl) {
  filtroMesBloqueiosEl.addEventListener('change', () => {
    renderizarResumoBloqueios();
  });
}

// Inicializa o calendário admin mesmo antes do login, se desejado
if (adminCalGridEl && adminCalMonthLabelEl) {
  inicializarCalendarioAdmin();
}

if (filtroMesAdminEl) {
  filtroMesAdminEl.addEventListener('change', () => {
    atualizarOpcoesDiaAdmin();
    renderizarTabelaAdmin();

    const mesSelecionado = filtroMesAdminEl.value;
    if (!mesSelecionado) {
      return;
    }

    // Seleciona automaticamente o primeiro dia disponível do mês
    const opcoesDia = Array.from(filtroDiaAdminEl.options).filter((opt) => opt.value);
    if (opcoesDia.length === 0) {
      return;
    }

    const primeiroDia = opcoesDia[0].value;
    filtroDiaAdminEl.value = primeiroDia;
    renderizarTabelaAdmin();

    const [ano, mes] = mesSelecionado.split('-');
    const dataISO = `${ano}-${mes}-${primeiroDia}`;

    if (dataBloqueioInput) {
      dataBloqueioInput.value = dataISO;
      carregarBloqueios(dataISO);
    }
  });
}

if (filtroDiaAdminEl) {
  filtroDiaAdminEl.addEventListener('change', () => {
    renderizarTabelaAdmin();

    const mesSelecionado = filtroMesAdminEl ? filtroMesAdminEl.value : '';
    const diaSelecionado = filtroDiaAdminEl.value;

    if (!mesSelecionado || !diaSelecionado) {
      return;
    }

    const [ano, mes] = mesSelecionado.split('-');
    const dataISO = `${ano}-${mes}-${diaSelecionado}`;

    if (dataBloqueioInput) {
      dataBloqueioInput.value = dataISO;
      carregarBloqueios(dataISO);
    }
  });
}

if (btnExportarXlsxEl && typeof XLSX !== 'undefined') {
  btnExportarXlsxEl.addEventListener('click', () => {
    const filtrados = obterAgendamentosFiltradosAdmin();
    if (!filtrados || filtrados.length === 0) {
      alert('Nenhum agendamento para exportar com o filtro atual.');
      return;
    }

    const dadosSheet = [
      ['ID', 'Data', 'Hora', 'Nome', 'E-mail', 'Telefone', 'Assunto', 'Criado em'],
      ...filtrados.map((item) => [
        item.id,
        formatarDataBr(item.data),
        item.hora,
        item.nome_completo,
        item.email,
        item.telefone,
        item.assunto,
        item.criado_em,
      ]),
    ];

    const ws = XLSX.utils.aoa_to_sheet(dadosSheet);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Mentorias');

    XLSX.writeFile(wb, 'mentorias.xlsx');
  });
}
