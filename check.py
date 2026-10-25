import json, time, urllib.request, os

# ── Les fenêtres de dates à surveiller (août 2027, 15 à 20 jours) ──
COMBOS = [
    ("2027-08-03", "2027-08-20"), # 17 jours
    ("2027-08-06", "2027-08-22"), # 16 jours
    ("2027-08-09", "2027-08-27"), # 18 jours
    ("2027-08-12", "2027-08-27"), # 15 jours
    ("2027-08-15", "2027-09-03"), # 19 jours
    ("2027-08-18", "2027-09-04")  # 17 jours
]

def fetch_flights(dep, ret):
    print(f"🔎 Recherche pour {dep} -> {ret}...")
    # 1. Lancer la recherche
    url = f"https://agents.ulysse.com/api/search?origin=CDG&destination=LIM&departure_date={dep}&return_date={ret}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode())
            req_id = data.get("id")
            if not req_id: return []
            
        # 2. Attendre que la recherche soit terminée (on essaie 10 fois)
        for _ in range(10):
            time.sleep(3)
            res_url = f"https://agents.ulysse.com/api/offer_requests/{req_id}"
            with urllib.request.urlopen(res_url, timeout=15) as r:
                res_data = json.loads(r.read().decode())
                if res_data.get("status") == "completed":
                    return res_data.get("offers", [])
        return []
    except Exception as e:
        print(f"❌ Erreur technique : {e}")
        return []

def analyze_combo(dep, ret):
    offers = fetch_flights(dep, ret)
    if not offers:
        return None
        
    af_direct_prices = []
    other_prices = []
    
    for o in offers:
        # Récupérer le prix total (converti en float)
        price = float(o.get("total", {}).get("amount", 0))
        
        # Récupérer la compagnie
        carrier = o.get("owner", {}).get("iata_code", "")
        
        # Vérifier si c'est un vol direct (1 seul segment à l'aller ET au retour)
        slices = o.get("slices", [])
        is_direct = True
        if len(slices) > 0:
            for s in slices:
                if len(s.get("segments", [])) > 1:
                    is_direct = False
                    break
        
        # Trier : Air France direct vs le reste
        if carrier == "AF" and is_direct:
            af_direct_prices.append(price)
        else:
            other_prices.append((price, carrier))

    # Trouver les meilleurs prix
    best_af = min(af_direct_prices) if af_direct_prices else None
    best_other = min(other_prices, key=lambda x: x[0]) if other_prices else (None, None)

    # Appliquer votre règle des -30%
    if best_af and best_other[0]:
        seuil_30 = round(best_af * 0.70)
        if best_other[0] <= seuil_30:
            retained_price = best_other[0]
            choice = f"✈️ AUTRE ({best_other[1]}) - {round((1 - best_other[0]/best_af)*100)}% moins cher"
        else:
            retained_price = best_af
            choice = "🇫🇷 AIR FRANCE (Direct)"
    elif best_af:
        retained_price = best_af
        choice = "🇫🇷 AIR FRANCE (Direct)"
    elif best_other[0]:
        retained_price = best_other[0]
        choice = f"✈️ AUTRE ({best_other[1]}) - Pas d'AF direct"
    else:
        return None

    return {
        "dep": dep, "ret": ret,
        "price": retained_price,
        "choice": choice,
        "af_direct": best_af,
        "best_other": best_other[0]
    }

print("🤖 Démarrage de l'analyse...")
results = []
for dep, ret in COMBOS:
    res = analyze_combo(dep, ret)
    if res:
        results.append(res)

# Trier par prix croissant
results.sort(key=lambda x: x["price"])

print("\n--- RÉSULTATS ---")
for r in results:
    print(f"{r['dep']} au {r['ret']} : {r['price']} € | {r['choice']}")
