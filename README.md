# three-way
Beheer aandelen.


# "All good things come in three and there are always three ways out"
## Financial system

### The never zero project. 

Predicting, stearing and enumariting information
of financial instruments to maximize returns within a certian amount of time.
The window is not focused on short term profit but the focus is increasing rendement 
over a long time window by calling either , daily, weekly or monthly to. Buy, sell or hold.
Based on three information streems news, financial indicators, and intuiton.
#### news - daily, weekly monthly -- general, financial, socila media -- 40%
#### financial indicators -- monthly, yearly, overall -- 40%
#### intuition -- gut feeling, observations, financial situation -- 20% 

### Gebruik
Elke maandag, woensdag en vrijdag: `python main.py`. Alleen dat.
Eens per maand (of als main zegt dat de regel oud is): `python walkforward.py`.

| Bestand | Vraag die het beantwoordt | Wanneer |
|---|---|---|
| `main.py` | Wat doe ik nu met elk aandeel? | ma, wo, vr |
| `walkforward.py` | Welke instelling van de regel werkte het beste de afgelopen 5 jaar? Slaat die op in `data/rule.json`. | maandelijks |
| `backcasting.py` | Hoe had de regel de laatste 3 maanden gedaan, en wat is het maximum? | als je wilt kijken |

De instelling wordt gekozen op het aandeel van periodes van twee maanden waarin de regel beter was dan
vasthouden. Recente periodes tellen zwaarder: een periode telt half zo zwaar voor elke 6 periodes (ongeveer een jaar)
die hij verder terug ligt (`RECENCY_HALF_LIFE_WINDOWS` in `constants.py`).

Alle drie gebruiken dezelfde regel (`rule.py`) met dezelfde instelling (`data/rule.json`),
dus main toont zelf ook het bewijs van de regel. Nieuws en intuitie (en analyse) zitten alleen in main,
want daar bestaat geen historie van. Tot er een maand checks in `data/checks.json` staan.

### Bestanden
| Bestand | Inhoud |
|---|---|
| `main.py`, `walkforward.py`, `backcasting.py` | De drie scripts |
| `constants.py`, `imports.py` | Alle constanten, alle imports |
| `market.py` | Yahoo, koersen, holdings |
| `rule.py` | De regel en de beslissing |
| `testing.py` | De rollende test van de regel |
| `analysis.py` | Fundamentals, analistenverwachting, ingevoerde scores |
| `storage.py` | Opgeslagen checks, cash-status, snapshots en regel |
| `report.py` | Overzicht van main en portefeuilletabel |