from datetime import datetime, timedelta, timezone
import os
from threading import Timer
import webbrowser
from flask import Flask, redirect, render_template_string, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///banco_horas_profissional.db"
)
app.config["SECRET_KEY"] = "chave-secreta-profissional-2026"
db = SQLAlchemy(app)

# Fuso horário de Brasília (UTC-3)
fuso_brasilia = timezone(timedelta(hours=-3))


class Tecnico(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  nome = db.Column(db.String(100), nullable=False, unique=True)
  translado_tempo = db.Column(db.String(5), default="01:30")


class LocalAtendimento(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  nome = db.Column(db.String(150), nullable=False, unique=True)


class Registro(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  tecnico = db.Column(db.String(100), nullable=False)
  data = db.Column(db.String(10), nullable=False)
  entrada = db.Column(db.String(5), nullable=False)
  saida = db.Column(db.String(5), nullable=False)
  almoço_inicio = db.Column(db.String(5), nullable=True)
  almoço_fim = db.Column(db.String(5), nullable=True)

  banco_inicio = db.Column(db.String(5), default="00:00")
  banco_final = db.Column(db.String(5), default="00:00")

  tipo_credito = db.Column(db.String(30), nullable=False)
  percentual_extra = db.Column(db.Integer, default=0)

  minutos_calculados = db.Column(db.Integer, default=0)
  horas_formatadas = db.Column(db.String(10), default="00:00")

  ferias_inicio = db.Column(db.String(10), nullable=True)
  ferias_fim = db.Column(db.String(10), nullable=True)
  ferias_dias = db.Column(db.Integer, default=0)

  local_atendimento = db.Column(db.String(500), nullable=True)

  chk_translado = db.Column(db.Boolean, default=False)
  chk_dia = db.Column(db.Boolean, default=False)
  chk_noite = db.Column(db.Boolean, default=False)


with app.app_context():
  db.create_all()

TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Sistema Completo - Banco de Horas & Extras</title>
    <style>
        :root {
            --primary: #1e293b;
            --accent: #2563eb;
            --success: #16a34a;
            --danger: #dc2626;
            --border: #cbd5e1;
        }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }
        .container { max-width: 1300px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        h2 { color: var(--primary); text-align: center; margin-bottom: 20px; }
        .nav-tabs { display: flex; gap: 10px; margin-bottom: 25px; border-bottom: 2px solid var(--border); padding-bottom: 10px; }
        .nav-tabs a { text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; font-size: 14px; background: #e2e8f0; color: var(--primary); transition: 0.2s; }
        .nav-tabs a.active { background: var(--accent); color: white; }
        .grid-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; background: #f1f5f9; padding: 20px; border-radius: 8px; border-left: 5px solid var(--accent); }
        .filter-box { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) auto; gap: 15px; margin-bottom: 25px; background: #e2e8f0; padding: 15px; border-radius: 8px; align-items: end; }
        .full-width { grid-column: 1 / -1; }
        label { font-weight: 600; font-size: 13px; color: #475569; display: block; margin-bottom: 5px; }
        input, select, textarea { padding: 10px; width: 100%; box-sizing: border-box; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: white; }

        .search-container { position: relative; }
        .search-results { position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid var(--border); border-top: none; max-height: 150px; overflow-y: auto; z-index: 10; display: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .search-result-item { padding: 8px 12px; cursor: pointer; font-size: 13px; }
        .search-result-item:hover { background: #e2e8f0; }
        
        .tags-container { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; min-height: 35px; padding: 6px; background: white; border: 1px solid var(--border); border-radius: 6px; }
        .tag { background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
        .tag .remove-tag { cursor: pointer; font-weight: bold; color: #dc2626; }

        button { background: var(--accent); color: white; border: none; padding: 12px 20px; font-size: 15px; font-weight: 600; border-radius: 6px; cursor: pointer; transition: 0.2s; }
        button:hover { background: #1d4ed8; }
        .btn-edit { background: #eab308; padding: 6px 12px; font-size: 12px; border-radius: 4px; color: white; text-decoration: none; display: inline-block; font-weight: 600; }
        .btn-edit:hover { background: #ca8a04; }
        .btn-delete { background: #dc2626; padding: 6px 12px; font-size: 12px; border-radius: 4px; color: white; text-decoration: none; display: inline-block; font-weight: 600; margin-left: 4px; }
        .btn-delete:hover { background: #b91c1c; }
        .btn-success { background: var(--success); width: 100%; }
        .btn-success:hover { background: #15803d; }
        .btn-filter { background: var(--primary); height: 42px; }
        .actions-bar { display: flex; justify-content: space-between; align-items: center; margin-top: 30px; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        th, td { border: 1px solid var(--border); padding: 10px 12px; text-align: center; font-size: 13px; }
        th { background-color: var(--primary); color: white; font-weight: 600; }
        tr:nth-child(even) { background-color: #f8fafc; }
        .badge { padding: 4px 8px; border-radius: 20px; font-size: 11px; font-weight: 600; display: inline-block; }
        .b-banco { background: #e0f2fe; color: #0369a1; }
        .b-extra { background: #fef9c3; color: #854d0e; }
        .btn-pdf { background: #7c3aed; display: inline-flex; align-items: center; gap: 6px; text-decoration: none; padding: 10px 18px; border-radius: 6px; color: white; font-weight: 600; cursor: pointer; }
        .btn-pdf:hover { background: #6d28d9; }
        
        .resumo-box { display: flex; gap: 20px; margin-bottom: 20px; background: #e2e8f0; padding: 15px; border-radius: 8px; font-weight: bold; }
        .resumo-item { flex: 1; text-align: center; background: white; padding: 10px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }

        .assinaturas-container {
            display: none;
            margin-top: 80px;
            justify-content: space-around;
            page-break-inside: avoid;
        }
        .linha-assinatura {
            width: 40%;
            text-align: center;
            border-top: 1px solid #333;
            padding-top: 8px;
            font-size: 13px;
            font-weight: 600;
            color: #000;
        }

        @media print {
            body { background: white; padding: 0; }
            .container { box-shadow: none; padding: 0; max-width: 100%; }
            form, .nav-tabs, .filter-box, .actions-bar, th:last-child, td:last-child { display: none !important; }
            table { border: 1px solid #333; }
            th, td { border: 1px solid #333; color: black; font-size: 11px; }
            .assinaturas-container { display: flex !important; }
        }
    </style>
    <script>
        function alternarCamposExtra() {
            var tipo = document.getElementById("tipo_credito").value;
            var divPercentual = document.getElementById("campo_percentual");
            if (tipo === "Hora Extra") {
                divPercentual.style.display = "block";
            } else {
                divPercentual.style.display = "none";
            }
        }

        function calcularDiasFerias() {
            let ini = document.getElementById("ferias_inicio").value;
            let fim = document.getElementById("ferias_fim").value;
            let campoDias = document.getElementById("ferias_dias");

            if (ini && fim) {
                let d1 = new Date(ini);
                let d2 = new Date(fim);
                if (d2 >= d1) {
                    let diffTime = Math.abs(d2 - d1);
                    let diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
                    campoDias.value = diffDays;
                } else {
                    campoDias.value = 0;
                }
            }
        }

        const todosClientes = [
            {% for l in locais %}"{{ l.nome }}"{% if not loop.last %},{% endif %}{% endfor %}
        ];

        function filtrarClientes() {
            let input = document.getElementById("inputBuscaCliente").value.toLowerCase();
            let listaBox = document.getElementById("listaResultadosBusca");
            listaBox.innerHTML = "";
            
            if (input.trim() === "") {
                listaBox.style.display = "none";
                return;
            }

            let filtrados = todosClientes.filter(c => c.toLowerCase().includes(input));
            
            if (filtrados.length > 0) {
                listaBox.style.display = "block";
                filtrados.forEach(cliente => {
                    let div = document.createElement("div");
                    div.className = "search-result-item";
                    div.innerText = cliente;
                    div.onclick = function() {
                        adicionarClienteTag(cliente);
                        document.getElementById("inputBuscaCliente").value = "";
                        listaBox.style.display = "none";
                    };
                    listaBox.appendChild(div);
                });
            } else {
                listaBox.style.display = "none";
            }
        }

        function adicionarClienteTag(nomeCliente) {
            let container = document.getElementById("tagsContainer");
            let inputsHidden = document.getElementById("hiddenInputsClientes");
            
            let existentes = Array.from(inputsHidden.getElementsByTagName("input")).map(i => i.value);
            if (existentes.includes(nomeCliente)) return;

            let tag = document.createElement("div");
            tag.className = "tag";
            tag.innerHTML = `${nomeCliente} <span class="remove-tag" onclick="removerTag(this, '${nomeCliente}')">&times;</span>`;
            container.appendChild(tag);

            let inputHidden = document.createElement("input");
            inputHidden.type = "hidden";
            inputHidden.name = "locais_atendimento";
            inputHidden.value = nomeCliente;
            inputsHidden.appendChild(inputHidden);
        }

        function removerTag(elementoTag, nomeCliente) {
            elementoTag.parentElement.remove();
            let inputsHidden = document.getElementById("hiddenInputsClientes");
            let inputs = inputsHidden.getElementsByTagName("input");
            for (let i = 0; i < inputs.length; i++) {
                if (inputs[i].value === nomeCliente) {
                    inputs[i].remove();
                    break;
                }
            }
        }
    </script>
</head>
<body>
    <div class="container">
        <h2>Controle Profissional de Banco de Horas & Extras</h2>
        
        <div class="nav-tabs">
            <a href="/" class="{% if not page or page == 'lancamentos' %}active{% endif %}">📋 Lançamentos e Atendimentos</a>
            <a href="/tecnicos" class="{% if page == 'tecnicos' %}active{% endif %}">👥 Gerenciar Técnicos</a>
            <a href="/locais" class="{% if page == 'locais' %}active{% endif %}">🏢 Gerenciar Clientes ({{ locais|length }})</a>
        </div>

        {% if page == 'tecnicos' %}
            <h3>Cadastro e Gestão de Técnicos</h3>
            <form method="POST" action="/tecnicos">
                <div class="grid-form">
                    <div>
                        <label>Nome Completo do Técnico:</label>
                        <input type="text" name="nome" placeholder="Ex: Carlos Eduardo" required>
                    </div>
                    <div>
                        <label>Tempo de Translado (Livre, ex: 01:30):</label>
                        <input type="text" name="translado_tempo" value="01:30" placeholder="HH:MM" required>
                    </div>
                    <div class="full-width">
                        <button type="submit" class="btn-success">Cadastrar Técnico</button>
                    </div>
                </div>
            </form>

            <h3>Técnicos Ativos (Total: {{ tecnicos|length }})</h3>
            <table>
                <tr>
                    <th>Nome do Técnico</th>
                    <th>Translado Padrão</th>
                    <th>Ações</th>
                </tr>
                {% for t in tecnicos %}
                <tr>
                    <td><b>{{ t.nome }}</b></td>
                    <td>{{ t.translado_tempo }}</td>
                    <td><a href="/tecnico/excluir/{{ t.id }}" class="btn-edit" style="background:#dc2626;" onclick="return confirm('Deseja excluir?')">Excluir</a></td>
                </tr>
                {% else %}
                <tr><td colspan="3" style="padding: 20px; color: #64748b;">Nenhum técnico cadastrado.</td></tr>
                {% endfor %}
            </table>

        {% elif page == 'locais' %}
            <h3>Cadastro de Clientes / Locais de Atendimento</h3>
            <form method="POST" action="/locais">
                <div class="grid-form">
                    <div class="full-width">
                        <label>Nome do Cliente / Local:</label>
                        <input type="text" name="nome_local" placeholder="Ex: Cliente A, Cliente B, etc." required>
                    </div>
                    <div class="full-width">
                        <button type="submit" class="btn-success">Cadastrar Cliente</button>
                    </div>
                </div>
            </form>

            <h3>Clientes Cadastrados (Total: {{ locais|length }})</h3>
            <table>
                <tr>
                    <th>Nome do Cliente / Local</th>
                    <th>Ações</th>
                </tr>
                {% for l in locais %}
                <tr>
                    <td><b>{{ l.nome }}</b></td>
                    <td><a href="/local/excluir/{{ l.id }}" class="btn-edit" style="background:#dc2626;" onclick="return confirm('Deseja excluir?')">Excluir</a></td>
                </tr>
                {% else %}
                <tr><td colspan="2" style="padding: 20px; color: #64748b;">Nenhum cliente cadastrado.</td></tr>
                {% endfor %}
            </table>

        {% elif page == 'editar' %}
            <h3>Editar Lançamento #{{ registro_edit.id }}</h3>
            <form method="POST" action="/editar/{{ registro_edit.id }}">
                <div class="grid-form">
                    <div>
                        <label>Técnico:</label>
                        <input type="text" name="tecnico" value="{{ registro_edit.tecnico }}" required>
                    </div>
                    <div>
                        <label>Data:</label>
                        <input type="date" name="data" value="{{ registro_edit.data }}" required>
                    </div>
                    <div>
                        <label>Horário de Entrada:</label>
                        <input type="time" name="entrada" value="{{ registro_edit.entrada }}" required>
                    </div>
                    <div>
                        <label>Início do Almoço:</label>
                        <input type="time" name="almoco_inicio" value="{{ registro_edit.almoço_inicio }}">
                    </div>
                    <div>
                        <label>Fim do Almoço:</label>
                        <input type="time" name="almoco_fim" value="{{ registro_edit.almoço_fim }}">
                    </div>
                    <div>
                        <label>Horário de Saída (Ex: 02:20 madrugada):</label>
                        <input type="time" name="saida" value="{{ registro_edit.saida }}" required>
                    </div>

                    <div>
                        <label>Banco de Horas (Início):</label>
                        <input type="time" name="banco_inicio" value="{{ registro_edit.banco_inicio }}">
                    </div>
                    <div>
                        <label>Banco de Horas (Final):</label>
                        <input type="time" name="banco_final" value="{{ registro_edit.banco_final }}">
                    </div>

                    <div>
                        <label>Forma de Pagamento:</label>
                        <select name="tipo_credito" id="tipo_credito" onchange="alternarCamposExtra()" required>
                            <option value="Banco de Horas" {% if registro_edit.tipo_credito == 'Banco de Horas' %}selected{% endif %}>Banco de Horas</option>
                            <option value="Hora Extra" {% if registro_edit.tipo_credito == 'Hora Extra' %}selected{% endif %}>Hora Extra</option>
                        </select>
                    </div>
                    <div id="campo_percentual" style="display: {% if registro_edit.tipo_credito == 'Hora Extra' %}block{% else %}none{% endif %};">
                        <label>Percentual Extra (%):</label>
                        <input type="number" name="percentual_extra" value="{{ registro_edit.percentual_extra }}" min="0" placeholder="Ex: 50 ou 100">
                    </div>
                    <div>
                        <label>Férias Início:</label>
                        <input type="date" id="ferias_inicio" name="ferias_inicio" value="{{ registro_edit.ferias_inicio }}" onchange="calcularDiasFerias()">
                    </div>
                    <div>
                        <label>Férias Fim:</label>
                        <input type="date" id="ferias_fim" name="ferias_fim" value="{{ registro_edit.ferias_fim }}" onchange="calcularDiasFerias()">
                    </div>
                    <div>
                        <label>Dias de Férias (Automático):</label>
                        <input type="number" id="ferias_dias" name="ferias_dias" value="{{ registro_edit.ferias_dias }}" readonly style="background: #f1f5f9;">
                    </div>

                    <div class="full-width" style="background: #e2e8f0; padding: 15px; border-radius: 6px;">
                        <label style="font-weight: bold; color: #1e293b; margin-bottom: 10px; display: block;">🚗 Opções Especiais de Translado:</label>
                        <div style="display: flex; gap: 30px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px;">
                                <input type="checkbox" name="chk_translado" value="1" {% if registro_edit.chk_translado %}checked{% endif %} style="width: 18px; height: 18px;">
                                **1 - Translado** (Soma translado à saída; zera se ultrapassar 17:45)
                            </label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px;">
                                <input type="checkbox" name="chk_dia" value="1" {% if registro_edit.chk_dia %}checked{% endif %} style="width: 18px; height: 18px;">
                                **2 - Dia** (Viagem de manhã antecipada)
                            </label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px;">
                                <input type="checkbox" name="chk_noite" value="1" {% if registro_edit.chk_noite %}checked{% endif %} style="width: 18px; height: 18px;">
                                **3 - Noite** (Retorno tardio após 17:45)
                            </label>
                        </div>
                    </div>

                    <div class="full-width">
                        <label>Clientes Atendidos (Pesquise para adicionar):</label>
                        <div class="search-container">
                            <input type="text" id="inputBuscaCliente" onkeyup="filtrarClientes()" placeholder="Digite o nome do cliente para buscar na base...">
                            <div id="listaResultadosBusca" class="search-results"></div>
                        </div>
                        <div id="tagsContainer" class="tags-container">
                            {% if registro_edit.local_atendimento %}
                                {% for cliente in registro_edit.local_atendimento.split(', ') %}
                                <div class="tag">{{ cliente }} <span class="remove-tag" onclick="removerTag(this, '${cliente}')">&times;</span></div>
                                {% endfor %}
                            {% endif %}
                        </div>
                        <div id="hiddenInputsClientes">
                            {% if registro_edit.local_atendimento %}
                                {% for cliente in registro_edit.local_atendimento.split(', ') %}
                                <input type="hidden" name="locais_atendimento" value="{{ cliente }}">
                                {% endfor %}
                            {% endif %}
                        </div>
                    </div>
                    <div class="full-width">
                        <button type="submit" class="btn-success">Salvar Alterações</button>
                    </div>
                </div>
            </form>
        {% else %}
            <form method="POST" action="/">
                <div class="grid-form">
                    <div>
                        <label>Técnico:</label>
                        <select name="tecnico" required>
                            <option value="">Selecione o Técnico...</option>
                            {% for t in tecnicos %}
                            <option value="{{ t.nome }}">{{ t.nome }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div>
                        <label>Data (Brasília):</label>
                        <input type="date" name="data" value="{{ data_atual }}" required>
                    </div>
                    <div>
                        <label>Horário de Entrada:</label>
                        <input type="time" name="entrada" value="08:00" required>
                    </div>
                    <div>
                        <label>Início do Almoço (Opcional):</label>
                        <input type="time" name="almoco_inicio" value="12:00">
                    </div>
                    <div>
                        <label>Fim do Almoço (Opcional):</label>
                        <input type="time" name="almoco_fim" value="13:00">
                    </div>
                    <div>
                        <label>Horário de Saída (Ex: 02:20 madrugada):</label>
                        <input type="time" name="saida" value="17:45" required>
                    </div>
                    
                    <div>
                        <label>Banco de Horas (Início):</label>
                        <input type="time" name="banco_inicio" value="00:00">
                    </div>
                    <div>
                        <label>Banco de Horas (Final):</label>
                        <input type="time" name="banco_final" value="00:00">
                    </div>

                    <div>
                        <label>Forma de Pagamento:</label>
                        <select name="tipo_credito" id="tipo_credito" onchange="alternarCamposExtra()" required>
                            <option value="Banco de Horas">Banco de Horas (Conta Corrente Horas)</option>
                            <option value="Hora Extra">Hora Extra (Manual %)</option>
                        </select>
                    </div>

                    <div id="campo_percentual" style="display: none;">
                        <label>Digite a Porcentagem (%):</label>
                        <input type="number" name="percentual_extra" value="50" min="0" placeholder="Ex: 50 ou 100">
                    </div>

                    <div>
                        <label>Férias (Data Início):</label>
                        <input type="date" id="ferias_inicio" name="ferias_inicio" onchange="calcularDiasFerias()">
                    </div>
                    <div>
                        <label>Férias (Data Fim):</label>
                        <input type="date" id="ferias_fim" name="ferias_fim" onchange="calcularDiasFerias()">
                    </div>
                    <div>
                        <label>Férias (Total Dias Automático):</label>
                        <input type="number" id="ferias_dias" name="ferias_dias" value="0" readonly style="background: #f1f5f9;">
                    </div>

                    <div class="full-width" style="background: #e2e8f0; padding: 15px; border-radius: 6px;">
                        <label style="font-weight: bold; color: #1e293b; margin-bottom: 10px; display: block;">🚗 Opções Especiais de Translado:</label>
                        <div style="display: flex; gap: 30px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px;">
                                <input type="checkbox" name="chk_translado" value="1" style="width: 18px; height: 18px;">
                                **1 - Translado** (Soma translado à saída; zera se ultrapassar 17:45)
                            </label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px;">
                                <input type="checkbox" name="chk_dia" value="1" style="width: 18px; height: 18px;">
                                **2 - Dia** (Viagem de manhã antecipada)
                            </label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px;">
                                <input type="checkbox" name="chk_noite" value="1" style="width: 18px; height: 18px;">
                                **3 - Noite** (Retorno tardio após 17:45)
                            </label>
                        </div>
                    </div>

                    <div class="full-width">
                        <label>Clientes Atendidos (Digite para buscar e setar):</label>
                        <div class="search-container">
                            <input type="text" id="inputBuscaCliente" onkeyup="filtrarClientes()" placeholder="🔍 Digite para pesquisar nos clientes cadastrados...">
                            <div id="listaResultadosBusca" class="search-results"></div>
                        </div>
                        <div id="tagsContainer" class="tags-container"></div>
                        <div id="hiddenInputsClientes"></div>
                    </div>

                    <div class="full-width">
                        <button type="submit" class="btn-success">Salvar e Registrar</button>
                    </div>
                </div>
            </form>

            <!-- FILTRO MENSAL E POR TÉCNICO -->
            <form method="GET" action="/">
                <div class="filter-box">
                    <div>
                        <label>Filtrar por Mês:</label>
                        <input type="month" name="mes_filtro" value="{{ filtro_mes }}">
                    </div>
                    <div>
                        <label>Filtrar por Técnico:</label>
                        <select name="tecnico_filtro">
                            <option value="">Todos os Técnicos</option>
                            {% for t in tecnicos %}
                            <option value="{{ t.nome }}" {% if filtro_tecnico == t.nome %}selected{% endif %}>{{ t.nome }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div>
                        <button type="submit" class="btn-filter" style="width:100%;">Filtrar Relatório</button>
                    </div>
                </div>
            </form>

            <div class="resumo-box">
                <div class="resumo-item" style="color: #16a34a;">Total Positivo: {{ total_positivo_fmt }}</div>
                <div class="resumo-item" style="color: #dc2626;">Total Negativo: {{ total_negativo_fmt }}</div>
                <div class="resumo-item" style="color: #2563eb;">Subtotal Líquido: {{ subtotal_fmt }}</div>
            </div>

            <div class="actions-bar">
                <h3>Histórico de Lançamentos (Total Filtrado: {{ registros|length }})</h3>
                <button onclick="window.print()" class="btn-pdf">📄 Imprimir / Salvar Relatório PDF</button>
            </div>

            <table>
                <tr>
                    <th>Técnico</th>
                    <th>Data</th>
                    <th>Período</th>
                    <th>Banco de Horas (Início / Fim)</th>
                    <th>Forma Pagamento</th>
                    <th>Balanço Horas</th>
                    <th>Férias</th>
                    <th>Clientes Atendidos</th>
                    <th>Ações</th>
                </tr>
                {% for reg in registros %}
                <tr>
                    <td><b>{{ reg.tecnico }}</b></td>
                    <td>{{ reg.data }}</td>
                    <td>
                        {{ reg.entrada }} às {{ reg.saida }}
                        {% if reg.chk_translado or reg.chk_dia or reg.chk_noite %}
                            <br><small style="color: #2563eb; font-weight: bold;">
                                🚗 {% if reg.chk_translado %}Translado{% endif %}{% if reg.chk_dia %} Dia{% endif %}{% if reg.chk_noite %} Noite{% endif %}
                            </small>
                        {% endif %}
                    </td>
                    <td>{{ reg.banco_inicio }} às {{ reg.banco_final }}</td>
                    <td>
                        <span class="badge {% if reg.tipo_credito == 'Banco de Horas' %}b-banco{% else %}b-extra{% endif %}">
                            {{ reg.tipo_credito }} {% if reg.tipo_credito == 'Hora Extra' %}({{ reg.percentual_extra }}%){% endif %}
                        </span>
                    </td>
                    <td><b style="color: {% if reg.minutos_calculados > 0 %}#16a34a{% elif reg.minutos_calculados < 0 %}#dc2626{% else %}#333{% endif %};">{{ reg.horas_formatadas }}</b></td>
                    <td><small>{% if reg.ferias_dias > 0 %}{{ reg.ferias_inicio }} a {{ reg.ferias_fim }} ({{ reg.ferias_dias }}d টাইমস){% else %}-{% endif %}</small></td>
                    <td><b>{{ reg.local_atendimento or '-' }}</b></td>
                    <td>
                        <a href="/editar/{{ reg.id }}" class="btn-edit">Editar</a>
                        <a href="/excluir/{{ reg.id }}" class="btn-delete" onclick="return confirm('Tem certeza que deseja excluir este lançamento?')">Excluir</a>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="9" style="padding: 20px; color: #64748b;">Nenhum lançamento encontrado para este filtro.</td></tr>
                {% endfor %}
            </table>

            <div class="assinaturas-container">
                <div class="linha-assinatura">
                    Assinatura do Técnico
                </div>
                <div class="linha-assinatura">
                    Supervisão Técnica
                </div>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""


def converter_tempo_minutos(tempo_str):
  try:
    partes = tempo_str.strip().split(":")
    return int(partes[0]) * 60 + int(partes[1])
  except:
    return 90


@app.route("/", methods=["GET", "POST"])
def index():
  tecnicos = Tecnico.query.order_by(Tecnico.nome).all()
  locais = LocalAtendimento.query.order_by(LocalAtendimento.nome).all()
  data_hoje = datetime.now(fuso_brasilia).strftime("%Y-%m-%d")
  mes_atual = datetime.now(fuso_brasilia).strftime("%Y-%m")

  if request.method == "POST":
    tecnico_nome = request.form["tecnico"]
    data = request.form["data"]
    entrada_str = request.form["entrada"]
    saida_str = request.form["saida"]
    a_ini = request.form.get("almoco_inicio", "")
    a_fim = request.form.get("almoco_fim", "")

    b_inicio = request.form.get("banco_inicio", "00:00")
    b_final = request.form.get("banco_final", "00:00")

    tipo_credito = request.form["tipo_credito"]
    percentual = int(request.form.get("percentual_extra") or 0)

    f_inicio = request.form.get("ferias_inicio", "")
    f_fim = request.form.get("ferias_fim", "")
    f_dias = int(request.form.get("ferias_dias") or 0)

    chk_translado = True if request.form.get("chk_translado") else False
    chk_dia = True if request.form.get("chk_dia") else False
    chk_noite = True if request.form.get("chk_noite") else False

    tecnico_obj = Tecnico.query.filter_by(nome=tecnico_nome).first()
    translado_str = (
        tecnico_obj.translado_tempo if tecnico_obj and tecnico_obj.translado_tempo else "01:30"
    )
    translado_minutos = converter_tempo_minutos(translado_str)

    locais_selecionados = request.form.getlist("locais_atendimento")
    local_atendimento_str = (
        ", ".join(locais_selecionados) if locais_selecionados else ""
    )

    fmt = "%H:%M"
    total_minutos = 0

    if b_inicio != "00:00" and b_final != "00:00":
      t_bini = datetime.strptime(b_inicio, fmt)
      t_bfim = datetime.strptime(b_final, fmt)
      if t_bfim >= t_bini:
        dif = t_bfim - t_bini
      else:
        dif = (
            (datetime.strptime("23:59", fmt) - t_bini)
            + (t_bfim - datetime.strptime("00:00", fmt))
            + timedelta(minutes=1)
        )
      total_minutos = int(dif.total_seconds() // 60)
    else:
      t_ent = datetime.strptime(entrada_str, fmt)
      t_sai = datetime.strptime(saida_str, fmt)
      limite_comercial = datetime.strptime("17:45", fmt)

      # Virada de dia (ex: 13:00 até 02:20 da madrugada)
      if t_sai < t_ent:
        t_sai = t_sai + timedelta(days=1)

      # Regra 1: Translado
      if chk_translado:
        t_sai_com_translado = t_sai + timedelta(minutes=translado_minutos)
        limite_dt = datetime.combine(t_sai.date(), limite_comercial.time())
        if t_sai_com_translado > limite_dt and t_sai >= limite_dt:
          total_minutos = 0
          t_sai = t_ent
        else:
          t_sai = t_sai_com_translado

      # Regra 2: Dia (Viagem antecipada de manhã)
      if chk_dia:
        t_ent = t_ent + timedelta(minutes=translado_minutos)

      # Regra 3: Noite (Retorno tardio após 17:45)
      if chk_noite:
        t_sai = t_sai - timedelta(minutes=translado_minutos)

      if not (chk_translado and total_minutos == 0):
        if t_sai >= t_ent:
          dif = t_sai - t_ent
        else:
          dif = timedelta(0)

        if a_ini and a_fim:
          t_aini = datetime.strptime(a_ini, fmt)
          t_afim = datetime.strptime(a_fim, fmt)
          if t_afim < t_aini:
            t_afim = t_afim + timedelta(days=1)
          if t_afim > t_aini:
            dif_almoco = t_afim - t_aini
            if dif > dif_almoco:
              dif = dif - dif_almoco

        trabalhado_minutos = int(dif.total_seconds() // 60)
        jornada_padrao_minutos = 525  # 8h45m (08:00 às 17:45)
        total_minutos = trabalhado_minutos - jornada_padrao_minutos

    saldo_minutos = total_minutos
    sinal = "+" if saldo_minutos > 0 else ("-" if saldo_minutos < 0 else "")
    m_abs = abs(saldo_minutos)
    h_fmt = (
        f"{sinal}{m_abs // 60:02d}:{m_abs % 60:02d}"
        if saldo_minutos != 0
        else "00:00"
    )

    novo = Registro(
        tecnico=tecnico_nome,
        data=data,
        entrada=entrada_str,
        saida=saida_str,
        almoço_inicio=a_ini,
        almoço_fim=a_fim,
        banco_inicio=b_inicio,
        banco_final=b_final,
        tipo_credito=tipo_credito,
        percentual_extra=percentual if tipo_credito == "Hora Extra" else 0,
        minutos_calculados=saldo_minutos,
        horas_formatadas=h_fmt,
        ferias_inicio=f_inicio,
        ferias_fim=f_fim,
        ferias_dias=f_dias,
        local_atendimento=local_atendimento_str,
        chk_translado=chk_translado,
        chk_dia=chk_dia,
        chk_noite=chk_noite,
    )
    db.session.add(novo)
    db.session.commit()
    return redirect(url_for("index"))

  filtro_mes = request.args.get("mes_filtro", mes_atual)
  filtro_tecnico = request.args.get("tecnico_filtro", "")

  query = Registro.query
  if filtro_mes:
    query = query.filter(Registro.data.like(f"{filtro_mes}%"))
  if filtro_tecnico:
    query = query.filter(Registro.tecnico == filtro_tecnico)

  registros = query.order_by(Registro.data.desc(), Registro.id.desc()).all()

  min_positivo = sum(
      r.minutos_calculados for r in registros if r.minutos_calculados > 0
  )
  min_negativo = sum(
      abs(r.minutos_calculados) for r in registros if r.minutos_calculados < 0
  )
  subtotal_minutos = sum(r.minutos_calculados for r in registros)

  def formatar_min_total(m):
    s = "+" if m > 0 else ("-" if m < 0 else "")
    m_a = abs(m)
    return f"{s}{m_a // 60:02d}:{m_a % 60:02d} ({m} min)"

  return render_template_string(
      TEMPLATE,
      tecnicos=tecnicos,
      locais=locais,
      registros=registros,
      data_atual=data_hoje,
      page="lancamentos",
      filtro_mes=filtro_mes,
      filtro_tecnico=filtro_tecnico,
      total_positivo_fmt=formatar_min_total(min_positivo),
      total_negativo_fmt=formatar_min_total(min_negativo),
      subtotal_fmt=formatar_min_total(subtotal_minutos),
  )


@app.route("/locais", methods=["GET", "POST"])
def gerenciar_locais():
  if request.method == "POST":
    nome_local = request.form["nome_local"].strip()
    if nome_local:
      existe = LocalAtendimento.query.filter_by(nome=nome_local).first()
      if not existe:
        db.session.add(LocalAtendimento(nome=nome_local))
        db.session.commit()
    return redirect(url_for("gerenciar_locais"))

  locais = LocalAtendimento.query.order_by(LocalAtendimento.nome).all()
  return render_template_string(
      TEMPLATE, locais=locais, page="locais", registros=[]
  )


@app.route("/local/excluir/<int:id>")
def excluir_local(id):
  l = LocalAtendimento.query.get_or_404(id)
  db.session.delete(l)
  db.session.commit()
  return redirect(url_for("gerenciar_locais"))


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
  reg = Registro.query.get_or_404(id)
  tecnicos = Tecnico.query.order_by(Tecnico.nome).all()
  locais = LocalAtendimento.query.order_by(LocalAtendimento.nome).all()

  if request.method == "POST":
    reg.tecnico = request.form["tecnico"]
    reg.data = request.form["data"]
    reg.entrada = request.form["entrada"]
    reg.saida = request.form["saida"]
    reg.almoço_inicio = request.form.get("almoco_inicio", "")
    reg.almoço_fim = request.form.get("almoco_fim", "")
    reg.banco_inicio = request.form.get("banco_inicio", "00:00")
    reg.banco_final = request.form.get("banco_final", "00:00")
    reg.tipo_credito = request.form["tipo_credito"]
    reg.percentual_extra = (
        int(request.form.get("percentual_extra") or 0)
        if reg.tipo_credito == "Hora Extra"
        else 0
    )
    reg.ferias_inicio = request.form.get("ferias_inicio", "")
    reg.ferias_fim = request.form.get("ferias_fim", "")
    reg.ferias_dias = int(request.form.get("ferias_dias") or 0)

    reg.chk_translado = True if request.form.get("chk_translado") else False
    reg.chk_dia = True if request.form.get("chk_dia") else False
    reg.chk_noite = True if request.form.get("chk_noite") else False

    tecnico_obj = Tecnico.query.filter_by(nome=reg.tecnico).first()
    translado_str = (
        tecnico_obj.translado_tempo if tecnico_obj and tecnico_obj.translado_tempo else "01:30"
    )
    translado_minutos = converter_tempo_minutos(translado_str)

    locais_selecionados = request.form.getlist("locais_atendimento")
    reg.local_atendimento = (
        ", ".join(locais_selecionados) if locais_selecionados else ""
    )

    fmt = "%H:%M"
    if reg.banco_inicio != "00:00" and reg.banco_final != "00:00":
      t_bini = datetime.strptime(reg.banco_inicio, fmt)
      t_bfim = datetime.strptime(reg.banco_final, fmt)
      if t_bfim >= t_bini:
        dif = t_bfim - t_bini
      else:
        dif = (
            (datetime.strptime("23:59", fmt) - t_bini)
            + (t_bfim - datetime.strptime("00:00", fmt))
            + timedelta(minutes=1)
        )
      reg.minutos_calculados = int(dif.total_seconds() // 60)
    else:
      t_ent = datetime.strptime(reg.entrada, fmt)
      t_sai = datetime.strptime(reg.saida, fmt)
      limite_comercial = datetime.strptime("17:45", fmt)

      if t_sai < t_ent:
        t_sai = t_sai + timedelta(days=1)

      if reg.chk_translado:
        t_sai_com_translado = t_sai + timedelta(minutes=translado_minutos)
        limite_dt = datetime.combine(t_sai.date(), limite_comercial.time())
        if t_sai_com_translado > limite_dt and t_sai >= limite_dt:
          reg.minutos_calculados = 0
          t_sai = t_ent
        else:
          t_sai = t_sai_com_translado

      if reg.chk_dia:
        t_ent = t_ent + timedelta(minutes=translado_minutos)
      if reg.chk_noite:
        t_sai = t_sai - timedelta(minutes=translado_minutos)

      if not (reg.chk_translado and reg.minutos_calculados == 0):
        if t_sai >= t_ent:
          dif = t_sai - t_ent
        else:
          dif = timedelta(0)

        if reg.almoço_inicio and reg.almoço_fim:
          t_aini = datetime.strptime(reg.almoço_inicio, fmt)
          t_afim = datetime.strptime(reg.almoço_fim, fmt)
          if t_afim < t_aini:
            t_afim = t_afim + timedelta(days=1)
          if t_afim > t_aini:
            dif_almoco = t_afim - t_aini
            if dif > dif_almoco:
              dif = dif - dif_almoco
        trabalhado_minutos = int(dif.total_seconds() // 60)
        reg.minutos_calculados = trabalhado_minutos - 525

    saldo_minutos = reg.minutos_calculados
    sinal = "+" if saldo_minutos > 0 else ("-" if saldo_minutos < 0 else "")
    m_abs = abs(saldo_minutos)
    reg.horas_formatadas = (
        f"{sinal}{m_abs // 60:02d}:{m_abs % 60:02d}"
        if saldo_minutos != 0
        else "00:00"
    )

    db.session.commit()
    return redirect(url_for("index"))

  return render_template_string(
      TEMPLATE,
      page="editar",
      registro_edit=reg,
      tecnicos=tecnicos,
      locais=locais,
      registros=[],
  )


@app.route("/excluir/<int:id>")
def excluir_registro(id):
  reg = Registro.query.get_or_404(id)
  db.session.delete(reg)
  db.session.commit()
  return redirect(url_for("index"))


@app.route("/tecnicos", methods=["GET", "POST"])
def gerenciar_tecnicos():
  if request.method == "POST":
    nome = request.form["nome"].strip()
    translado_tempo = request.form.get("translado_tempo", "01:30").strip()
    if nome:
      existe = Tecnico.query.filter_by(nome=nome).first()
      if not existe:
        db.session.add(
            Tecnico(nome=nome, translado_tempo=translado_tempo)
        )
        db.session.commit()
    return redirect(url_for("gerenciar_tecnicos"))

  tecnicos = Tecnico.query.order_by(Tecnico.nome).all()
  return render_template_string(
      TEMPLATE, tecnicos=tecnicos, page="tecnicos", registros=[]
  )


@app.route("/tecnico/excluir/<int:id>")
def excluir_tecnico(id):
  t = Tecnico.query.get_or_404(id)
  db.session.delete(t)
  db.session.commit()
  return redirect(url_for("gerenciar_tecnicos"))


if __name__ == "__main__":
  Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
  try:
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
  except KeyboardInterrupt:
    os._exit(0)