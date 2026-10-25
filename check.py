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
    url = f"https://agents.ulysse.com/api/search?origin=CDG&destination=LIM&departure_date={dep}&return_date={ret}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode())
            req_id = data.get("id")
            if not req_id: return []
            
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
        
    af_prices = []  
    other_prices = []
    
    for o in offers:
        price = float(o.get("total", {}).get("amount", 0))
        carrier = o.get("owner", {}).get("iata_code", "")
        
        # On vérifie le nombre d'escales
        slices = o.get("slices", [])
        max_segments = 0
        for s in slices:
            max_segments = max(max_segments, len(s.get("segments", [])))
            
        # CORRECTION ICI : On accepte Air France direct (0 escale) OU 1 escale max (2 segments)
        if carrier == "AF" and max_segments <= 2:
            af_prices.append(price)
        else:
            other_prices.append((price, carrier))

    best_af = min(af_prices) if af_prices else None
    best_other = min(other_prices, key=lambda x: x[0]) if other_prices else (None, None)

    # Application de la règle des 30%
    if best_af and best_other[0]:
        seuil_30 = round(best_af * 0.70)
        if best_other[0] <= seuil_30:
            retained_price = best_other[0]
            choice = f"✈️ AUTRE ({best_other[1]}) - {round((1 - best_other[0]/best_af)*100)}% moins cher (AF à {best_af} €)"
        else:
            retained_price = best_af
            choice = f"🇫🇷 AIR FRANCE - (Autre moins cher : {best_other[0]} €)"
    elif best_af:
        retained_price = best_af
        choice = "🇫🇷 AIR FRANCE - Pas de concurrence"
    elif best_other[0]:
        retained_price = best_other[0]
        choice = f"✈️ AUTRE ({best_other[1]}) - Pas d'AF trouvé"
    else:
        return None

    return {
        "dep": dep, "ret": ret,
        "price": retained_price,
        "choice": choice,
        "af": best_af,
        "other": best_other[0]
    }

print("🤖 Démarrage de l'analyse...")
results = []
for dep, ret in COMBOS:
    res = analyze_combo(dep, ret)
    if res:
        results.append(res)

results.sort(key=lambda x: x["price"])

print("\n--- RÉSULTATS ---")
for r in results:
    print(f"{r['dep']} au {r['ret']} : {r['price']} € | {r['choice']}")
