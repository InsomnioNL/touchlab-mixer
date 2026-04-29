# Code-style notes — index.html

## One-liner if-guards zijn een bewuste keuze

De codebase gebruikt consequent one-liner guards zonder accolades
voor enkele-statement-checks, bijvoorbeeld:

    if(btn) btn.classList.add('active');
    if(!el || el._swipe) return;
    if(ws && ws.readyState===1) ws.send(...);

Dit is geen bug en hoeft niet "gefixed" te worden. Het is een
stilistische keuze voor compactheid in deze single-file UI.

## Wel een echte fix-kandidaat

Een if/else waarbij de takken asymmetrisch zijn — bv. if-tak met
accolades en meerdere statements, else-tak een naakte one-liner —
is wel een risico-patroon. Bij uitbreiding van de else-tak met een
tweede statement valt die buiten de else en wordt onvoorwaardelijk
uitgevoerd. Dat patroon is opgeruimd in commit 2a5d733
(ELSE-BRACES-BANKTABS-V1).

## Audit-resultaat (29 april 2026)

Discovery-grep over index.html toonde:
- Patroon "if op aparte regel zonder body": 0 hits
- Patroon "if-met-statement op één regel": ~109 hits, bijna alle
  legitieme one-liner guards
- Patroon "else zonder accolades, single statement": 1 hit
  (regel 1470, opgelost)

Conclusie: codebase is consistent in z'n stijl. Geen verdere
audit-actie nodig tenzij een volgende asymmetrische if/else
opduikt.
