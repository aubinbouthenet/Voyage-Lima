import json, time, urllib.request, os
from datetime import date

# ── Les fenêtres de dates à surveiller (août 2027, 15 à 20 jours) ──
COMBOS = [
    ("2027-08-03", "2027-08-20"),
    ("2027-08-06", "2027-08-22"),
    ("2027-08-09", "2027-08-27"),
    ("2027-08-12", "2027-08-27"),
    ("2027-08-15", "2027-09-03"),
    ("2027-08-18", "2027-09-04")
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
        print(f"❌ Erreur : {e}")
        return []

print("🤖 Démarrage de l'analyse...")
all_offers = []

for dep, ret in COMBOS:
    offers = fetch_flights(dep, ret)
    for o in offers:
        price = float(o.get("total", {}).get("amount", 0))
        carrier = o.get("owner", {}).get("iata_code", "?")
        name = o.get("owner", {}).get("name", "Inconnue")
        
        # Nombre d'escales
        slices = o.get("slices", [])
        stops = 0
        for s in slices:
            stops += max(0, len(s.get("segments", [])) - 1)
            
        all_offers.append({
            "dep": dep,
            "ret": ret,
            "price": price,
            "airline_code": carrier,
            "airline_name": name,
            "stops": stops
        })

# On trie toutes les offres par prix croissant
all_offers.sort(key=lambda x: x["price"])
top_3 = all_offers[:3]

# ── Préparation des données pour le site web ──
data_to_save = {
    "last_update": date.today().isoformat(),
    "top_offers": top_3,
    "all_offers": all_offers[:20] # On garde les 20 meilleures
}

with open("prices.json", "w") as f:
    json.dump(data_to_save, f, indent=2)

print("\n--- TOP 3 DES VOLS ---")
for i, o in enumerate(top_3):
    print(f"{i+1}. {o['price']} € | {o['airline_name']} ({o['stops']} escale(s)) | {o['dep']} au {o['ret']}")

# ── Envoi de la notification ntfy ──
topic = os.environ.get("NTFY_TOPIC")
if topic and top_3:
    lignes = []
    for i, o in enumerate(top_3):
        lignes.append(f"{i+1}. {o['price']} € : {o['airline_name']} ({o['dep']} au {o['ret']})")
    
    msg = "\n".join(lignes)
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=msg.encode('utf-8'),
        headers={"Title": "✈️ Top 3 Vols Lima du jour", "Tags": "airplane"}
    )
    urllib.request.urlopen(req, timeout=10)
