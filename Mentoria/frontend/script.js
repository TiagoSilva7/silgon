const form = document.getElementById('mentoria-form');
const mensagemEl = document.getElementById('mensagem');
const dataInput = document.getElementById('data');
const horaInput = document.getElementById('hora');
const horaOpcoesEl = document.getElementById('hora-opcoes');
const calGridEl = document.getElementById('cal-grid');
const calMonthLabelEl = document.getElementById('cal-month-label');
const calPrevBtn = document.getElementById('cal-prev');
const calNextBtn = document.getElementById('cal-next');
let calCurrentYear;
let calCurrentMonth; // 0-11

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  mensagemEl.textContent = '';
  mensagemEl.className = 'mensagem';

  const formData = new FormData(form);

  const payload = {
    nomeCompleto: formData.get('nomeCompleto')?.trim(),
    email: formData.get('email')?.trim(),
    telefone: formData.get('telefone')?.trim(),
    data: formData.get('data'),
    hora: formData.get('hora'),
    assunto: formData.get('assunto')?.trim(),
  };

  try {
    const response = await fetch('/api/mentorias', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.mensagem || 'Erro ao realizar agendamento.');
    }

    mensagemEl.textContent = data.mensagem || 'Agendamento realizado com sucesso!';
    mensagemEl.classList.add('sucesso');

    // Permite o usuário fazer vários agendamentos, apenas limpando o formulário
    form.reset();

    // Remover o bloco de horário selecionado da interface, sem recarregar a página
    const slotSelecionado = document.querySelector('.hora-slot.selecionado');
    if (slotSelecionado) {
      slotSelecionado.remove();
    }

    horaInput.value = '';

    // Se não restarem horários visíveis, exibir mensagem de esgotado
    if (!horaOpcoesEl.querySelector('.hora-slot')) {
      horaOpcoesEl.innerHTML = '<span class="hora-msg">Nenhum horário disponível nesta data.</span>';
    }

    // A listagem de agendamentos agora está apenas na página de admin,
    // portanto não é mais atualizada aqui.
  } catch (error) {
    mensagemEl.textContent = error.message || 'Erro ao realizar agendamento.';
    mensagemEl.classList.add('erro');

    // Em caso de conflito de horário, recarregar horários disponíveis
    if (dataInput.value) {
      carregarHorariosDisponiveis(dataInput.value);
    }
  }
});

async function carregarHorariosDisponiveis(dataSelecionada) {
  horaInput.value = '';
  horaOpcoesEl.innerHTML = '<span class="hora-msg">Carregando horários...</span>';

  try {
    const response = await fetch(`/api/mentorias/disponiveis?data=${encodeURIComponent(dataSelecionada)}`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.mensagem || 'Erro ao buscar horários disponíveis.');
    }

    const horarios = Array.isArray(payload.horarios) ? payload.horarios : [];

    if (horarios.length === 0) {
      horaOpcoesEl.innerHTML = '<span class="hora-msg">Nenhum horário disponível nesta data.</span>';
      return;
    }

    horaOpcoesEl.innerHTML = '';

    horarios.forEach((hora) => {
      const slot = document.createElement('div');
      slot.className = 'hora-slot';
      slot.textContent = hora;
      slot.dataset.hora = hora;

      slot.addEventListener('click', () => {
        if (slot.classList.contains('desativado')) return;

        document.querySelectorAll('.hora-slot.selecionado').forEach((el) => el.classList.remove('selecionado'));
        slot.classList.add('selecionado');
        horaInput.value = hora;
      });

      horaOpcoesEl.appendChild(slot);
    });
  } catch (error) {
    horaOpcoesEl.innerHTML = '<span class="hora-msg">Erro ao carregar horários.</span>';
  }
}
dataInput.addEventListener('change', () => {
  if (dataInput.value) {
    carregarHorariosDisponiveis(dataInput.value);
  } else {
    horaInput.value = '';
    horaOpcoesEl.innerHTML = '<span class="hora-msg">Selecione uma data primeiro.</span>';
  }
});

function inicializarCalendario() {
  const hoje = new Date();
  calCurrentYear = hoje.getFullYear();
  calCurrentMonth = hoje.getMonth();
  renderizarCalendario();

  calPrevBtn.addEventListener('click', () => {
    if (calCurrentMonth === 0) {
      calCurrentMonth = 11;
      calCurrentYear -= 1;
    } else {
      calCurrentMonth -= 1;
    }
    renderizarCalendario();
  });

  calNextBtn.addEventListener('click', () => {
    if (calCurrentMonth === 11) {
      calCurrentMonth = 0;
      calCurrentYear += 1;
    } else {
      calCurrentMonth += 1;
    }
    renderizarCalendario();
  });
}

function renderizarCalendario() {
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

  calMonthLabelEl.textContent = `${nomesMeses[calCurrentMonth]} de ${calCurrentYear}`;

  calGridEl.innerHTML = '';

  const nomesDias = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S'];
  nomesDias.forEach((d) => {
    const el = document.createElement('div');
    el.textContent = d;
    el.className = 'calendar-day-name';
    calGridEl.appendChild(el);
  });

  const primeiroDiaMes = new Date(calCurrentYear, calCurrentMonth, 1);
  const diaSemanaPrimeiro = primeiroDiaMes.getDay(); // 0 (Dom) - 6 (Sáb)
  const diasNoMes = new Date(calCurrentYear, calCurrentMonth + 1, 0).getDate();

  const hoje = new Date();
  const hojeISO = hoje.toISOString().slice(0, 10);
  const selecionadaISO = dataInput.value;

  for (let i = 0; i < diaSemanaPrimeiro; i += 1) {
    const vazio = document.createElement('div');
    vazio.className = 'calendar-day outside-month';
    calGridEl.appendChild(vazio);
  }

  for (let dia = 1; dia <= diasNoMes; dia += 1) {
    const cell = document.createElement('div');
    cell.textContent = String(dia);
    cell.className = 'calendar-day';

    const dataISO = `${calCurrentYear}-${String(calCurrentMonth + 1).padStart(2, '0')}-${String(dia).padStart(2, '0')}`;
    const diaSemana = new Date(calCurrentYear, calCurrentMonth, dia).getDay(); // 0 (Dom) - 6 (Sáb)

    // Fins de semana (sábado e domingo) ficam desativados para seleção
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

      dataInput.value = dataISO;
      carregarHorariosDisponiveis(dataISO);

      document.querySelectorAll('.calendar-day.selected').forEach((el) => el.classList.remove('selected'));
      cell.classList.add('selected');
    });

    calGridEl.appendChild(cell);
  }

  marcarDiasSemHorario();
}

function marcarDiasSemHorario() {
  const cells = calGridEl.querySelectorAll('.calendar-day');

  cells.forEach((cell) => {
    const dataISO = cell.dataset.dateIso;
    if (!dataISO) return;

    fetch(`/api/mentorias/disponiveis?data=${encodeURIComponent(dataISO)}`)
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) return;

        const horarios = Array.isArray(payload.horarios) ? payload.horarios : [];
        if (horarios.length === 0) {
          cell.classList.add('sem-horario');
          cell.dataset.bloqueado = 'true';
        }
      })
      .catch(() => {
        // Em caso de erro, não alteramos o estado visual do dia
      });
  });
}

// Inicializar calendário ao carregar o script
inicializarCalendario();
