# Spec: Guldbevakare – kraschdetektering för guldgruveaktier

## 0. Status – redan klart, gör inte om detta

- [x] GitHub-repo skapat och satt till **publikt**: [github.com/Janne-sz/golden_slumbers](https://github.com/Janne-sz/golden_slumbers)
- [x] `docs/index.html` skapad med platshållarinnehåll, committad till `main`.
- [x] GitHub Pages aktiverad: Settings → Pages → Source = "Deploy from a branch", branch `main`, mapp `/docs`. Sajten är **live** på `https://janne-sz.github.io/golden_slumbers/` (visar just nu bara platshållartext).
- [x] ntfy.sh-topic valt: `Guldet-48gk62bx` (ännu **inte** lagd som GitHub Actions secret – se steg 1 i "Kvar att göra").
- [ ] Workflow-permissions ("Read and write") under Settings → Actions → General – **oklart om detta är satt**, kontrollera som första steg.

## Kvar att göra (i rekommenderad ordning)

1. Lägg `Guldet-48gk62bx` som repository secret `NTFY_TOPIC` (Settings → Secrets and variables → Actions).
2. Sätt workflow-permissions till "Read and write" (Settings → Actions → General → Workflow permissions).
3. Bygg mappstruktur och filer enligt avsnitt 4.
4. Implementera `scripts/fetch.py` – återanvänd YF-hämtningsmodulen från beställarens tidigare projekt, men lägg till inkrementell-hämtning-logiken (avsnitt 5, steg 2).
5. Implementera `scripts/indicators.py`, `scripts/severity.py`, `scripts/notify.py` enligt avsnitt 6–8.
6. Bygg `docs/app.js` + `docs/manifest.json` (ersätter platshållar-`index.html`) enligt avsnitt 9.
7. Skriv `.github/workflows/poll.yml` (cron `0 * * * *`) enligt avsnitt 5 och 10.
8. Testa en full körning manuellt (`workflow_dispatch`-trigger) innan cron aktiveras skarpt.



## 1. Bakgrund och syfte

Beställaren äger andelar i två aktivt förvaltade guldgruvefonder (BGF World Gold, CPR Invest Global Gold Mines). Dessa fonder handlas bara till en NAV-kurs en gång per dag, vilket gör dem olämpliga för snabb bevakning. Syftet med detta system är att bevaka de underliggande innehavens **börsnoterade aktier** (som handlas kontinuerligt under dagen) som en proxy för fondernas rörelse, och larma i god tid om något som liknar en sektorkrasch är på väg – i stil med guldkraschen våren 2026 (guld föll ~26% från topp 28 jan till slutet av juni 2026, med tydliga tekniska varningssignaler redan i februari–mars).

Systemet ska **inte** lägga några ordrar automatiskt. Det är ett bevaknings- och larmsystem. Användaren fattar alla köp/sälj-beslut manuellt efter att ha fått en notis.

## 2. Definition of done (MVP)

- [ ] En PWA (installerbar på hemskärmen, fullskärmsläge) visar aktuell status för alla bevakade instrument, färgkodad efter allvarlighetsgrad.
- [ ] Ett schemalagt jobb hämtar kursdata en gång i timmen under (amerikansk/relevanta) börsers öppettider.
- [ ] Endast ny data sedan senaste hämtningen hämtas (inkrementell hämtning), inte hela historiken varje gång.
- [ ] Systemet beräknar per instrument: trailing drawdown från peak, dagsförändring, glidande medelvärden (50/100/200 dagar), rullande lägsta-nivå, antal dagar i följd nedåt.
- [ ] Systemet beräknar en **breadth-signal**: hur många av de bevakade aktierna som är ner mer än X% samma dag.
- [ ] Ett larm med 5 allvarlighetsnivåer (se avsnitt 7) skickas via ntfy.sh när villkor uppfylls, med olika prioritet per nivå.
- [ ] Att lägga till/ta bort ett bevakat instrument kräver bara en ändring i en konfigurationsfil – ingen kodändring.
- [ ] Att ändra ett tröskelvärde (t.ex. trailing-%, breadth-antal, MA-perioder) kräver bara en ändring i en konfigurationsfil – ingen kodändring.

## 3. Arkitektur – översikt

```
┌─────────────────────┐     schemalagd, 1 ggr/tim     ┌──────────────────────┐
│   GitHub Actions     │ ──────────────────────────▶  │  Python-jobb          │
│   (cron trigger)     │                               │  1. Hämta ny kursdata │
└─────────────────────┘                               │  2. Beräkna indikatorer│
                                                         │  3. Beräkna severity  │
                                                         │  4. Skicka ev. notis  │
                                                         │     till ntfy.sh      │
                                                         └──────────┬───────────┘
                                                                    │ committar
                                                                    ▼
                                                         ┌──────────────────────┐
                                                         │  data/*.json i repot  │
                                                         │  (fungerar som DB)    │
                                                         └──────────┬───────────┘
                                                                    │ GitHub Pages
                                                                    │ deployar om
                                                                    ▼
┌─────────────────────┐        laddar data.json         ┌──────────────────────┐
│  Telefon (PWA,       │ ◀──────────────────────────────│  Statisk PWA          │
│  hemskärms-ikon)     │                                 │  (GitHub Pages)       │
└─────────────────────┘                                 └──────────────────────┘
        ▲
        │ push (nivå 3–5 endast)
┌─────────────────────┐
│      ntfy.sh          │
└─────────────────────┘
```

Ingen traditionell server eller databas. GitHub Actions är "backend", en JSON-fil i repot är "databasen", GitHub Pages är hosting, ntfy.sh är push-leverantör.

## 4. Repo-struktur (förslag)

```
/
├── .github/workflows/
│   └── poll.yml                # schemalagt jobb, körs 1 ggr/tim
├── config/
│   ├── tickers.json             # lista på bevakade instrument – redigeras för att lägga till/ta bort aktier
│   └── thresholds.json          # alla tröskelvärden/villkor – redigeras för att justera larmkänslighet
├── data/
│   ├── prices/                  # historisk OHLC per ticker, en fil per ticker
│   │   └── <TICKER>.json
│   ├── state.json               # senaste hämtningstidpunkt per ticker + löpande peak-värden
│   └── latest_status.json       # aggregerat resultat PWA:n läser (severity per ticker, breadth-status)
├── scripts/
│   ├── fetch.py                 # hämtar ny data (inkrementellt), återanvänd YF-modul från tidigare projekt
│   ├── indicators.py            # beräknar MA, trailing drawdown, rullande lägsta, streaks
│   ├── severity.py              # slår ihop indikatorer → severity-nivå per ticker + breadth-koll
│   ├── notify.py                # POST till ntfy.sh med rätt priority
│   └── main.py                  # orkestrerar ovanstående, körs av workflow
├── docs/
│   ├── index.html
│   ├── manifest.json
│   ├── service-worker.js
│   └── app.js                   # läser data/latest_status.json, ritar UI, sätter app-badge
└── README.md
```

## 5. Dataflöde, steg för steg

1. **Trigger**: `.github/workflows/poll.yml` körs på cron `0 * * * *` (varje timme, dygnet runt). Beslut: eftersom GitHub Pages kräver publikt repo (se avsnitt 13) är Actions-minuter obegränsade, så det finns ingen anledning att begränsa till en enskild börs öppettider. Enklare och mer robust än att försöka synka USA/London/Australien-scheman med olika sommartidsövergångar. Körningar utanför öppettider ger bara "ingen ny data" för de tickers vars börs är stängd, vilket den inkrementella hämtningen hanterar utan problem.
2. **Inkrementell hämtning** (`fetch.py`): för varje ticker i `config/tickers.json`, läs `data/state.json` för att se `last_fetched_timestamp`. Hämta bara data nyare än detta (via redan existerande YF-hämtningsmodul från tidigare projekt – återanvänd den, men lägg till incremental-logik: skicka `start=last_fetched_timestamp` till biblioteket istället för att hämta hela historiken). Skriv ny data till `data/prices/<TICKER>.json` (append), uppdatera `last_fetched_timestamp` i `state.json`.
3. **Indikatorer** (`indicators.py`): för varje ticker, räkna ut (se avsnitt 6) utifrån den lagrade historiken (inte bara senaste punkten – MA och rullande lägsta kräver historik).
4. **Severity per ticker** (`severity.py`): mappa indikatorer → nivå 1–5 enligt konfigurerbara regler i `thresholds.json` (se avsnitt 7).
5. **Breadth-koll** (`severity.py`): räkna hur många tickers som har dagsförändring ≤ breadth-tröskeln. Om antalet ≥ konfigurerat minimum → höj golvet för samtliga bevakade tickers severity (se avsnitt 7.2).
6. **Skriv resultat**: `data/latest_status.json` skrivs om helt varje körning (litet, PWA:n läser bara denna filen).
7. **Notis** (`notify.py`): om någon tickers severity ≥ nivå 3, eller breadth-villkoret precis triggades (gick från icke-uppfyllt till uppfyllt), POST:a till ntfy.sh med rätt `Priority`-header (se avsnitt 8). Undvik spam: skicka bara notis när severity *höjs* till en ny nivå för ett instrument, inte varje timme instrumentet redan ligger kvar på samma nivå (kräver att skriptet jämför mot föregående körnings severity, sparad i `state.json`).
8. **Commit & push**: workflow committar `data/` (inklusive `latest_status.json`, uppdaterade `prices/*.json` och `state.json`) tillbaka till repot med default `GITHUB_TOKEN`.
9. **Deploy**: GitHub Pages triggas automatiskt av pushen, ny data blir tillgänglig på den statiska sajten inom någon minut.
10. **PWA**: nästa gång användaren öppnar appen (eller om service worker cachar/pollar i bakgrunden) hämtas `latest_status.json` och UI uppdateras. `navigator.setAppBadge()` sätts till antal instrument på nivå 3+.

## 6. Instrument att bevaka

### 6.1 Bekräftad lista (från BGF World Gold, senaste fondfaktablad maj 2026)

| Bolag | Ticker (yfinance) | Vikt i BGF World Gold |
|---|---|---|
| Barrick Mining Corp | `GOLD` | 8.20% |
| Newmont Corporation | `NEM` | 6.73% |
| AngloGold Ashanti PLC | `AU` | 6.61% |
| Wheaton Precious Metals Corp | `WPM` | 5.89% |
| Endeavour Mining PLC | `EDV.L` (London) alt. `EDV.TO` (Toronto) | 4.95% |
| Franco-Nevada Corp | `FNV` | 4.73% |
| Kinross Gold Corp | `KGC` | 4.70% |
| Northern Star Resources Ltd | `NST.AX` (Australien) | 4.51% |
| Agnico Eagle Mines Ltd | `AEM` | 4.05% |
| Alamos Gold Inc | `AGI` | 4.05% |

### 6.1b Bekräftad lista (CPR Invest Global Gold Mines, aktuellt innehav från Avanza)

| Bolag | Ticker (yfinance) | Vikt i CPR |
|---|---|---|
| Agnico Eagle | `AEM` | 7.99% |
| Newmont | `NEM` | 5.93% |
| Franco-Nevada | `FNV` | 5.45% |
| Wheaton Precious Metals | `WPM` | 4.78% |
| AngloGold Ashanti | `AU` | 4.70% |
| Barrick Mining | `GOLD` | 4.27% |
| Kinross Gold | `KGC` | 3.91% |
| Gold Fields ADR | `GFI` | 3.34% |
| Pan American Silver | `PAAS` | 3.06% |
| Alamos Gold | `AGI` | 2.59% |

### 6.1c Slutgiltig, sammanslagen och deduplicerad startlista (MVP)

Stort överlapp mellan fonderna som väntat. 12 unika bolag totalt:

| Bolag | Ticker | I BGF | I CPR |
|---|---|---|---|
| Barrick Mining Corp | `GOLD` | ✓ | ✓ |
| Newmont Corporation | `NEM` | ✓ | ✓ |
| AngloGold Ashanti PLC | `AU` | ✓ | ✓ |
| Wheaton Precious Metals Corp | `WPM` | ✓ | ✓ |
| Franco-Nevada Corp | `FNV` | ✓ | ✓ |
| Kinross Gold Corp | `KGC` | ✓ | ✓ |
| Agnico Eagle Mines Ltd | `AEM` | ✓ | ✓ |
| Alamos Gold Inc | `AGI` | ✓ | ✓ |
| Endeavour Mining PLC | `EDV.L` alt. `EDV.TO` | ✓ | – |
| Northern Star Resources Ltd | `NST.AX` | ✓ | – |
| Gold Fields ADR | `GFI` | – | ✓ |
| Pan American Silver | `PAAS` | – | ✓ |

Detta är den lista som ska ligga i `config/tickers.json` från start. Öppen fråga #1 (se avsnitt 12) är därmed löst.

### 6.2 Referens-instrument (för cross-check, ej del av breadth-räkningen)

| Syfte | Ticker |
|---|---|
| Guldpris (spot-proxy) | `GC=F` (COMEX-terminer) eller `GLD` (ETF, mer likvid/lättillgänglig historik) |
| BGF World Gold NAV (kontext, uppdateras 1 ggr/dag, ej realtid) | `0P00000B0I` |
| CPR Global Gold Mines NAV (kontext, uppdateras 1 ggr/dag) | `0P0001KRE8` |

### 6.3 `config/tickers.json` – schema

```json
{
  "watchlist": [
    { "ticker": "GOLD", "name": "Barrick Mining Corp", "include_in_breadth": true },
    { "ticker": "NEM", "name": "Newmont Corporation", "include_in_breadth": true }
  ],
  "reference": [
    { "ticker": "GC=F", "name": "Gold spot (futures)", "include_in_breadth": false },
    { "ticker": "0P00000B0I", "name": "BGF World Gold NAV", "include_in_breadth": false }
  ]
}
```
Att lägga till en ny bevakad aktie = lägga till en rad i `watchlist`. Inget annat behöver ändras.

## 7. Indikatorer och severity-modell

### 7.1 Indikatorer per ticker (beräknas varje körning)

| Indikator | Beskrivning |
|---|---|
| `trailing_drawdown_pct` | (peak sedan bevakning startade − nuvarande pris) / peak |
| `daily_change_pct` | förändring sedan föregående stängning |
| `below_ma50` | boolean, pris under 50-dagars glidande medelvärde |
| `below_ma100` | boolean, pris under 100-dagars glidande medelvärde. **Används inte som egen konfluenspunkt** (för korrelerad med `below_ma50`) – fungerar istället som en eskalator, se 7.2. |
| `new_swing_low` | boolean, dagens lägsta är lägre än lägsta de senaste N (konfigurerbart, standard 60) handelsdagarna |
| `down_streak_days` | antal sammanhängande dagar med negativ stängning |

### 7.2 Severity-nivåer (standardvärden – allt konfigurerbart i `thresholds.json`)

| Nivå | Färg | Villkor (per ticker) | Notis |
|---|---|---|---|
| 1 | Ljusgul | trailing_drawdown ≥ 2% | Ingen – bara UI-färg |
| 2 | Gul | trailing_drawdown ≥ 4% | Ingen – bara UI-färg |
| 3 | Orange | trailing_drawdown ≥ 6% **eller** (≥ 2 av: below_ma50, new_swing_low, down_streak_days ≥ 3) | ntfy `priority: low` |
| 4 | Mörkorange | trailing_drawdown ≥ 6% **och** ≥ 2 av villkoren ovan samtidigt, **eller** breadth-larm aktivt utan guldbekräftelse (se nedan) | ntfy `priority: default` |
| 5 | Röd | trailing_drawdown ≥ 8% **och** ≥ 3 av villkoren, **eller** breadth-larm aktivt **med** guldbekräftelse (se nedan) | ntfy `priority: urgent` |

**MA100-eskalator**: `below_ma100` räknas inte som en egen konfluenspunkt (för korrelerad med `below_ma50` – ger falsk känsla av oberoende bevis). Istället: om en ticker redan kvalificerar för nivå 3 **och** samtidigt har `below_ma100 = true`, höj den tickerns nivå med ett steg (3→4, eller 4→5 om den redan nått 4 av andra skäl). Appliceras efter att grundnivån räknats ut, innan notis skickas.

**Breadth-villkor (sektorbekräftelse)**: räkna antal tickers i `watchlist` med `daily_change_pct ≤ -4%` (tröskel konfigurerbar) samma dag.
- Om antalet ≥ `breadth_min_count` (standard 3 av totalt antal bevakade) → **golv på nivå 4** för samtliga tickers, oavsett individuellt trailing-värde. Skicka en separat "breadth"-notis med `priority: default`.
- Om guldpris-referensen (`GC=F`) **samtidigt** också är ner mer än en konfigurerbar tröskel (standard −3%) samma dag → **golv höjs till nivå 5** istället, och breadth-notisen skickas med `priority: urgent`. Detta bekräftar att det är en genuin guldrörelse, inte bara att aktiemarknaden i stort drar med sig gruvbolag (vilket delvis hände under tvångsförsäljningarna våren 2026).

### 7.3 `config/thresholds.json` – schema

```json
{
  "trailing_levels": { "1": 2, "2": 4, "3": 6, "5": 8 },
  "ma_periods": [50, 100],
  "ma100_escalates_by_levels": 1,
  "swing_low_lookback_days": 60,
  "down_streak_min_days": 3,
  "confluence_required_for_level_3": 2,
  "confluence_required_for_level_5": 3,
  "breadth": {
    "daily_drop_threshold_pct": 4,
    "min_count": 3,
    "floor_level_without_gold_confirmation": 4,
    "floor_level_with_gold_confirmation": 5,
    "gold_confirmation_threshold_pct": 3
  },
  "notify_only_on_level_increase": true
}
```
Att ändra känslighet = ändra värden i denna fil, ingen kodändring.

## 8. Notiser – ntfy.sh

- Ingen inloggning krävs. Ett hemligt, svårgissat topic-namn väljs (lagras som GitHub Actions secret `NTFY_TOPIC`, inte hårdkodat).
- `notify.py` gör ett enkelt POST:
  ```
  POST https://ntfy.sh/<NTFY_TOPIC>
  Headers: Priority: low | default | urgent
  Body: text med ticker, nivå, trailing-%, ev. breadth-info
  ```
- Nivå 1–2: ingen notis alls, bara UI-färg.
- Nivå 3: `priority: low` (syns i notismenyn, ljudlöst).
- Nivå 4: `priority: default` (normal notis-signal).
- Nivå 5: `priority: urgent` (kan konfigureras att upprepas tills kvitterad, se ntfy-dokumentation för `Actions`/`Delay`-headers om det önskas i senare iteration – ej MVP-krav).

## 9. PWA – frontend-krav

- `manifest.json`: `"display": "standalone"`, ikon, namn, themefärg.
- `index.html` + `app.js`: hämtar `data/latest_status.json`, renderar en lista/tabell över bevakade instrument med severity-färg, senaste pris, trailing-%, samt en tydlig indikator om breadth-larm är aktivt.
- `navigator.setAppBadge(n)` sätts till antal instrument på nivå 3+ (kräver installerad PWA, funkar på Android och iOS 16.4+).
- Ingen inloggning, ingen backend-koppling förutom att läsa den statiska JSON-filen.
- Responsiv för mobilskärm i första hand.

## 10. Icke-funktionella krav / kända begränsningar

- **GitHub Actions schemaläggning** är inte exakt på minuten – kan förskjutas vid hög belastning på GitHub:s sida. Acceptabelt för timvis bevakning, inte lämpligt om sub-minut-precision skulle behövas senare.
- **yfinance** är ett inofficiellt bibliotek som skrapar Yahoo Finance-data. Kan sluta fungera vid ändringar hos Yahoo. Ingen SLA. Om detta blir ett problem i drift, utred alternativ datakälla som en separat uppgift (ej MVP-scope).
- **Repo-synlighet**: rekommenderas publikt (obegränsade gratis Actions-minuter). Om privat: 2000 gratis minuter/månad på Free-plan, vilket räcker för timvis körning men bör hållas under uppsikt.
- Workflow-permissions måste sättas till "Read and write" under Settings → Actions → General, annars kan jobbet inte committa tillbaka data.

## 11. Utanför scope för MVP (möjlig senare utveckling)

- Automatisk säljorder-koppling till mäklare (Avanza saknar öppet API för detta – skulle kräva annan lösning).
- Riktig Web Push direkt till PWA:n (VAPID/service worker) som alternativ till ntfy – inte nödvändigt då ntfy löser behovet enklare.
- Historisk backtesting av severity-modellen mot tidigare kraschperioder (t.ex. våren 2026) för att kalibrera trösklarna – rekommenderas som uppföljande arbete när verklig data samlats in.
- Egen domän via Cloudflare eller annan DNS-leverantör – rent kosmetiskt.

## 12. Öppna frågor till utvecklaren

1. Verifiera att `EDV.L`/`EDV.TO` och `NST.AX` faktiskt returnerar data via befintlig YF-hämtningsmodul (icke-amerikanska börser hanteras ibland annorlunda).
2. Bekräfta att beställaren accepterar att repot/Pages-sajten är publik (se avsnitt 13) innan launch, eller besluta att bygga Cloudflare Access-varianten direkt istället för att lägga till den senare.

## 13. Miljö och åtkomst

- **Repo**: [github.com/Janne-sz/golden_slumbers](https://github.com/Janne-sz/golden_slumbers) (ägare: `Janne-sz`).
- **ntfy-topic**: `Guldet-48gk62bx`. Ska **inte** hårdkodas i koden. Lägg den som ett repository secret: Settings → Secrets and variables → Actions → New repository secret → namn `NTFY_TOPIC`, värde `Guldet-48gk62bx`. `notify.py` läser den via miljövariabel (`os.environ["NTFY_TOPIC"]`), och workflow-filen exponerar secreten till jobbet via `env:`.
- **Workflow-permissions**: kom ihåg att sätta "Read and write permissions" under Settings → Actions → General → Workflow permissions (se avsnitt 10), annars kan jobbet inte committa `data/`-filerna.
- **Publikt/privat repo – beslutat**: repot måste vara **publikt** för att GitHub Pages ska fungera alls. På GitHub Free/Pro för privatpersoner går det inte att publicera en privat Pages-sajt – det kräver GitHub Enterprise Cloud med organisationskonto, vilket är orimligt för ett personligt projekt. Konsekvens: bevakningslistan (bolagsnamn/tickers) och aktuella severity-nivåer/drawdown-% blir synliga för den som känner till URL:en. Inga kontosaldon, innehavsstorlekar eller personuppgifter exponeras. Bedömd risknivå: låg, accepteras för MVP.
  - **Om verklig åtkomstkontroll önskas senare**: byt hosting av `docs/`-mappen från GitHub Pages till **Cloudflare Pages + Cloudflare Access** (gratis, riktig inloggning via e-post-OTP). GitHub Actions/repo fortsätter sköta all beräkning och committar `data/latest_status.json` som vanligt – bara den statiska sajten som visar datan flyttar värd. Ett lösenord implementerat enbart i JavaScript på klientsidan är **inte** en riktig lösning (går trivialt att kringgå) och ska undvikas.
- **Inloggningsuppgifter till GitHub-kontot**: delades i klartext i chatten där denna spec togs fram. Sådana ska aldrig committas till repot eller stå i ett dokument som delas vidare – de är medvetet uteslutna härifrån. Rekommendation: byt lösenord på kontot, och använd i stället en Personal Access Token eller SSH-nyckel för eventuell git-autentisering lokalt (GitHub Actions behöver ingen inloggning alls – den använder automatiskt genererade `GITHUB_TOKEN`).
