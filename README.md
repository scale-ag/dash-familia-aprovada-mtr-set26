# Dashboard de Captação de Leads · Núbia Oliveira

Dashboard **100% na nuvem** do funil **Família Aprovada · MTR-SET26**, cruzando a
mídia paga (Meta Ads) com os leads capturados na landing page. Build estático
(HTML/CSS/JS puro + Chart.js via CDN) publicado no **GitHub Pages** e reconstruído
a cada ~30 min pelo GitHub Actions (disparado externamente pelo cron-job.org).

**URL pública:** https://scale-ag.github.io/dash-familia-aprovada-mtr-set26/

Somente leitura das planilhas. O build **nunca** escreve de volta.

---

## O que a dash mostra

Funil: **Gasto → Impressões → Cliques → Visitas na LP → Leads**, com CPM, CTR,
CPC, CR, CPV, ConvLP e CPL. Três páginas:

1. **Visão Geral de Leads** — funil + KPIs secundários, evolução diária,
   tabela diária com heatmap e 4 quebras (por anúncio, por posicionamento,
   por conjunto e CPL por anúncio).
2. **Captura Meta Ads** — mesmo funil + donut de conversão da LP, compilado de
   anúncios por CPL, tabela diária e as 3 tabelas hierárquicas
   (Campanha → Conjunto → Anúncio) com filtro cruzado bidirecional.
3. **Relatório** — espelha a Visão Geral, mais o painel editável de metas e a
   tabela de anúncios com status de amostra. O bloco "Insights de Tráfego"
   aparece vazio até a Routine do Claude ser criada (ver abaixo).

### Regra de LEAD VÁLIDO
Só entra na dashboard o lead que satisfaz **as três** condições
(`build/build.py` → `is_valid_lead`):

1. `utm_source` == `Meta-Ads`;
2. `utm_campaign` começa com `MTR-SET26`;
3. `nome`, `email` e `telefone` preenchidos.

Isso descarta os cadastros de teste e os leads diretos/orgânicos sem UTM.
**Consequência:** 100% dos leads da dash são de mídia paga. O build imprime no
log quantos leads foram descartados e por quê.

### O que NÃO existe nesta conta
Não há MQL/qualificação, compradores, vendas, faturamento, receita, CAC nem
ROAS — não existe fonte de dados para nada disso, então nenhuma dessas métricas
é calculada ou exibida. O Meta Ads desta conta também não expõe
`Adds to Cart`/`Subscriptions` (sem Checkouts) nem permalink do criativo.

### Fuso horário
`data_inscricao` vem em **America/Sao_Paulo** (UTC−3) e o `Day` do Meta Ads é
fechado em **America/Noronha** (UTC−2), fuso da conta de anúncios. O build
converte a hora do lead antes de decidir o dia (`build.py` → `parse_lead_date`),
então **lead a partir das 23h em São Paulo conta no dia seguinte** — alinhado com
o Meta. O `Day` do Meta entra sem conversão.

### Imposto da mídia paga
`TAX_FACTOR = 1.13806` (13,806%) em `build/build.py`, aplicado **somente** ao
gasto do Meta Ads. O toggle "Imposto Meta" já vem ligado; desligá-lo mostra o
gasto sem imposto.

## Fontes de dados (Google Sheets, somente leitura)

São **duas planilhas separadas**:

| Planilha | ID | Aba (gid) | Colunas usadas |
|---|---|---|---|
| Leads (LP) | `11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s` | `0` | `data_inscricao` · `nome` · `email` · `telefone` · `utm_source` · `utm_campaign` · `utm_medium` · `utm_content` · `utm_term` |
| Meta Ads | `1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0` | `0` | `Day` · `Campaign Name` · `Ad Set Name` · `Ad Name` · `Impressions` · `Link Clicks` · `Landing Page Views` · `Amount Spent` |

O casamento entre as duas é **exato**, sem heurística:
`utm_campaign` = `Campaign Name` · `utm_medium` = `Ad Set Name` · `utm_content` = `Ad Name`.

A mesma planilha de Leads tem uma segunda aba (gid `1548896461`) com o
questionário de aplicação. **Ela não é usada** — não há critério de MQL nesta
dash.

URL de export CSV: `https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=<GID>`

## Rodar/testar local

```bash
python build/build.py --leads-file leads.csv --meta-file meta.csv --out dist/index.html
```

Sem `--leads-file`/`--meta-file` o script busca os CSVs públicos direto do
Google Sheets — o runner do GitHub Actions alcança `docs.google.com`, a maioria
dos sandboxes de agente não.

## Automação

- `.github/workflows/deploy.yml` — roda `build/build.py` e publica no Pages.
  Dispara por `workflow_dispatch` (usado pelo cron-job.org a cada 30 min),
  `schedule` de backup e `push` na `main`.
- `.github/workflows/briefing.yml` — coleta os números do Relatório. **Com o
  agendamento desligado**, porque a Routine do Claude que consome esse JSON
  ainda não existe. Ver o comentário no topo do arquivo para ativar.

Valores exatos para o cron-job.org: **`SETUP-CRON.md`**.
