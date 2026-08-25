# Framtida ändringar och förslag

Den här listan är en prioriterad arbetsyta för förbättringar efter MVP. Lägg nya idéer längst ned med en kort motivering och önskad prioritet.

## Nästa förbättringar

- [ ] **Service-worker-versionering** – skapa ett nytt cache-namn per deploy så att installerade iPhone-PWA:er alltid hämtar nya UI-filer.
- [ ] **Datakvalitet i UI** – visa när en ticker senast lyckades uppdateras och markera föråldrad data tydligt.
- [ ] **Automatiska hämtningstester** – testa YFinance-datumformat, normalisering och inkrementell sammanslagning utan live-anrop.
- [ ] **Historisk kalibrering** – backtesta severity-reglerna mot perioden januari–juni 2026 och justera trösklarna med dokumenterad evidens.
- [ ] **Börssessionsmedveten breadth** – räkna bara instrument med färsk data från sin aktuella lokala handelsdag.
- [ ] **Notifieringssammanfattning** – lägg till tydligare ntfy-text med utlösande indikatorer och direktlänk till PWA:n.

## Senare möjligheter

- [ ] **Cloudflare Access** – flytta den statiska PWA:n om bevakningslistan senare ska kräva inloggning.
- [ ] **Reservdatakälla** – utvärdera en alternativ kurskälla om Yahoo Finance blir instabilt.
- [ ] **Konfigurationspanel** – ett säkert administrativt sätt att ändra bevakningslista och trösklar utan att redigera JSON manuellt.
