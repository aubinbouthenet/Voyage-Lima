import json, time, urllib.request

# On teste sur une seule date pour aller plus vite
dep = "2027-08-03"
ret = "2027-08-20"

def fetch_flights(dep, ret):
    print(f"🔎 Diagnostic pour {dep} -> {ret}...")
    url = f"https://agents.ulysse.com/api/search?origin=CDG&destination=LIM&departure_date={dep}&return_date={ret}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode())
            req_id = data.get("id")
            
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

offers = fetch_flights(dep, ret)

print(f"\n--- {len(offers)} VOLS TROUVÉS ---")
for o in offers:
    # On récupère le prix
    price = float(o.get("total", {}).get("amount", 0))
    
    # On récupère la compagnie selon l'API (Owner)
    owner = o.get("owner", {})
    code = owner.get("iata_code", "?")
    name = owner.get("name", "Inconnu")
    
    # On regarde aussi dans les détails du vol (souvent plus fiable)
    slices = o.get("slices", [])
    companies_in_segments = []
    if slices:
        for s in slices:
            for seg in s.get("segments", []):
                mc = seg.get("marketing_carrier", {}).get("iata_code")
                if mc and mc not in companies_in_segments:
                    companies_in_segments.append(mc)
                    
    print(f"Prix: {price} € | Compagnie (Owner): {code} ({name}) | Dans les vols: {', '.join(companies_in_segments)}")
