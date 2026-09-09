# AGENTS.md — Dash Captação de Leads · Núbia Oliveira (Família Aprovada MTR-SET26)

> Contexto completo em **`CLAUDE.md`** (mesma pasta) — leia-o antes de mexer no
> projeto. Este arquivo é um resumo para agentes/ferramentas que seguem a
> convenção `AGENTS.md`.
>
> Este repositório veio de um template genérico High Ticket, mas **já está
> configurado** — não há marcadores a preencher.

## O essencial em 6 linhas

- **Repo:** `scale-ag/dash-familia-aprovada-mtr-set26` · **Pages:** https://scale-ag.github.io/dash-familia-aprovada-mtr-set26/
- **Fontes:** duas planilhas Google (Leads da LP + Meta Ads), somente leitura. IDs/gids no topo de `build/build.py`.
- **Funil:** `Gasto → Impressões → Cliques → Visitas na LP → Leads`. Termina no lead.
- **Lead válido:** `utm_source=Meta-Ads` **e** campanha começando com `MTR-SET26` **e** nome/e-mail/telefone preenchidos (`is_valid_lead`).
- **Não existe nesta conta:** MQL, compradores, vendas, faturamento, receita, CAC, ROAS, Checkouts, link do criativo. Não tente reintroduzir sem fonte de dados.
- **Build:** `python build/build.py --leads-file leads.csv --meta-file meta.csv --out dist/index.html` (sem os flags, busca os CSVs públicos — precisa alcançar `docs.google.com`).

## Onde mexer

| Quero mudar… | Arquivo |
|---|---|
| IDs/gids das planilhas, regra de lead válido, imposto, limiares de amostra | `build/build.py` (constantes no topo + `is_valid_lead`) |
| Só as cores (tema claro/escuro) | `build/identidade-visual.css` |
| Layout/componentes | `build/estilos.css` |
| KPIs, funil, tabelas, gráficos, filtro cruzado | `build/app.js` |
| Título, logo, textos fixos da página | `build/template.html` |
| Publicação | `.github/workflows/deploy.yml` · `SETUP-CRON.md` |

`build/build.py` **não agrega**: exporta as linhas cruas (`leads[]`/`meta[]`) e
TODA a lógica (filtros de data, filtro cruzado, KPIs, tabelas, gráficos, heatmap,
imposto) roda no navegador, em `app.js`. `render()` costura
`template.html` + `identidade-visual.css` + `estilos.css` + `app.js` nos
placeholders `__STYLES__`/`__APP_JS__`/`__DATA_JSON__`.

## Insights de Tráfego (aba Relatório) — inativos

`build/relatorios.json` e `build/relatorios_dados.json` estão vazios (`{}`) e o
`schedule` do `.github/workflows/briefing.yml` está **comentado**: a Routine do
Claude que redige os Insights não foi criada para este cliente. Instruções para
ativar no topo do `briefing.yml`. O `gerar_relatorios.py` do template foi
removido (era todo baseado em MQL/CAC/ROAS).

## Antes de publicar

Testar local com CSVs de amostra: 3 páginas, tema claro/escuro, multi-seleção
(Ctrl) nas tabelas hierárquicas, filtro cruzado e seletor de período.
Ver `GUIA-REPLICACAO.md` para os detalhes de implementação (engine de tabela,
filtro cruzado, gráficos Chart.js).
