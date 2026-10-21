# VAA Strategy

Aplicatie pentru calcularea automata a strategiei Vigilant Asset Allocation (VAA) - varianta Agresiva.

## Ce face

- Descarca automat preturile ETF-urilor din `assets.json` folosind yfinance.
- Calculeaza scorul de momentum ponderat: `12*r1 + 4*r3 + 2*r6 + r12` (r_n = randament fata de acum n luni).
- Aplica regulile de alocare VAA si afiseaza verdictul (100% ofensiv / 50-50 / 100% defensiv).
- Trateaza cele doua ETF-uri din sectorul rotativ "hot" (Energie) ca un singur semnal.

## Instalare

```bash
pip install -r requirements.txt
```

## Rulare

Interfata web (recomandat):
```bash
streamlit run app.py
```

Linie de comanda:
```bash
python main.py
```

## Structura

- `assets.json` - lista de ETF-uri ofensive/defensive, cu tickere Yahoo Finance si ISIN-uri.
- `logic.py` - descarcare date, calcul momentum, reguli de alocare.
- `app.py` - interfata Streamlit.
- `main.py` - rulare rapida in consola.

## Configurare active

Editeaza `assets.json` pentru a adauga/schimba ETF-uri. Tickerul trebuie sa fie recunoscut de Yahoo Finance
(verifica sufixul bursei, ex: `.DE` pentru Xetra, `.L` pentru Londra).
