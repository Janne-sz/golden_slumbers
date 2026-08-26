# Guldbevakare – implementerad lösning och användarmanual

Senast uppdaterad: 25 augusti 2026. Detta dokument beskriver den funktionalitet som finns i `main` i dag. För framtida idéer, se [FRAMTIDA_ANDRINGAR.md](FRAMTIDA_ANDRINGAR.md).

## Versionshistorik

Projektet använder Git som versionshistorik. Varje implementation och varje automatisk marknadsuppdatering får en commit i GitHub-repot.

- `Build gold equity alert MVP` – första fungerande PWA, datahämtning, severity och ntfy.
- `Fix intraday Yahoo Finance start time` – rättade timhämtning och säkerställde att dagliga kurser sparas vid intradagfel.
- `Show gold signals and monitor-relative drawdown` – guldsektion överst, tre förändringsmått, peak-backfill, ATH-referens och stale-data-hantering.
- `Refresh gold market status` – automatiska commits från GitHub Actions med uppdaterad marknadsdata och PWA-status.

Historiken finns under repots flik **Commits**. Återställning till en tidigare version bör göras genom en ny, explicit revert-commit – inte genom att skriva över historik.

## Vad systemet gör

Guldbevakare övervakar tolv guldgruveaktier som proxy för två guldgruvefonder. Det är ett informations- och larmsystem: det lägger aldrig order och ger inte personlig investeringsrådgivning.

Varje schemalagd körning hämtar Yahoo Finance-data, uppdaterar den lokala historiken, beräknar indikatorer och skriver en kompakt statusfil som PWA:n läser. GitHub Actions kör normalt varje timme vid minut 17 UTC; GitHub kan fördröja en schemalagd körning.

### Bevakade data

- **Guldgruveaktier och ETF:er:** GOLD, NEM, AU, WPM, FNV, KGC, AEM, AGI, EDV.L, NST.AX, GFI, PAAS, GDX och IS0E.DE. ETF:erna visas och kan larma individuellt, men räknas inte in i breadth-larmet.
- **Guldreferens:** `GC=F`, COMEX-guldterminen från Yahoo Finance. Detta är en futuresreferens, inte ett rent spotpris.
- **Fysisk guldreferens:** PPFB.DE (iShares Physical Gold ETC, Xetra) visas under övriga referenser.
- **Fond-NAV:** BGF World Gold och CPR Global Gold Mines visas som referenser när Yahoo Finance-data finns, men används inte i breadth-larmet.

## Använd PWA:n

Öppna [PWA:n](https://janne-sz.github.io/golden_slumbers/) på iPhone i Safari och välj **Dela → Lägg till på hemskärmen**. Öppna sedan ikonen som en vanlig app.

PWA:n visar aktuell status när den öppnas. Appens skal cachas för snabb start, men `latest_status.json` hämtas på nytt varje gång den öppnas. Efter en UI-deploy kan du stänga och öppna appen igen om iOS ännu visar en äldre layout.

### Guldpris överst

Guldsektionen ligger överst eftersom den används som bekräftelse i sektorlarmet. Den visar tre olika mått som inte ska blandas ihop:

1. **Sedan peak** – drawdown från bevakningssystemets egen peak; detta är huvudtalet och styr severity.
2. **Sedan stängningen Må dd/mm** – förändring mot Yahoo Finance `previousClose`, med den stängningsdag som används direkt i etiketten. Detta är samma tal som breadth-regeln använder.
3. **Sedan HH:MM** – tre kortsiktiga förändringar från de senast tillgängliga 1-, 2- och 4-timmarsstaplarna. Klockslagen visas i svensk tid.

Den informativa raden **Sedan ATH** är helt frikopplad från larm. För `GC=F` används 5 589 USD den 28 januari 2026 som konfigurerad historisk referens.

### Guldgruveaktier

Varje aktiekort använder samma mått. **Sedan peak** visas störst, eftersom nivå 1–5 bygger på detta mått. Om ingen ny datapunkt har kommit på 90 minuter eller mer visar kortet när datan senast kom in. Knappen **Uppdatera** laddar om sidan, kontrollerar en ny service-worker-version och hämtar den senaste publicerade statusfilen; den kan inte själv starta Yahoo-hämtningen, som görs av GitHub Actions.

Peak är inte instrumentets all-time-high. Vid första bevakningen initieras den från högsta stängning under de senaste 45 handelsdagarna, och stiger därefter bara när systemet observerar en ny högre kurs. Därför kan systemet upptäcka nästa tydliga nedgång utan att permanent larma för en gammal topp.

## Larmnivåer

Alla trösklar ligger i `config/thresholds.json` och kan ändras utan kodändring.

| Nivå | Standardvillkor | Notis |
|---|---|---|
| 1 | Drawdown från peak minst 2 % | Ingen |
| 2 | Drawdown minst 4 % | Ingen |
| 3 | Drawdown minst 6 %, eller minst två av: under MA50, nytt 60-dagars swing low, minst tre negativa stängningar i följd | ntfy low, ljudlös |
| 4 | Drawdown minst 6 % och minst två av konfluensvillkoren | ntfy default |
| 5 | Drawdown minst 8 % och alla tre konfluensvillkoren | ntfy urgent |

Om en aktie minst är nivå 3 och även ligger under MA100, höjs den en extra nivå. MA100 räknas medvetet inte som ytterligare en konfluenspunkt, eftersom MA50 och MA100 är starkt korrelerade.

### Breadth / sektorlarm

Breadth räknar hur många bevakade aktier som faller minst 4 % sedan föregående stängning. När minst tre aktier gör det samtidigt:

- får alla instrument minst nivå 4 och en separat ntfy-notis skickas med normal prioritet;
- om `GC=F` samtidigt har fallit minst 3 % sedan föregående stängning, höjs golvet till nivå 5 och notisen blir urgent.

En aktie skickar bara en ny individuell notis när dess grundnivå höjs. Ett breadth-larm skickar en separat notis när sektorlarmet går från inaktivt till aktivt, inte en notis per aktie.

## Drift och felsökning

- **Datakälla:** yfinance/Yahoo Finance är en extern, inofficiell källa. Saknade eller försenade data kan förekomma.
- **Status:** PWA:n visar `Data saknas` om kursserien inte gått att hämta. `degraded` i statusfilen betyder att minst en ticker hade ett hämtningsfel.
- **Notiser:** ntfy-topic lagras som repository secret `NTFY_TOPIC`; topic-värdet får inte läggas i kod eller dokumentation.
- **Manuell körning:** GitHub Actions → `Poll gold equities` → `Run workflow`. Kontrollera körningsloggen om data inte uppdateras.
- **Publik information:** PWA, bevakningslista och aktuella signaltal är offentliga. Systemet innehåller inga belopp, konton eller orderfunktioner.
