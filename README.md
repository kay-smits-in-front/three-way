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
Draai `python main.py` op maandag, woensdag en vrijdag. Main vraagt nieuws en intuitie (-5 tot +5),
laadt koersen en analyse van Yahoo, toont per aandeel het signaal van de contraire regel en de beslissing
(KOPEN, VERKOPEN of HOUDEN met reden), en bewaart elke check in `data/checks.json`.
`python walkforward.py` toetst de regel op rollende periodes, `python backcasting.py` toont vasthouden tegen maximum.