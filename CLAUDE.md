# CLAUDE.md — Contexto do projeto (Núbia Oliveira · Família Aprovada MTR-SET26)

> Este arquivo é lido automaticamente pelo Claude Code ao abrir o repositório.
> Ele carrega TODO o contexto necessário para continuar o trabalho sem depender
> de mensagens anteriores. Mantenha-o atualizado.
>
> Este repositório nasceu de um template genérico de dashboard High Ticket, mas
> **já está configurado para este cliente** — não há mais marcadores a preencher.
> O funil desta conta é mais curto que o do template: ver "O que NÃO existe".

---

## O que é

Dashboard de **Captação de Leads** — um app de BI estático (HTML/CSS/JS
puro + Chart.js via CDN) publicado no **GitHub Pages**, que cruza a lista de
**Leads** da landing page com o gerenciador de mídia paga (Meta Ads) e se
atualiza sozinho a cada ~30 min (build 100% na nuvem via GitHub Actions,
disparado externamente pelo cron-job.org).

- **Cliente:** Núbia Oliveira · **Oferta:** Família Aprovada (MTR-SET26)
- **Repo:** `scale-ag/dash-familia-aprovada-mtr-set26`
- **URL pública:** https://scale-ag.github.io/dash-familia-aprovada-mtr-set26/
- **Somente leitura** das planilhas. Nunca escrever de volta.

## O que NÃO existe nesta conta (importante)

Não há **MQL/qualificação, compradores, vendas, faturamento, receita, CAC nem
ROAS** — nenhuma fonte de dados alimenta isso, então nada disso é calculado nem
aparece na interface. O funil termina em **Leads/CPL**. O Meta Ads desta conta
também não expõe `Adds to Cart`/`Subscriptions` (sem Checkouts) nem permalink do
criativo (sem coluna "Link" nas tabelas de anúncio).

Se um dia chegarem compradores/vendas, isso é **desenvolvimento novo** — o
código foi enxugado, não apenas escondido atrás de um flag.

## Fontes de dados (Google Sheets)

São **duas planilhas separadas** (o template original usava uma só, com 4 abas):

| Planilha | ID | Aba (gid) | Colunas usadas |
|---|---|---|---|
| **Leads (LP)** — fonte principal | `11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s` | `0` | `data_inscricao` · `nome` · `email` · `telefone` · `utm_source` · `utm_campaign` · `utm_medium` · `utm_content` · `utm_term` · `url_pagina` |
| **Meta Ads** | `1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0` | `0` | `Day` · `Campaign Name` · `Ad Set Name` · `Ad Name` · `Impressions` · `Link Clicks` · `Landing Page Views` · `Amount Spent` |

Constantes em `build.py`: `SPREADSHEET_ID_LEADS`/`GID_LEADS` e
`SPREADSHEET_ID_META`/`GID_META`.
URL de export CSV: `https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=<GID>`

A planilha de Leads tem uma **segunda aba** (gid `1548896461`) com o questionário
de aplicação (`email` · `concursos_sonhos` · `momento_atual_estudos` ·
`situacao_hoje` · `horas_de_estudos` · `dificuldade_nos_estudos` ·
`espera_mentoria`). **Ela não é lida** — decisão do cliente: esta dash não marca
MQL.

### Casamento Leads × Meta Ads (exato, sem heurística)
```
utm_campaign == Campaign Name
utm_medium   == Ad Set Name
utm_content  == Ad Name
utm_term     -> posicionamento (Instagram_Feed/Stories/Reels, Facebook_*, Others)
```
Verificado com os dados reais: 1 campanha dos dois lados, e todo conjunto/anúncio
presente nos leads existe no Meta.

### Regra de LEAD VÁLIDO (`build.py` → `is_valid_lead`)
Só entra na dashboard o lead que satisfaz **as três** condições:
1. `utm_source` == `Meta-Ads`;
2. `utm_campaign` começa com `MAIN_PRODUCT_PREFIX` (`MTR-SET26`);
3. `nome`, `email` e `telefone` preenchidos.

Descarta os cadastros de teste e os leads diretos/orgânicos sem UTM.
**Consequência: 100% dos leads da dash são de mídia paga** — por isso não existe
gráfico "por origem" nem quebra orgânico vs. pago. `is_test_lead()` é uma rede de
segurança extra para um cadastro de teste que chegue com UTM válida (nome/e-mail
literalmente "teste"/"test", ou domínio de teste). O build imprime no log quantos
leads foram descartados e por qual das condições.

### Convenções de campanha
Nomenclatura do gerenciador:
```
MTR-SET26 | E2-CAP | P1-QUENTE | LEAD | ABO | 2026-09-08 | Teste de criativos
^^^^^^^^^   ^^^^^^   ^^^^^^^^^   ^^^^   ^^^
sigla       etapa    público     obj.   estrutura
```
- **Sigla do funil: `MTR-SET26`** (`MAIN_PRODUCT_PREFIX`) — só existe uma nesta conta.
- `E2-CAP` = etapa 2 / captação · `P1-QUENTE` = público quente · `LEAD` = objetivo · `ABO`.

### Veiculação do anúncio (Ativo/Pausado)
Coluna **Veiculação** nas 3 tabelas hierárquicas e na tabela de anúncios do
Relatório, mais o KPI "Anúncios veiculando" na Visão Geral. Funciona em dois modos:

1. **Status real** — se o export do Meta trouxer uma coluna de veiculação
   (`Ad Delivery`, `Delivery`, `Veiculação`, `Status`, `Effective Status`,
   `Entrega`), `build.py` a lê e emite `DATA.ad_status` (anúncio → status do dia
   mais recente). `app.js` → `statusRank()` normaliza PT/EN para
   **Ativo** (verde) · **Pausado** (vermelho) · qualquer outro estado do Meta
   exibido como veio, também em vermelho.
2. **Inferido pelo gasto** — enquanto a coluna não existir (**é o caso hoje**),
   `app.js` → `deliveryCell()` usa o último dia COM GASTO de cada anúncio:
   **Veiculando** = gastou no último dia do período · **Sem entrega** = já gastou
   antes, mas não no último dia · **Sem gasto** = nada no período.

A leitura da coluna é **binária por decisão do cliente**: só verde (entregando) e
vermelho (não entregando) — sem faixa amarela. O rank numérico (`_veic`) mantém
os 3 níveis para a ordenação continuar separando "Sem entrega" de "Sem gasto".
Isso vale só para a Veiculação; o amarelo continua nas outras escalas (CPL vs
meta e badge "Em observação"), que são de atenção, não de status.

Os rótulos são diferentes de propósito: "Veiculando/Sem entrega" deixa claro que
é entrega observada, não o botão do gerenciador. Campanha e conjunto sempre usam
o modo inferido (a coluna de status é por anúncio). Para ligar o modo real basta
adicionar a coluna no export — **nenhuma mudança de código**.

A coluna é `type:'html'` (chip colorido) com `sortKey:'_veic'`, um rank numérico
paralelo — sem isso o clique no cabeçalho não ordenaria. `sortKey` é uma extensão
da engine de tabela, disponível para qualquer coluna HTML futura.

### Fuso horário (crítico para o CPL diário)
A planilha de Leads grava `data_inscricao` em **America/Sao_Paulo** (UTC−3), mas o
campo `Day` do Meta Ads é o dia fechado no fuso da **conta de anúncios**, que é
**America/Noronha** (UTC−2) — 1h à frente. `build.py` → `parse_lead_date()`
converte a hora do lead de São Paulo para o fuso da conta antes de decidir o dia;
o `Day` do Meta entra sem conversão (já é o fuso de referência). Consequência
prática: **lead cadastrado a partir das 23h em São Paulo conta no dia seguinte**,
igual ao Meta. Sem isso, o lead caía num dia e o gasto que o gerou no outro,
distorcendo CPL e ConvLP diários (o total do período nunca mudava).

Constantes: `LEADS_TZ_NAME`/`ACCOUNT_TZ_NAME` em `build.py`. Usa `zoneinfo` e cai
para offsets fixos (−3/−2) se não houver tz database — exato, porque o Brasil não
tem mais horário de verão. O `today` do seletor de período e as janelas do
`coletar_dados_relatorio.py` também usam o fuso da conta; só o carimbo
"última atualização" fica na hora local do gestor (BRT).

### Imposto da mídia paga
`TAX_FACTOR = 1.13806` (13,806%) em `build.py`, aplicado **somente** ao gasto do
Meta Ads. O toggle "Imposto Meta" fica **ativo por padrão** (`STATE.tax=true` em
`app.js`) e aplica o fator no gasto e em todos os derivados (CPM, CPC, CPV, CPL)
via `taxf()`, que só multiplica `a.sp`. Desligar o toggle volta ao gasto sem imposto.

## Arquitetura / arquivos

```
build/build.py            # lê os 2 CSVs (read-only), aplica is_valid_lead(), emite REGISTROS BRUTOS (leads[]/meta[]); render() COSTURA os 4 arquivos abaixo
build/template.html       # esqueleto HTML. Placeholders __STYLES__, __APP_JS__, __DATA_JSON__, __BUILD_ID__, __GENERATED_BRT__
build/identidade-visual.css  # TODAS as cores (tema claro=padrão / escuro). Mexa AQUI p/ trocar só cor
build/estilos.css         # layout/componentes (sidebar, topbar, period-picker, funil, tabelas, gráficos, aba Relatório)
build/app.js              # lógica + renderização (KPIs, funil, tabelas, filtro cruzado, period-picker, heatmap, Relatório)
build/relatorios.json     # Insights de Tráfego por período (aba Relatório) — VERSIONADO; lido no build, sem API. Hoje {} (Routine não criada).
build/relatorios_dados.json      # números brutos por período (insumo p/ a Routine escrever relatorios.json) — não lido pelo site. Hoje {}.
build/relatorio_lib.py           # datas/agregação compartilhadas (usada por coletar_dados_relatorio.py)
build/coletar_dados_relatorio.py # gera relatorios_dados.json (só números, sem texto) — roda no briefing.yml (agendamento DESLIGADO)
build/GUIA-RELATORIOS.md            # formato/estrutura dos Insights da aba Relatório (os 7 blocos)
build/GUIA-INTERPRETACAO-METRICAS.md # regras de diagnóstico por métrica — leitura obrigatória p/ redigir
.github/workflows/deploy.yml    # roda build.py e publica no Pages (workflow_dispatch + schedule + push)
.github/workflows/briefing.yml  # roda coletar_dados_relatorio.py e commita relatorios_dados.json na main (cron DESLIGADO — ver topo do arquivo)
dist/index.html           # saída gerada (gitignored; o Actions reconstrói)
GUIA-REPLICACAO.md        # como replicar este modelo para outros relatórios/clientes
SETUP-CRON.md             # valores exatos do cron-job.org (só o token fica como TOKEN_AQUI)
```

### Aba Relatório
Terceira página (sidebar, entre a de mídia paga e o rodapé). **Espelha a Visão
Geral** (mesmo funil/KPIs/gráficos/tabela diária, via `renderGeralCore(REL_IDS)`)
e, abaixo, acrescenta 3 blocos novos + um painel de metas editável:
- **Metas & parâmetros (painel editável)** — no topo da aba: Meta CPL, Volume
  mínimo amostral (leads), N dias p/ corte. Persiste em `localStorage['dm_metas']`,
  default de `build.py` (`META_CPL`=None → "não definida"; `VOLUME_MIN_AMOSTRAL`/
  `N_DIAS_CORTE`). Editar recolore o **CPL** na tabela de anúncios (verde ≤ meta ·
  amarelo até +30% · vermelho acima) e ajusta o badge Em observação/Avaliável,
  **tudo ao vivo** (`METAS` + `renderRelAds()` em `app.js`).
- **Anúncios** — 13 colunas (Anúncio · **Status** · Campanha · Conjunto · Gasto ·
  Impr · CPM · CTR · CPC · Vis. LP · ConvLP · Leads · CPL). Anúncio e Status ficam
  **sticky** à esquerda. Ranking por **volume de leads** e, no empate, menor
  **CPL**; sem amostra relevante → badge **"Em observação"**. Limiares em
  `build.py`: `SAMPLE_MIN_SPEND`, `SAMPLE_MIN_LEADS`, `TOP_ADS_N`.
- **Insights de Tráfego** — texto por período redigido pelo **Claude** (linguagem de
  gestor de tráfego), lido de `build/relatorios.json` (sem API no build/navegador —
  o site só exibe o texto já pronto). Formato em **4 quadrantes** por período. Cada
  período compara com o período anterior **correto para aquela janela** (regra em
  `relatorio_lib.previous_period`). Chaves de período fixas
  (`hoje/ontem/3d/7d/14d/30d/mes/mespass/todo`), tags `Escalar/Otimizar/Cortar/Observar`.
  Toda a aritmética é pré-calculada em `build/relatorios_dados.json` — a Routine só
  interpreta, nunca recalcula. Regras completas em `build/GUIA-RELATORIOS.md` +
  `build/GUIA-INTERPRETACAO-METRICAS.md`. `app.js` ainda reconhece o formato antigo
  (`{"html": "…"}`) como fallback.

### Briefing automático do gestor (Routine do Claude, sem chamada à API Anthropic)
`build/relatorios.json` pode ser escrito 1×/dia por uma **Routine do Claude**
(Claude Code Remote — mesma infraestrutura de sessão/agente deste repo, agendada;
não é chamada paga à API). Fluxo em 2 etapas, porque o ambiente da Routine não
alcança `docs.google.com` (só o runner do GitHub Actions alcança):
1. `build/coletar_dados_relatorio.py` (GitHub Actions, `.github/workflows/briefing.yml`,
   1×/dia) agrega **só números** em `build/relatorios_dados.json` e commita na `main`.
2. A Routine do Claude lê esse JSON + `build/GUIA-RELATORIOS.md` +
   `build/GUIA-INTERPRETACAO-METRICAS.md`, redige `build/relatorios.json` e faz
   commit/push direto na `main`, disparando o `deploy.yml`. **Precisa ser criada
   por cliente** (`create_trigger` apontando para o repo novo) — não vem pronta.

**Estado atual: a Routine NÃO existe para este cliente.** Por isso o `schedule`
do `briefing.yml` está comentado e `relatorios.json`/`relatorios_dados.json`
estão vazios (`{}`) — a aba Relatório mostra "Os insights por IA ainda não foram
gerados". Para ativar, siga as instruções no topo de `.github/workflows/briefing.yml`
(inclui pôr Workflow permissions em "Read and write", que o job precisa p/ commitar).
O `gerar_relatorios.py` do template (fallback determinístico) foi **removido**:
ele era inteiramente baseado em MQL/CAC/ROAS, que não existem nesta conta.

Funil desta conta: `Gasto → Impressões → Cliques → Visitas na LP → Leads`, com
CPM · CTR · CPC · CR · CPV · ConvLP · CPL. Não há etapas depois do lead (ver
"O que NÃO existe nesta conta").

> **Layout modular:** o front-end é separado em `identidade-visual.css` + `estilos.css`
> + `app.js`, costurados por `render()` nos placeholders `__STYLES__`/`__APP_JS__`.
> Página 1 usa **funil vertical de leads** + KPIs secundários. Topbar tem
> **seletor de período em calendário** (default "Este mês"). **Heatmap** = cor FIXA
> por métrica (só opacidade varia): **Gasto=vermelho · Leads=azul**
> (`--heat-gasto`/`--heat-leads`).

O `build.py` **não agrega**: exporta as linhas cruas e TODA a lógica (filtros de
data, filtro cruzado, KPIs, tabelas, gráficos, heatmap, imposto) roda no navegador.

## Rodar/testar local

```bash
python build/build.py --leads-file leads.csv --meta-file meta.csv --out dist/index.html
# (o sandbox do agente NÃO alcança docs.google.com; use CSVs locais para testar.
#  O runner do GitHub Actions tem internet e busca os CSVs ao vivo.)
```

## Especificação funcional (resumo)

Três **páginas separadas** (sidebar):
1. **Visão Geral de Leads** — funil vertical (Gasto → Impressões → Cliques →
   Visitas na LP → Leads) + KPIs secundários; gráfico combinado diário + tabela
   diária com heatmap; 4 quebras em barras: por anúncio, por posicionamento
   (`utm_term`), por conjunto e CPL por anúncio.
2. **Captura Meta Ads** — mesmo funil; combinado diário; leads por anúncio; donut
   de ConvLP; compilado de anúncios por CPL; tabela diária com heatmap; 3 tabelas
   hierárquicas Campanha → Conjunto → Anúncio, cada uma com gráfico de CPL/dia
   embaixo; lista de leads do período.
3. **Relatório** — espelha a Visão Geral + painel de Metas editável + tabela de
   Anúncios (13 colunas, com Status) + Insights de Tráfego (hoje vazio).
   Ver `build/GUIA-RELATORIOS.md`.

**Ordem das colunas nas tabelas diárias:** `Data · Dia · Gasto · Impr. · CPM ·
Cliques · CTR · CPC · Vis. LP · CR · CPV · Leads · ConvLP · CPL` (`DAILY_COLS` em
`app.js`). As tabelas hierárquicas usam as mesmas métricas, trocando Data/Dia pela
dimensão.

**Regras obrigatórias das tabelas** (ver `GUIA-REPLICACAO.md`): cabeçalho sticky;
ordenação tri‑state; colunas redimensionáveis (persist localStorage); linha
"Total Geral" fixa; dimensão nunca truncada; seleção com toggle + Ctrl multi;
filtro cruzado bidirecional; tabela diária com último dia no topo; heatmap de cor
fixa por métrica.

## Lacunas de dados
- **Checkouts / VisCHK** → dependeriam de `Adds to Cart` no export do Meta; não existem.
- **Link do criativo** → dependeria de uma coluna de permalink no export do Meta; não existe.
- **Status real do anúncio (Ativo/Pausado)** → dependeria de uma coluna de
  `Delivery`/`Veiculação` no export do Meta; não existe. A dash mostra a
  veiculação inferida pelo gasto até a coluna aparecer (ver acima).
- Etapas pós-lead (MQL, vendas, faturamento) → ver "O que NÃO existe nesta conta".

## Publicação — problemas conhecidos
1. **Push:** se a integração GitHub da sessão for somente‑leitura (403), o caminho
   é `git push` direto para `github.com` com o **PAT do usuário**. Nunca gravar o
   token no `.git/config` (usar URL efêmera `https://x-access-token:<TOKEN>@github.com/...`).
2. **cron-job.org só funciona na `main`:** `workflow_dispatch` só existe na branch
   padrão. Levar `build/` + `.github/workflows/deploy.yml` para a `main`.
2b. **API de Settings do Actions/Pages é bloqueada pelo proxy do agente:**
   `/actions/permissions`, `/actions/permissions/workflow` e `/pages` devolvem
   403 "not permitted through this proxy" — não é escopo de token. Dá para
   listar/disparar workflows e ler logs normalmente. `default_workflow_permissions`
   precisa ser ajustado à mão em Settings (só importa se o `briefing.yml` for ligado).
3. **Pages liga sozinho:** `actions/configure-pages@v5` com `enablement: true`
   (precisa `permissions: pages: write, id-token: write`).
4. **Proxy do sandbox:** o ambiente do agente costuma NÃO alcançar `docs.google.com`,
   `*.github.io` nem a API REST de Actions/Pages — mas o runner do Actions alcança tudo.
5. **Token exposto:** se um token foi colado no chat, **revogar e gerar um novo**.

## Branch / git
- Desenvolvimento na branch designada da sessão; manter sincronizada com `main`.
