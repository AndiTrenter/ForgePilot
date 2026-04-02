# GitHub Build Fix

## Problem
GitHub Actions Build schlug fehl mit:
```
ERROR: No matching distribution found for emergentintegrations==0.1
```

## Lösung
✅ `emergentintegrations` aus `requirements.txt` entfernt

**Warum:** `emergentintegrations` ist nur lokal mit speziellem Index verfügbar:
```bash
--extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

GitHub Actions kann nicht auf diesen privaten Index zugreifen.

## Verifizierung
```bash
✅ emergentintegrations nicht mehr in requirements.txt
✅ Alle verbleibenden Pakete sind public PyPI-Pakete (133 total)
```

## Nächster Build
Der nächste GitHub Actions Build sollte jetzt erfolgreich durchlaufen.

**Commit-Message:**
```
fix: Remove emergentintegrations from requirements.txt for GitHub build

- emergentintegrations is only available via private index
- GitHub Actions cannot access private package index
- All remaining packages are public PyPI packages
```

## Test lokal
```bash
cd /app/backend
pip install -r requirements.txt
# Sollte ohne Fehler durchlaufen
```
