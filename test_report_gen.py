import sys, importlib
sys.path.insert(0, '.')
import report
importlib.reload(report)

tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

module1 = {
    "turbines": [{"label": "Turbine 1", "lat": 52.05, "lon": 5.05, "category_label": "Hoog (> 150 m tiphoogte)", "method": "flat"}],
    "warnings": [],
    "buurten": [
        {"buurtnaam": "Cattenbroek", "gemeentenaam": "Woerden", "afstand_centroide_m": 850, "geraakte_woningen": 120.5,
         "gemiddelde_woz": 385000, "gewogen_waardedaling_pct": -4.2, "max_waardedaling_pct": -5.4,
         "totale_waardedaling_euro": 1950000, "waardedaling_per_woning_euro": 16182, "nadeelcompensatie_euro": 450000},
        {"buurtnaam": "Kamerik", "gemeentenaam": "Woerden", "afstand_centroide_m": 1600, "geraakte_woningen": 60.0,
         "gemiddelde_woz": 410000, "gewogen_waardedaling_pct": -2.1, "max_waardedaling_pct": -4.0,
         "totale_waardedaling_euro": 517000, "waardedaling_per_woning_euro": 8617, "nadeelcompensatie_euro": 90000},
    ],
    "totalen": {
        "aantal_buurten": 2, "totaal_geraakte_woningen": 180.5, "totale_waardedaling_euro": 2467000,
        "gemiddelde_waardedaling_per_woning_euro": 13667, "totaal_normaal_maatschappelijk_risico_euro": 1927000,
        "totaal_nadeelcompensatie_euro": 540000, "gemiddelde_nadeelcompensatie_per_woning_euro": 2992,
    },
}

def make_drempel(pct, houses, hh, per_person=609.60, dw=0.021):
    n_pers = houses * hh
    cost_year = n_pers * per_person
    cost_25 = cost_year * 25
    daly_year = n_pers * dw
    daly_25 = daly_year * 25
    return {
        "drempel_pct": pct, "aantal_woningen": round(houses,1), "aantal_personen": round(n_pers,1),
        "kosten_per_jaar_euro": round(cost_year), "kosten_25jaar_euro": round(cost_25),
        "daly": {
            "daly_totaal_jaar": round(daly_year,3), "daly_totaal_25jaar": round(daly_25,2),
            "waarde_rivm_jaar_euro": round(daly_year*50000), "waarde_pbl_jaar_euro": round(daly_year*70000),
            "waarde_zin_jaar_euro": round(daly_year*80000),
            "waarde_rivm_25jaar_euro": round(daly_year*50000*25), "waarde_pbl_25jaar_euro": round(daly_year*70000*25),
            "waarde_zin_25jaar_euro": round(daly_year*80000*25),
        }
    }

rows = []
for dist, houses in [(500, 30), (800, 70), (1300, 150), (2000, 260), (5000, 900)]:
    hh = 2.2
    rows.append({
        "afstand_m": dist, "aantal_woningen": houses, "dba_7ms": 45 - dist/200, "db_onweighted": 55 - dist/200,
        "personen_per_huishouden": hh,
        "drempels": [make_drempel(9, houses, hh), make_drempel(30, houses, hh), make_drempel(46, houses, hh)],
    })

module23 = {"rijen": rows}

module4 = {
    "rijen": [
        {"label": "Groep 1", "hoofdcategorie_label": "Regulier", "windcategorie": "III", "vermogen_per_turbine_mw": 6.0,
         "aantal_turbines": 3, "vermogen_totaal_mw": 18.0, "investering_totaal_euro": 27720000,
         "kosten_per_mwh_jaar1_euro": 62.3, "kosten_per_mwh_levensduur_euro": 62.3},
    ],
    "totalen": {"vermogen_totaal_mw": 18.0, "aantal_turbines_totaal": 3, "investering_totaal_euro": 27720000,
                "gem_kosten_per_mwh_levensduur_euro": 62.3},
}

module2a = {
    "wind_from_label": "zuidwesten",
    "downwind_label": "noordoosten",
    "sound_types": [
        {"key": "hoorbaar", "label": "Hoorbaar geluid",
         "day": {"base_km": 1.2, "downwind": 1.25, "upwind": 0.55},
         "night": {"base_km": 1.8, "downwind": 1.35, "upwind": 0.5}},
        {"key": "laagfrequent", "label": "Laagfrequent geluid",
         "day": {"base_km": 2.0, "downwind": 1.15, "upwind": 0.75},
         "night": {"base_km": 3.0, "downwind": 1.2, "upwind": 0.7}},
        {"key": "infrasoon", "label": "Infrasoon geluid",
         "day": {"base_km": 6.0, "downwind": 1.05, "upwind": 0.95},
         "night": {"base_km": 12.0, "downwind": 1.05, "upwind": 0.95}},
    ],
}

data = {
    "turbines": module1["turbines"],
    "module1": module1,
    "module23": module23,
    "module2a": module2a,
    "module4": module4,
    "map1_image": tiny_png_b64,
    "map2_image": tiny_png_b64,
    "map2a_day_image": tiny_png_b64,
    "map2a_night_image": tiny_png_b64,
    "generated_at": "06-09-2026 09:40",
}

pdf_bytes = report.build_report_pdf(data)
open('/home/user/workspace/test_report.pdf', 'wb').write(pdf_bytes)
print("PDF size:", len(pdf_bytes))
