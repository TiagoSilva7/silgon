const express = require('express');
const path = require('path');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const nodemailer = require('nodemailer');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Servir frontend estático
const frontendPath = path.join(__dirname, '..', 'frontend');
app.use(express.static(frontendPath));

// Banco de dados SQLite (arquivo local, sem necessidade de servidor instalado)
const dbPath = path.join(__dirname, 'mentorias.db');
const db = new sqlite3.Database(dbPath, (err) => {
	if (err) {
		console.error('Erro ao conectar ao banco SQLite:', err.message);
	} else {
		console.log('Conectado ao banco SQLite em', dbPath);
	}
});

// Configuração opcional de e-mail (via variáveis de ambiente)
// Defina: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
// Opcional: SMTP_SECURE ('true'/'false'), SMTP_FROM, SMTP_TO
let mailTransporter = null;
if (process.env.SMTP_HOST && process.env.SMTP_PORT && process.env.SMTP_USER && process.env.SMTP_PASS) {
	mailTransporter = nodemailer.createTransport({
		host: process.env.SMTP_HOST,
		port: Number(process.env.SMTP_PORT),
		secure: process.env.SMTP_SECURE === 'true',
		auth: {
			user: process.env.SMTP_USER,
			pass: process.env.SMTP_PASS,
		},
	});

	mailTransporter.verify((err) => {
		if (err) {
			console.error('Falha ao verificar configuração de e-mail:', err.message);
			mailTransporter = null;
		} else {
			console.log('Transporte de e-mail configurado com sucesso.');
		}
	});
} else {
	console.log('Transporte de e-mail não configurado (variáveis de ambiente SMTP_* ausentes).');
}


function parseHoraParaMinutos(horaStr) {
	if (!horaStr || typeof horaStr !== 'string') return null;
	const partes = horaStr.split(':');
	if (partes.length !== 2) return null;
	const horas = Number(partes[0]);
	const minutos = Number(partes[1]);
	if (Number.isNaN(horas) || Number.isNaN(minutos)) return null;
	return horas * 60 + minutos;
}

// Criação das tabelas, se não existirem
db.serialize(() => {
	db.run(
		`CREATE TABLE IF NOT EXISTS mentorias (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			nome_completo TEXT NOT NULL,
			email TEXT NOT NULL,
			telefone TEXT NOT NULL,
			data TEXT NOT NULL,
			hora TEXT NOT NULL,
			assunto TEXT NOT NULL,
			criado_em TEXT NOT NULL
		)`
	);

	db.run(
		`CREATE TABLE IF NOT EXISTS bloqueios (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			data TEXT NOT NULL,
			hora TEXT NOT NULL,
			criado_em TEXT NOT NULL,
			UNIQUE (data, hora)
		)`
	);
});

// Rota para criar um novo agendamento de mentoria
app.post('/api/mentorias', (req, res) => {
	const { nomeCompleto, email, telefone, data, hora, assunto } = req.body;

	if (!nomeCompleto || !email || !telefone || !data || !hora || !assunto) {
		return res.status(400).json({ mensagem: 'Todos os campos são obrigatórios.' });
	}

	const inicioMinutos = parseHoraParaMinutos(hora);
	if (inicioMinutos === null) {
		return res.status(400).json({ mensagem: 'Horário inválido.' });
	}
	const fimMinutos = inicioMinutos + 60; // sempre 1 hora de duração

	// Verificar conflito de horário no mesmo dia.
	// Para mentorias existentes, checamos sobreposição de 1h.
	// Para bloqueios administrativos, consideramos conflito apenas
	// se a mesma hora de início estiver bloqueada.
	const selectSql = `
		SELECT hora, 'M' AS tipo FROM mentorias WHERE data = ?
		UNION ALL
		SELECT hora, 'B' AS tipo FROM bloqueios WHERE data = ?
	`;
	db.all(selectSql, [data, data], (err, rows) => {
		if (err) {
			console.error('Erro ao verificar conflitos:', err.message);
			return res.status(500).json({ mensagem: 'Erro ao verificar disponibilidade.' });
		}

		const conflito = rows.some((row) => {
			if (row.tipo === 'M') {
				const inicioExistente = parseHoraParaMinutos(row.hora);
				if (inicioExistente === null) return false;
				const fimExistente = inicioExistente + 60;
				// há conflito se os intervalos se sobrepõem
				return inicioMinutos < fimExistente && fimMinutos > inicioExistente;
			}
			// Para bloqueios administrativos, o conflito é apenas na mesma hora exata
			if (row.tipo === 'B') {
				return row.hora === hora;
			}
			return false;
		});

		if (conflito) {
			return res.status(409).json({ mensagem: 'Horário já reservado para esta data.' });
		}

		const insertSql = `INSERT INTO mentorias (nome_completo, email, telefone, data, hora, assunto, criado_em)
					 VALUES (?, ?, ?, ?, ?, ?, datetime('now'))`;

		db.run(insertSql, [nomeCompleto, email, telefone, data, hora, assunto], function (insertErr) {
			if (insertErr) {
				console.error('Erro ao inserir mentoria:', insertErr.message);
				return res.status(500).json({ mensagem: 'Erro ao salvar agendamento.' });
			}

			// Enviar e-mail de notificação (não bloqueia a resposta para o usuário)
			if (mailTransporter) {
				const para = process.env.SMTP_TO || 'tiago.silva@teradata.com';
				const de = process.env.SMTP_FROM || process.env.SMTP_USER;
				const assuntoEmail = `Novo agendamento de mentoria - ${data} ${hora}`;
				const corpoTexto = [
					'Novo agendamento de mentoria:',
					'',
					`Nome: ${nomeCompleto}`,
					`E-mail: ${email}`,
					`Telefone: ${telefone}`,
					`Data: ${data}`,
					`Horário: ${hora}`,
					`Assunto: ${assunto}`,
					'',
					`Criado em: ${new Date().toISOString()}`,
				].join('\n');

				mailTransporter.sendMail(
					{
						from: de,
						to: para,
						subject: assuntoEmail,
						text: corpoTexto,
					},
					(errEnvio) => {
						if (errEnvio) {
							console.error('Erro ao enviar e-mail de notificação:', errEnvio.message);
						} else {
							console.log('E-mail de notificação de mentoria enviado para', para);
						}
					}
				);
			}

			return res.status(201).json({
				mensagem: 'Agendamento realizado com sucesso!',
				id: this.lastID,
			});
		});
	});
});

// (Opcional) rota para listar agendamentos, caso queira consultar depois
app.get('/api/mentorias', (req, res) => {
	db.all('SELECT * FROM mentorias ORDER BY data, hora', [], (err, rows) => {
		if (err) {
			console.error('Erro ao consultar mentorias:', err.message);
			return res.status(500).json({ mensagem: 'Erro ao buscar agendamentos.' });
		}
		res.json(rows);
	});
});

// Rota para cancelar (remover) um agendamento de mentoria específico
app.delete('/api/mentorias/:id', (req, res) => {
	const { id } = req.params;
	const idNum = Number(id);
	if (!Number.isInteger(idNum) || idNum <= 0) {
		return res.status(400).json({ mensagem: 'ID inválido para cancelamento.' });
	}

	const sql = 'DELETE FROM mentorias WHERE id = ?';
	db.run(sql, [idNum], function (err) {
		if (err) {
			console.error('Erro ao cancelar mentoria:', err.message);
			return res.status(500).json({ mensagem: 'Erro ao cancelar mentoria.' });
		}

		if (this.changes === 0) {
			return res.status(404).json({ mensagem: 'Agendamento não encontrado.' });
		}

		return res.json({ mensagem: 'Agendamento cancelado com sucesso.' });
	});
});

// Rota para obter horários disponíveis em uma data específica
app.get('/api/mentorias/disponiveis', (req, res) => {
	const { data } = req.query;

	if (!data) {
		return res.status(400).json({ mensagem: 'Parâmetro "data" é obrigatório (YYYY-MM-DD).' });
	}

	// Gerar todos os horários possíveis de início (a cada 1 hora)
	// Blocos: das 09:00 às 11:00 e das 13:00 às 17:00, de 60 em 60 minutos
	const horariosPossiveis = [];
	// Manhã
	for (let minutos = 9 * 60; minutos <= 11 * 60; minutos += 60) {
		const h = String(Math.floor(minutos / 60)).padStart(2, '0');
		const m = String(minutos % 60).padStart(2, '0');
		horariosPossiveis.push(`${h}:${m}`);
	}
	// Tarde
	for (let minutos = 13 * 60; minutos <= 17 * 60; minutos += 60) {
		const h = String(Math.floor(minutos / 60)).padStart(2, '0');
		const m = String(minutos % 60).padStart(2, '0');
		horariosPossiveis.push(`${h}:${m}`);
	}

	const selectSql = `
		SELECT hora, 'M' AS tipo FROM mentorias WHERE data = ?
		UNION ALL
		SELECT hora, 'B' AS tipo FROM bloqueios WHERE data = ?
	`;
	db.all(selectSql, [data, data], (err, rows) => {
		if (err) {
			console.error('Erro ao buscar horários ocupados:', err.message);
			return res.status(500).json({ mensagem: 'Erro ao buscar horários disponíveis.' });
		}

		const horasMentorias = rows.filter((row) => row.tipo === 'M').map((row) => row.hora).filter(Boolean);
		const horasBloqueios = rows.filter((row) => row.tipo === 'B').map((row) => row.hora).filter(Boolean);

		const disponiveis = horariosPossiveis.filter((horaInicio) => {
			const inicioMinutos = parseHoraParaMinutos(horaInicio);
			const fimMinutos = inicioMinutos + 60;

			// Mentorias bloqueiam qualquer horário que sobreponha 1h
			const conflitaComMentoria = horasMentorias.some((horaOcupada) => {
				const inicioExistente = parseHoraParaMinutos(horaOcupada);
				if (inicioExistente === null) return false;
				const fimExistente = inicioExistente + 60;
				return inicioMinutos < fimExistente && fimMinutos > inicioExistente;
			});

			// Bloqueios administrativos removem apenas o horário exato
			const bloqueadoAdmin = horasBloqueios.includes(horaInicio);

			return !conflitaComMentoria && !bloqueadoAdmin;
		});

		return res.json({ data, horarios: disponiveis });
	});
});

// Rotas administrativas para gerenciamento de bloqueios de horários
// Obtém os horários bloqueados para uma data específica
app.get('/api/bloqueios', (req, res) => {
	const { data } = req.query;

	if (!data) {
		return res.status(400).json({ mensagem: 'Parâmetro "data" é obrigatório (YYYY-MM-DD).' });
	}

	const sql = 'SELECT hora FROM bloqueios WHERE data = ? ORDER BY hora';
	db.all(sql, [data], (err, rows) => {
		if (err) {
			console.error('Erro ao buscar bloqueios:', err.message);
			return res.status(500).json({ mensagem: 'Erro ao buscar bloqueios.' });
		}

		const horas = rows.map((row) => row.hora).filter(Boolean);
		return res.json({ data, bloqueios: horas });
	});
});

// Obtém todos os bloqueios cadastrados (resumo geral)
app.get('/api/bloqueios/todos', (req, res) => {
	const sql = 'SELECT data, hora FROM bloqueios ORDER BY data, hora';
	db.all(sql, [], (err, rows) => {
		if (err) {
			console.error('Erro ao buscar todos os bloqueios:', err.message);
			return res.status(500).json({ mensagem: 'Erro ao buscar resumo de bloqueios.' });
		}

		const bloqueios = (rows || []).map((row) => ({ data: row.data, hora: row.hora })).filter((b) => b.data && b.hora);
		return res.json({ bloqueios });
	});
});

// Cria novos bloqueios para uma data (uma ou mais horas)
app.post('/api/bloqueios', (req, res) => {
	const { data, horas } = req.body;

	if (!data || !Array.isArray(horas) || horas.length === 0) {
		return res.status(400).json({ mensagem: 'Informe a data e ao menos um horário para bloqueio.' });
	}

	const horasValidas = horas.filter((horaStr) => parseHoraParaMinutos(horaStr) !== null);
	if (horasValidas.length === 0) {
		return res.status(400).json({ mensagem: 'Nenhum horário válido informado.' });
	}

	db.serialize(() => {
		const stmt = db.prepare(
			`INSERT OR IGNORE INTO bloqueios (data, hora, criado_em)
			 VALUES (?, ?, datetime('now'))`
		);

		for (const hora of horasValidas) {
			stmt.run([data, hora]);
		}

		stmt.finalize((err) => {
			if (err) {
				console.error('Erro ao salvar bloqueios:', err.message);
				return res.status(500).json({ mensagem: 'Erro ao salvar bloqueios.' });
			}
			return res.status(201).json({ mensagem: 'Bloqueios salvos com sucesso.' });
		});
	});
});

// Remove um bloqueio específico de data/hora
app.delete('/api/bloqueios', (req, res) => {
	const { data, hora } = req.body;

	if (!data || !hora) {
		return res.status(400).json({ mensagem: 'Informe data e hora do bloqueio a ser removido.' });
	}

	const sql = 'DELETE FROM bloqueios WHERE data = ? AND hora = ?';
	db.run(sql, [data, hora], function (err) {
		if (err) {
			console.error('Erro ao remover bloqueio:', err.message);
			return res.status(500).json({ mensagem: 'Erro ao remover bloqueio.' });
		}

		if (this.changes === 0) {
			return res.status(404).json({ mensagem: 'Bloqueio não encontrado.' });
		}

		return res.json({ mensagem: 'Bloqueio removido com sucesso.' });
	});
});

// Iniciar servidor
app.listen(PORT, () => {
	console.log(`Servidor rodando em http://localhost:${PORT}`);
});

