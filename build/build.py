#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera a dashboard estatica (index.html) do funil de Captacao de Leads da
Nubia Oliveira (Familia Aprovada · MTR-SET26) a partir de DUAS planilhas
publicas do Google Sheets (somente leitura):

  - "Meteorico MFA L1 - Leads" (aba "Leads", gid 0): fonte PRINCIPAL de leads —
    submissoes do formulario da LP (https://familiaprovada.com/mtr/), com as
    UTMs preservadas. Usada em TODOS os graficos/cards/tabelas/conversoes.
  - "Meta Ads" (gid 0): investimento/impressoes/cliques/visitas na LP do
    gerenciador de midia.

LEAD VALIDO (decisao do cliente): so entra na dashboard o lead que veio de
midia paga E esta completo. As tres condicoes sao obrigatorias — ver
is_valid_lead():
  1. utm_source == "Meta-Ads";
  2. utm_campaign comeca com MAIN_PRODUCT_PREFIX ("MTR-SET26");
  3. nome, email e telefone preenchidos.
Isso descarta os leads de teste (utm_source "test"/"teste") e os cadastros
diretos/organicos sem UTM. Consequencia: 100% dos leads da dash sao de midia
paga, entao a Visao Geral e a pagina de midia paga olham para o mesmo universo,
mudando so as quebras.

O casamento com o Meta Ads e EXATO, sem heuristica:
    utm_campaign == Campaign Name · utm_medium == Ad Set Name · utm_content == Ad Name

FORA DE ESCOPO NESTA CONTA (decisao do cliente — nao ha fonte de dados):
MQL/qualificacao, compradores, vendas, faturamento, receita, CAC e ROAS. Nada
disso e calculado aqui nem aparece na interface; o funil termina em Leads/CPL.
A conta tambem nao tem "Adds to Cart"/"Subscriptions" no Meta, entao nao ha
Checkouts nem link de criativo.

Este script apenas LE as planilhas (export CSV publico) e emite os REGISTROS
BRUTOS (leads[] e meta[]) dentro do HTML. Todos os filtros, agregacoes, KPIs,
tabelas e graficos sao calculados no navegador (client-side). Nunca escreve
nada de volta.

Teste local: --leads-file / --meta-file apontando para CSVs baixados.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

# Planilha de Leads ("Meteorico MFA L1 - Leads") — fonte principal.
SPREADSHEET_ID_LEADS = "11AzC3YayPbFx_jtKfHc566gwVAaR_2AtUnja_tdW4-s"
GID_LEADS = "0"
# Planilha de midia paga (Meta Ads) — planilha SEPARADA, id proprio.
SPREADSHEET_ID_META = "1op35YxXrib70If3Ywo3iRHIZxdbLOYGxMkk3za1hVC0"
GID_META = "0"
EXPORT_URL = "https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"

# Identificação do cliente/conta (usada só em textos/relatórios — não afeta o cruzamento de dados).
CLIENT_NAME = "Núbia Oliveira"
MAIN_PRODUCT = "Família Aprovada · MTR-SET26"
# Sigla do funil / prefixo comum a TODAS as campanhas da conta. Extraída do
# padrão de nomenclatura do gerenciador:
#   MTR-SET26 | E2-CAP | P1-QUENTE | LEAD | ABO | 2026-09-08 | Teste de criativos
#   ^^^^^^^^^   ^^^^^^   ^^^^^^^^^   ^^^^   ^^^
#   sigla       etapa    público     obj.   estrutura
# Só existe UMA sigla nesta conta (MTR-SET26); é ela que valida o lead como
# sendo desta operação (ver is_valid_lead).
MAIN_PRODUCT_PREFIX = "MTR-SET26"
# utm_source exigido para o lead contar como mídia paga.
LEAD_SOURCE_META = "meta-ads"

# --------------------------------------------------------------------------- #
# Fusos horarios — a planilha de Leads e a conta de anuncios NAO estao no mesmo
# fuso, e isso desloca o dia de parte dos leads:
#   - data_inscricao (planilha de Leads) e' gravada em America/Sao_Paulo (UTC-3);
#   - o campo "Day" do Meta Ads e' o dia fechado no fuso da CONTA DE ANUNCIOS,
#     que aqui e' America/Noronha (UTC-2).
# Como Noronha esta 1h A FRENTE, todo lead das 23:00-23:59 em Sao Paulo ja e' do
# DIA SEGUINTE para o Meta. Sem converter, esses leads caem num dia e o gasto que
# os gerou no outro, estragando CPL/ConvLP diarios. parse_lead_date() faz a
# conversao; o "Day" do Meta entra como esta (ja e' o fuso de referencia).
# O Brasil nao tem mais horario de verao (extinto em 2019), entao os dois fusos
# sao offsets fixos — o fallback abaixo e' exato, nao uma aproximacao.
LEADS_TZ_NAME = "America/Sao_Paulo"    # fuso em que a planilha de Leads grava a hora
ACCOUNT_TZ_NAME = "America/Noronha"    # fuso da conta de anuncios (dia de referencia da dash)
try:                                    # tzdata do sistema (runner do Actions tem)
    from zoneinfo import ZoneInfo
    LEADS_TZ = ZoneInfo(LEADS_TZ_NAME)
    ACCOUNT_TZ = ZoneInfo(ACCOUNT_TZ_NAME)
except Exception:                       # sem tz database: offsets fixos equivalentes
    LEADS_TZ = timezone(timedelta(hours=-3))
    ACCOUNT_TZ = timezone(timedelta(hours=-2))

BRT = timezone(timedelta(hours=-3))   # horario de Brasilia (so p/ o carimbo "ultima atualizacao")
TAX_FACTOR = 1.13806   # fator padrão de imposto/taxa sobre o gasto de mídia paga (Meta Ads) = 13,806%.
                       # Default do template para toda nova dash criada a partir dele; ajuste apenas
                       # se o cliente tiver um fator diferente, ou use 1.0 se não houver imposto.

# --------------------------------------------------------------------------- #
# Regras da aba Relatório (Top/Piores anúncios)
# --------------------------------------------------------------------------- #
# Amostra mínima para julgar um anúncio como "vencedor" ou "ruim". Abaixo disso
# ele entra como "Em observação" (dado insuficiente) — nunca é classificado só
# porque teve 1 resultado com pouco investimento.
SAMPLE_MIN_SPEND = 100.0   # gasto mínimo (R$) para amostra relevante
SAMPLE_MIN_LEADS = 3       # leads mínimos para julgar o anúncio
TOP_ADS_N = 10             # nº de linhas em Top / Piores anúncios

# Metas & parâmetros da conta (DEFAULTS do painel editável da aba Relatório).
# São só o valor inicial: o usuário edita no navegador (persistido em
# localStorage) e as tabelas de anúncios recolorem o CPL e reavaliam a amostra
# ao vivo. None = "meta não definida" (métrica aparece sem cor até o gestor
# preencher).
META_CPL = None            # meta de CPL (R$/lead); None = não definida
VOLUME_MIN_AMOSTRAL = SAMPLE_MIN_LEADS  # conversões (leads) mínimas p/ amostra confiável
N_DIAS_CORTE = 5           # dias consecutivos acima do teto p/ considerar corte


# --------------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------------- #
FETCH_RETRIES = 3       # tentativas totais em caso de timeout/erro de rede no export CSV
FETCH_RETRY_DELAY = 15  # segundos entre tentativas (o Google Sheets às vezes trava a resposta)


def fetch_csv(url: str) -> list[list[str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "dash-mtr-set26-bot/1.0"})
    last_err: Exception | None = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            return list(csv.reader(io.StringIO(raw)))
        except (TimeoutError, urllib.error.URLError) as exc:
            last_err = exc
            if attempt < FETCH_RETRIES:
                print(f"[fetch_csv] tentativa {attempt}/{FETCH_RETRIES} falhou ({exc!r}); "
                      f"tentando de novo em {FETCH_RETRY_DELAY}s...", file=sys.stderr)
                time.sleep(FETCH_RETRY_DELAY)
    raise last_err


def read_csv_file(path: str) -> list[list[str]]:
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.reader(f))


def load_rows(url: str, local: str | None) -> list[list[str]]:
    return read_csv_file(local) if local else fetch_csv(url)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str | None) -> str:
    return strip_accents((s or "").strip().lower())


def to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v).strip())
    if not s:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_date(v: str) -> str | None:
    """Dia SEM conversao de fuso — usado no "Day" do Meta Ads, que ja vem fechado
    no fuso da conta (o fuso de referencia da dash). Para os leads use
    parse_lead_date(), que converte de Sao Paulo para o fuso da conta."""
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    s = s.split()[0]          # "08/09/2026 15:15" -> "08/09/2026"
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%b %d, %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# Regra de LEAD VÁLIDO
# --------------------------------------------------------------------------- #
# Rede de segurança para o caso de um cadastro de teste chegar COM utm válida
# (alguém testando o formulário depois de clicar no anúncio). Bate só em
# nome/e-mail que são literalmente "teste"/"test" (opcionalmente numerados) ou
# em e-mail de domínio de teste — nunca em nome real que apenas contenha essas
# letras.
_TEST_NAME_RE = re.compile(r"^(teste?\d*)(\s+teste?\d*)*$")
_TEST_EMAIL_DOMAINS = ("teste.com", "test.com", "example.com")


# Formatos aceitos em data_inscricao, com e sem hora.
_LEAD_DT_FORMATS = (
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%d/%m/%y %H:%M:%S", "%d/%m/%y %H:%M", "%d/%m/%y",
)


def parse_lead_date(v: str) -> str | None:
    """Dia do lead JA CONVERTIDO para o fuso da conta de anuncios.

    data_inscricao vem em America/Sao_Paulo (UTC-3) e o dia do Meta Ads e' fechado
    em America/Noronha (UTC-2), 1h a frente: um lead de 08/09 23:30 em Sao Paulo e'
    09/09 00:30 para o Meta e precisa contar no dia 09. Sem hora na celula, assume
    00:00 (o dia nao muda). Devolve "YYYY-MM-DD" no fuso da conta."""
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = re.sub(r"\s+", " ", s)
    for fmt in _LEAD_DT_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
        except ValueError:
            continue
        return dt.replace(tzinfo=LEADS_TZ).astimezone(ACCOUNT_TZ).strftime("%Y-%m-%d")
    # formato desconhecido: cai no parser generico (sem conversao de fuso)
    return parse_date(s)


def is_test_lead(name: str, email: str) -> bool:
    if _TEST_NAME_RE.match(norm(name)):
        return True
    e = norm(email)
    if "@" in e:
        local, _, domain = e.partition("@")
        if domain in _TEST_EMAIL_DOMAINS or _TEST_NAME_RE.match(local):
            return True
    return False


def is_valid_lead(source: str, campaign: str, name: str, email: str, phone: str) -> bool:
    """Lead que entra na dashboard (decisao do cliente): veio da Meta Ads, e' da
    campanha desta operacao e esta com o cadastro completo. Qualquer uma das tres
    condicoes falhando descarta a linha — e' assim que os leads de teste e os
    cadastros diretos/organicos sem UTM ficam de fora da contagem."""
    if norm(source) != LEAD_SOURCE_META:
        return False
    if not norm(campaign).startswith(norm(MAIN_PRODUCT_PREFIX)):
        return False
    if not (name.strip() and email.strip() and phone.strip()):
        return False
    return not is_test_lead(name, email)


def first_last_initial(name: str) -> str:
    parts = (name or "").strip().split()
    if not parts:
        return "—"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][:1]}."


def mask_email(e: str) -> str:
    e = (e or "").strip()
    if "@" not in e:
        return "—"
    user, dom = e.split("@", 1)
    keep = user[:2] if len(user) > 2 else user[:1]
    return f"{keep}****@{dom}"


def mask_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p or "")
    return f"…{digits[-4:]}" if len(digits) >= 4 else "—"


# Posicionamento (utm_term) -> rótulo legível para o gráfico "Leads por
# posicionamento". O que não estiver no mapa é exibido como veio.
PLACEMENT_LABELS = {
    "instagram_reels": "Instagram Reels",
    "instagram_feed": "Instagram Feed",
    "instagram_stories": "Instagram Stories",
    "instagram_explore": "Instagram Explore",
    "facebook_mobile_feed": "Facebook Feed",
    "facebook_mobile_reels": "Facebook Reels",
    "facebook_stories": "Facebook Stories",
    "others": "Outros",
}


def pretty_placement(v: str) -> str:
    s = (v or "").strip()
    if not s:
        return "Não informado"
    return PLACEMENT_LABELS.get(norm(s), s)


# --------------------------------------------------------------------------- #
# Indexacao das colunas
# --------------------------------------------------------------------------- #
def header_index(header, wanted, fallback):
    idx = {}
    hn = [norm(h) for h in header]
    for key, aliases in wanted.items():
        found = None
        for a in aliases:
            a = norm(a)
            for i, h in enumerate(hn):
                if h == a or (a and a in h):
                    found = i
                    break
            if found is not None:
                break
        idx[key] = found if found is not None else fallback.get(key)
    return idx


def cell(row, i):
    if i is None or i < 0 or i >= len(row):
        return ""
    return (row[i] or "").strip()


# --------------------------------------------------------------------------- #
# Processamento -> registros brutos
# --------------------------------------------------------------------------- #
def process(leads_rows, meta_rows):
    lheader = leads_rows[0] if leads_rows else []
    lidx = header_index(
        lheader,
        {"created": ["data_inscricao", "data"], "name": ["nome"], "email": ["email"],
         "phone": ["telefone"], "source": ["utm_source"], "campaign": ["utm_campaign"],
         "adset": ["utm_medium"], "ad": ["utm_content"], "placement": ["utm_term"]},
        {"created": 0, "name": 1, "email": 2, "phone": 3, "source": 4, "campaign": 5,
         "adset": 6, "ad": 7, "placement": 8},
    )

    leads = []
    descartados = {"sem_meta": 0, "fora_da_campanha": 0, "incompleto": 0, "teste": 0}
    for row in leads_rows[1:]:
        if not any((c or "").strip() for c in row):
            continue
        source = cell(row, lidx["source"])
        campaign = cell(row, lidx["campaign"])
        name = cell(row, lidx["name"])
        email = cell(row, lidx["email"])
        phone = cell(row, lidx["phone"])
        if not is_valid_lead(source, campaign, name, email, phone):
            if norm(source) != LEAD_SOURCE_META:
                descartados["sem_meta"] += 1
            elif not norm(campaign).startswith(norm(MAIN_PRODUCT_PREFIX)):
                descartados["fora_da_campanha"] += 1
            elif not (name.strip() and email.strip() and phone.strip()):
                descartados["incompleto"] += 1
            else:
                descartados["teste"] += 1
            continue
        leads.append({
            "d": parse_lead_date(cell(row, lidx["created"])),
            # Todo lead que chega aqui é, por definição, de mídia paga.
            "src": "meta",
            "plat": pretty_placement(cell(row, lidx["placement"])),
            "camp": campaign,
            "adset": cell(row, lidx["adset"]) or "(sem conjunto)",
            "ad": cell(row, lidx["ad"]) or "(sem anúncio)",
            "nm": first_last_initial(name),
            "em": mask_email(email),
            "ph": mask_phone(phone),
        })

    mheader = meta_rows[0] if meta_rows else []
    midx = header_index(
        mheader,
        {"day": ["day", "data"], "campaign": ["campaign name", "campaign"],
         "adset": ["ad set name", "adset"], "ad": ["ad name"],
         "spent": ["amount spent", "valor gasto", "gasto"], "impr": ["impressions", "impress"],
         "clicks": ["link clicks", "clicks", "cliques"],
         "pv": ["landing page views", "page views", "pageviews"],
         # Colunas OPCIONAIS de veiculação ("Delivery" no Meta / "Veiculação" no
         # export em português). Hoje NENHUMA existe neste export — enquanto não
         # existirem, a dash cai na veiculação INFERIDA pelo gasto, que NÃO
         # enxerga um anúncio pausado HOJE (ele já gastou hoje antes de ser
         # pausado, e a planilha é diária, não horária). Basta adicionar a coluna
         # que o status real passa a valer, sem mexer no código.
         # Uma coluna por nível; a de anúncio é a mais importante, porque conjunto
         # e campanha são deduzidos dela quando não vierem explícitos.
         "status": ["ad delivery", "veiculacao do anuncio", "ad status",
                    "delivery", "veiculacao", "effective status", "status", "entrega"],
         "adset_status": ["ad set delivery", "adset delivery", "veiculacao do conjunto",
                          "ad set status", "adset status"],
         "camp_status": ["campaign delivery", "veiculacao da campanha", "campaign status"]},
        {"day": 0, "campaign": 1, "adset": 2, "ad": 3, "impr": 4, "clicks": 5, "pv": 6, "spent": 7},
    )

    meta = []
    # Anúncio -> status REAL de veiculação, quando a coluna existir. Guarda o
    # valor do dia MAIS RECENTE em que o anúncio aparece (o status de ontem não
    # deve sobrescrever o de hoje).
    # nível -> nome -> (dia, status). Guarda o valor do dia MAIS RECENTE em que o
    # membro aparece: o status de ontem não pode sobrescrever o de hoje.
    status_por_nivel: dict[str, dict[str, tuple[str, str]]] = {"ad": {}, "adset": {}, "camp": {}}
    for row in meta_rows[1:]:
        if not any((c or "").strip() for c in row):
            continue
        dia = parse_date(cell(row, midx["day"])) or ""
        for nivel, col_status, col_nome in (("ad", "status", "ad"),
                                            ("adset", "adset_status", "adset"),
                                            ("camp", "camp_status", "campaign")):
            st = cell(row, midx[col_status])
            nome = cell(row, midx[col_nome])
            if not st or not nome:
                continue
            atual = status_por_nivel[nivel].get(nome)
            if atual is None or dia >= atual[0]:
                status_por_nivel[nivel][nome] = (dia, st)
        meta.append({
            "d": parse_date(cell(row, midx["day"])),
            "camp": cell(row, midx["campaign"]) or "(sem campanha)",
            "adset": cell(row, midx["adset"]) or "(sem conjunto)",
            "ad": cell(row, midx["ad"]) or "(sem anúncio)",
            "sp": round(to_float(cell(row, midx["spent"])), 4),
            "im": to_float(cell(row, midx["impr"])),
            "cl": to_float(cell(row, midx["clicks"])),
            "pv": to_float(cell(row, midx["pv"])),
        })

    dates = sorted({d for d in ([l["d"] for l in leads if l["d"]] + [m["d"] for m in meta if m["d"]])})
    now_brt = datetime.now(BRT)              # carimbo "ultima atualizacao" (hora local do gestor)
    hoje_conta = datetime.now(ACCOUNT_TZ)    # "hoje" do funil = dia no fuso da conta de anuncios
    return {
        "build": {
            "generated_at_brt": now_brt.strftime("%d/%m/%Y %H:%M"),
            "build_id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            "today": hoje_conta.strftime("%Y-%m-%d"),
            "date_min": dates[0] if dates else None,
            "date_max": dates[-1] if dates else None,
            "tax_factor": TAX_FACTOR,
            "leads_tz": LEADS_TZ_NAME,
            "account_tz": ACCOUNT_TZ_NAME,
            "client_name": CLIENT_NAME,
            "main_product": MAIN_PRODUCT,
            # config da aba Relatório (lida pelo front)
            "sample_min_spend": SAMPLE_MIN_SPEND,
            "sample_min_leads": SAMPLE_MIN_LEADS,
            "top_ads_n": TOP_ADS_N,
            # metas & parâmetros (defaults do painel editável; None = não definida)
            "meta_cpl": META_CPL,
            "volume_min_amostral": VOLUME_MIN_AMOSTRAL,
            "n_dias_corte": N_DIAS_CORTE,
            # diagnóstico da regra de lead válido (exibido no rodapé da dash)
            "leads_descartados": descartados,
        },
        "leads": leads,
        "meta": meta,
        # Status real de veiculação vindo da planilha, por nível. Vazios enquanto
        # não houver coluna de Delivery/Veiculação no export do Meta. O front usa
        # o nível explícito quando existe e, para conjunto/campanha sem coluna
        # própria, deduz do status dos anúncios que estão dentro deles.
        "status": {nivel: {nome: st for nome, (_, st) in m.items()}
                   for nivel, m in status_por_nivel.items()},
        # Insights de Tráfego (texto pré-escrito, lido de relatorios.json). Preenchido
        # em main() via load_briefings(); fica {} se relatorios.json não existir.
        "briefings": {},
    }


# --------------------------------------------------------------------------- #
# Insights de Tráfego (aba Relatório)
# --------------------------------------------------------------------------- #
def load_briefings(path: str) -> dict:
    """Lê build/relatorios.json. Estrutura:
        {"generated_at": "...", "periodos": {"<preset>": {...}, ...}}
    Retorna o dict inteiro (ou {} se o arquivo não existir/for inválido).
    A geração NÃO acontece aqui — este build só lê o texto já pronto, sem
    chamar nenhuma API (custo zero no build/no navegador)."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, OSError):
        return {}


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def render(data, template_path):
    # A dashboard e montada a partir de arquivos separados (visual x logica):
    #   template.html          -> esqueleto HTML (placeholders __STYLES__/__APP_JS__)
    #   identidade-visual.css  -> TODAS as cores (edite aqui p/ mexer so em cor)
    #   estilos.css            -> layout/componentes
    #   app.js                 -> logica + renderizacao
    # Esta funcao so COSTURA os arquivos e injeta os dados; nao altera nada deles.
    base = os.path.dirname(os.path.abspath(template_path))

    def readf(name):
        with open(os.path.join(base, name), "r", encoding="utf-8") as f:
            return f.read()

    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    styles = readf("identidade-visual.css") + "\n" + readf("estilos.css")
    tpl = tpl.replace("__STYLES__", styles)
    tpl = tpl.replace("__APP_JS__", readf("app.js"))
    tpl = tpl.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    tpl = tpl.replace("__BUILD_ID__", data["build"]["build_id"])
    tpl = tpl.replace("__GENERATED_BRT__", data["build"]["generated_at_brt"])
    return tpl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leads-file", help="CSV local da aba Leads (fonte principal)")
    ap.add_argument("--meta-file", help="CSV local da planilha Meta Ads")
    ap.add_argument("--template", default="build/template.html")
    ap.add_argument("--out", default="dist/index.html")
    args = ap.parse_args()

    leads_rows = load_rows(EXPORT_URL.format(sid=SPREADSHEET_ID_LEADS, gid=GID_LEADS), args.leads_file)
    meta_rows = load_rows(EXPORT_URL.format(sid=SPREADSHEET_ID_META, gid=GID_META), args.meta_file)

    data = process(leads_rows, meta_rows)

    # Insights de Tráfego (texto pré-escrito) — lidos do arquivo versionado ao
    # lado do template. Sem chamada de API no build.
    briefings_path = os.path.join(os.path.dirname(os.path.abspath(args.template)), "relatorios.json")
    data["briefings"] = load_briefings(briefings_path)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render(data, args.template))

    b = data["build"]
    d = b["leads_descartados"]
    sp = sum(m["sp"] for m in data["meta"])
    print("== build ok ==", file=sys.stderr)
    print(f"  periodo   : {b['date_min']} -> {b['date_max']}", file=sys.stderr)
    print(f"  leads     : {len(data['leads'])} válidos "
          f"(Meta-Ads + campanha {MAIN_PRODUCT_PREFIX} + cadastro completo)", file=sys.stderr)
    print(f"  descartados: {d['sem_meta']} sem utm_source=Meta-Ads · "
          f"{d['fora_da_campanha']} fora da campanha · {d['incompleto']} incompletos · "
          f"{d['teste']} de teste", file=sys.stderr)
    print(f"  meta      : {len(data['meta'])} linhas · gasto R$ {sp:,.2f} "
          f"(sem imposto; fator {TAX_FACTOR})", file=sys.stderr)
    st = data["status"]
    achados = [f"{len(st[k])} {rot}" for k, rot in
               (("ad", "anúncio(s)"), ("adset", "conjunto(s)"), ("camp", "campanha(s)")) if st[k]]
    if achados:
        veic = "status real na planilha para " + " · ".join(achados)
    else:
        veic = ("SEM coluna de status no export; a dash infere pelo gasto do dia "
                "(NÃO detecta o que foi pausado hoje)")
    print(f"  veiculação: {veic}", file=sys.stderr)
    print(f"  out       : {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
