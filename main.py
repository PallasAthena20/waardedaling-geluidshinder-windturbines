#!/usr/bin/env python3
"""
Vercel serverless entrypoint. Combines the calc engine and FastAPI routes
in a single file (Vercel Python functions treat every top-level .py file
under /api as its own function entrypoint, so shared modules must be
either inlined here or placed outside /api).

Rekenmodule: waardedaling woningen door windturbines
Gebaseerd op Droes, M.I. & Koster, H.R.A. (2021) - "Wind turbines, solar
farms, and house prices", Energy Policy 155, 112327.
https://doi.org/10.1016/j.enpol.2021.112327
"""
import csv
import io
import json
import math
import os
import traceback
import urllib.parse
from dataclasses import dataclass

import pyproj
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from shapely.geometry import Point, shape, mapping
from shapely.ops import transform as shp_transform

RD = "EPSG:28992"
WGS84 = "EPSG:4326"
_to_wgs84 = pyproj.Transformer.from_crs(RD, WGS84, always_xy=True).transform
_to_rd_transformer = pyproj.Transformer.from_crs(WGS84, RD, always_xy=True)

PDOK_GEOCODE = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
CBS_WFS = "https://service.pdok.nl/cbs/wijkenbuurten/2024/wfs/v1_0"

NMR_THRESHOLD = 0.04  # 4% normaal maatschappelijk risico

# ---------------------------------------------------------------------------
# Geluidshinder-module (nieuw)
# ---------------------------------------------------------------------------
# Bronvermogen turbine bij 7 m/s (door gebruiker opgegeven referentiewaarde,
# representatief voor een moderne turbine van ca. 3-4 MW):
NOISE_LW_A = 108.0   # dB(A), A-gewogen bronvermogenniveau
NOISE_LW_LIN = 117.0  # dB,   lineair (onweighted) bronvermogenniveau

# Vaste beoordelingsafstanden zoals opgegeven door gebruiker
NOISE_DISTANCES_M = [500, 1000, 1200, 5000, 10000]

# Geluidskosten-aanname: gemiddelde jaarlijkse zorgkosten (huisarts/ziekenhuis
# e.d.) per getroffen woning bij aantoonbare (ernstige) hinder, en de
# beschouwingstermijn in jaren — beide expliciet door de gebruiker opgegeven.
NOISE_COST_PER_HOUSE_PER_YEAR = 2000.0
NOISE_COST_HORIZON_YEARS = 25

# Hinderdrempels waarvoor het model apart het aantal getroffen woningen en de
# bijbehorende kosten toont.
NOISE_HINDER_THRESHOLDS_PCT = [10.0, 30.0]

# TNO (2008) dosis-effectrelatie is gefit op Lden = 29-50 dB(A); buiten dat
# bereik extrapoleert de kubische polynoom onbetrouwbaar. Onder de ondergrens
# nemen we aan dat het hinderpercentage verwaarloosbaar is (0%); boven de
# bovengrens knippen we de INVOERWAARDE af op 50 dB voor de polynoom, zodat
# het model niet buiten het gevalideerde bereik extrapoleert.
_TNO_LDEN_FIT_MIN = 29.0
_TNO_LDEN_FIT_MAX = 50.0


def _propagation_level(lw: float, r: float) -> float:
    """RIVM-vuistregel voor windturbinegeluid op afstand R (meter):
    Limm = Lw - 20*log10(R) - 9 - 0.005*R
    Bron: RIVM briefrapport 609333002 \"Windturbines: invloed op de beleving
    en gezondheid van omwonenden\", bijlage 3 (afgeleid van Pedersen et al.,
    project WINDFARMperception, 2008). Nauwkeurigheid ca. ±3 dB.
    https://www.platformstorm.nl/downloads/windturbines_ggd.pdf
    """
    if r <= 0:
        return lw
    return lw - 20 * math.log10(r) - 9 - 0.005 * r


def _pct_hinder_buiten(lden_proxy: float) -> float:
    """% (algemeen) gehinderden, buitenwaarde, TNO 2008-D-R1051/B (Janssen,
    Vos & Eisses), sectie 5.4, gefit op Lden 29-50 dB(A).
    https://www.tno.nl/media/2187/hinder_door_geluid_van_windturbines.pdf
    """
    if lden_proxy < _TNO_LDEN_FIT_MIN:
        return 0.0
    l = min(lden_proxy, _TNO_LDEN_FIT_MAX)
    pct = 34.25 - 0.864 * l - 0.0548 * l**2 + 0.001551 * l**3
    return max(0.0, min(100.0, pct))


def _pct_ernstige_hinder_buiten(lden_proxy: float) -> float:
    """% ernstig gehinderden, buitenwaarde, TNO 2008-D-R1051/B, sectie 5.4."""
    if lden_proxy < _TNO_LDEN_FIT_MIN:
        return 0.0
    l = min(lden_proxy, _TNO_LDEN_FIT_MAX)
    pct = -97.94 + 9.627 * l - 0.3175 * l**2 + 0.003522 * l**3
    return max(0.0, min(100.0, pct))


def _houses_within_radius(turbines: list, radius_m: float) -> float:
    """Telt (fractioneel, naar oppervlakte-aandeel) het aantal woningen dat
    ligt binnen de vereniging van cirkels met straal radius_m rond elke
    turbine. Hergebruikt de CBS-buurt/WFS-infrastructuur van de
    waardedalingsmodule, maar dan als simpele schijf (geen effectbanden)."""
    from shapely.ops import unary_union

    discs = [Point(t.x, t.y).buffer(radius_m, quad_segs=48) for t in turbines]
    union = unary_union(discs) if len(discs) > 1 else discs[0]

    buurten_by_code = {}
    for t in turbines:
        feats = _fetch_buurten(t.x, t.y, radius_m)
        for feat in feats:
            code = feat["properties"]["buurtcode"]
            if code not in buurten_by_code:
                buurten_by_code[code] = feat

    total_houses = 0.0
    for feat in buurten_by_code.values():
        props = feat["properties"]
        wv = props.get("woningvoorraad")
        if wv is None or wv < 0:
            continue
        try:
            geom = shape(feat["geometry"])
        except Exception:
            continue
        if not geom.is_valid:
            geom = geom.buffer(0)
        area = geom.area
        if area <= 0:
            continue
        inter = union.intersection(geom)
        if inter.is_empty:
            continue
        total_houses += wv * (inter.area / area)
    return total_houses


def calculate_noise(turbines: list) -> dict:
    """Bouwt de geluidshinder-tabel voor de vaste beoordelingsafstanden.
    dBA/dB zijn pure fysica (functie van R en het bronvermogen, onafhankelijk
    van het aantal turbines); het aantal woningen binnen elke straal wordt
    wél berekend op basis van de daadwerkelijk ingevoerde turbinelocatie(s)
    (vereniging van cirkels, geen dubbeltelling bij overlap)."""
    if not turbines:
        raise ValueError("Geef minimaal één windturbinelocatie op.")

    rows = []
    for r in NOISE_DISTANCES_M:
        houses = _houses_within_radius(turbines, r)
        dba = _propagation_level(NOISE_LW_A, r)
        db_lin = _propagation_level(NOISE_LW_LIN, r)
        pct_hinder = _pct_hinder_buiten(dba)
        pct_ernstig = _pct_ernstige_hinder_buiten(dba)

        row = {
            "afstand_m": r,
            "aantal_woningen": round(houses, 1),
            "dba_7ms": round(dba, 1),
            "db_onweighted": round(db_lin, 1),
            "pct_hinder": round(pct_hinder, 2),
            "pct_ernstige_hinder": round(pct_ernstig, 2),
            "drempels": [],
        }
        for threshold in NOISE_HINDER_THRESHOLDS_PCT:
            # Aantal getroffen woningen = het percentage van de woningen
            # binnen deze afstand dat de opgegeven hinderdrempel ervaart
            # (bijv. 10% of 30% van de woningen op deze afstand), direct
            # doorgerekend naar kosten per jaar en over de beschouwingstermijn.
            n_houses = houses * (threshold / 100.0)
            cost_year = n_houses * NOISE_COST_PER_HOUSE_PER_YEAR
            cost_horizon = cost_year * NOISE_COST_HORIZON_YEARS
            row["drempels"].append(
                {
                    "drempel_pct": threshold,
                    "aantal_woningen": round(n_houses, 1),
                    "kosten_per_jaar_euro": round(cost_year),
                    "kosten_25jaar_euro": round(cost_horizon),
                }
            )
        rows.append(row)

    return {
        "bronvermogen_dba": NOISE_LW_A,
        "bronvermogen_db": NOISE_LW_LIN,
        "kosten_per_woning_per_jaar_euro": NOISE_COST_PER_HOUSE_PER_YEAR,
        "kosten_horizon_jaar": NOISE_COST_HORIZON_YEARS,
        "drempels_pct": NOISE_HINDER_THRESHOLDS_PCT,
        "rijen": rows,
    }

HEIGHT_CATEGORIES = {
    "laag": {
        "label": "Laag (< 50 m tiphoogte)",
        "flat_effect": -0.01,
        "radius_m": 1000,
        "band_effects": None,
        "significant": False,
    },
    "midden": {
        "label": "Midden (50 - 150 m tiphoogte)",
        "flat_effect": -0.03,
        "radius_m": 2000,
        "band_effects": None,
        "significant": True,
    },
    "hoog": {
        "label": "Hoog (> 150 m tiphoogte)",
        "flat_effect": -0.054,
        "radius_m": 2000,
        # bovengrens (m) -> effect; afgelezen uit Fig. 6 Droes & Koster (2021)
        "band_effects": {500: -0.083, 1000: -0.06, 1500: -0.04, 2000: -0.025},
        "significant": True,
    },
}


class GeocodeError(Exception):
    pass


def geocode_suggestions(query: str, rows: int = 5):
    """Geocode a Dutch address/place using the free PDOK Locatieserver.
    Returns a list of candidate matches (address, place, etc.)."""
    r = requests.get(
        PDOK_GEOCODE,
        params={
            "q": query,
            "rows": rows,
            # "gemeente" bewust uitgesloten: de centroïde van een gemeente kan in
            # water vallen (bv. Urk, Almere) en is te grofmazig voor het plaatsen
            # van een turbine. Adres/buurt/wijk/woonplaats geven een punt op het land.
            "fq": "type:(woonplaats OR adres OR buurt OR wijk)",
        },
        timeout=15,
    )
    r.raise_for_status()
    docs = r.json().get("response", {}).get("docs", [])
    out = []
    for d in docs:
        try:
            rd_str = d["centroide_rd"].replace("POINT(", "").replace(")", "")
            x, y = (float(v) for v in rd_str.split())
            ll_str = d["centroide_ll"].replace("POINT(", "").replace(")", "")
            lon, lat = (float(v) for v in ll_str.split())
        except (KeyError, ValueError):
            continue
        out.append(
            {
                "x": x,
                "y": y,
                "lat": lat,
                "lon": lon,
                "label": d.get("weergavenaam", query),
                "type": d.get("type"),
            }
        )
    return out


def geocode(query: str):
    """Return the single best match for a query (first suggestion)."""
    res = geocode_suggestions(query, rows=1)
    if not res:
        raise GeocodeError(f"Geen locatie gevonden voor '{query}'")
    return res[0]


def _rings_for_turbine(x, y, category_key, method):
    """Return list of (Polygon in RD, effect_fraction) rings for one turbine."""
    cat = HEIGHT_CATEGORIES[category_key]
    center = Point(x, y)
    rings = []
    if category_key == "hoog" and method == "afstandsband" and cat["band_effects"]:
        prev_r = 0
        for upper, effect in sorted(cat["band_effects"].items()):
            outer = center.buffer(upper, quad_segs=48)
            inner = center.buffer(prev_r, quad_segs=48) if prev_r > 0 else None
            ring = outer.difference(inner) if inner else outer
            rings.append((ring, effect))
            prev_r = upper
    else:
        disc = center.buffer(cat["radius_m"], quad_segs=48)
        rings.append((disc, cat["flat_effect"]))
    return rings


def _fetch_buurten(x, y, radius_m):
    pad = radius_m + 100
    bbox = f"{x - pad},{y - pad},{x + pad},{y + pad},{RD}"
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "wijkenbuurten:buurten",
        "outputFormat": "json",
        "srsName": RD,
        "bbox": bbox,
    }
    r = requests.get(CBS_WFS, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("features", [])


@dataclass
class Turbine:
    x: float
    y: float
    lat: float
    lon: float
    label: str
    category: str
    method: str = "vlak"  # "vlak" or "afstandsband" (only for hoog)


def calculate(turbines: list):
    if not turbines:
        raise ValueError("Geef minimaal één windturbinelocatie op.")

    # 1. Build all (ring polygon, effect) tuples across all turbines
    all_rings = []
    for t in turbines:
        for poly, effect in _rings_for_turbine(t.x, t.y, t.category, t.method):
            all_rings.append((poly, effect))

    # 2. Fetch candidate buurten near each turbine (deduped by buurtcode)
    buurten_by_code = {}
    warnings = []
    for t in turbines:
        radius = HEIGHT_CATEGORIES[t.category]["radius_m"]
        feats = _fetch_buurten(t.x, t.y, radius)
        heeft_bruikbare_data = False
        for feat in feats:
            code = feat["properties"]["buurtcode"]
            props = feat["properties"]
            wv = props.get("woningvoorraad")
            woz = props.get("gemiddeldeWoningwaarde")
            if wv is not None and woz is not None and wv >= 0 and woz >= 0:
                heeft_bruikbare_data = True
            if code not in buurten_by_code:
                buurten_by_code[code] = feat
        if not heeft_bruikbare_data:
            warnings.append(
                f"Bij '{t.label}' zijn geen woningen met CBS-gegevens gevonden "
                f"binnen {radius} m. Mogelijk ligt de locatie in water, buitenland "
                f"of een gebied zonder woningen — controleer of het gekozen punt "
                f"precies genoeg is (kies bij voorkeur een adres of buurt in plaats "
                f"van een hele gemeente)."
            )

    # 3. Assign each spot in space to the turbine/band with the STRONGEST
    #    (most negative) effect - matches Droes&Koster / TNO methodology.
    all_rings.sort(key=lambda pe: pe[1])  # most negative first
    claimed = None
    partition = []  # list of (polygon, effect)
    for poly, effect in all_rings:
        region = poly.difference(claimed) if claimed is not None else poly
        if not region.is_empty:
            partition.append((region, effect))
        claimed = poly if claimed is None else claimed.union(poly)

    # 4. Intersect partition regions with each buurt, aggregate results
    results = []
    total = {
        "woningen": 0.0,
        "waardedaling": 0.0,
        "compensabel": 0.0,
        "zelfrisico": 0.0,
    }
    for code, feat in buurten_by_code.items():
        props = feat["properties"]
        woningvoorraad = props.get("woningvoorraad")
        woz = props.get("gemiddeldeWoningwaarde")
        if woningvoorraad is None or woz is None or woningvoorraad < 0 or woz < 0:
            continue  # geen bruikbare CBS-cijfers (bv. water- of buitenlandvlak)
        try:
            geom = shape(feat["geometry"])
        except Exception:
            continue
        if not geom.is_valid:
            geom = geom.buffer(0)
        buurt_area = geom.area
        if buurt_area <= 0:
            continue

        woz_euro = woz * 1000  # CBS levert dit veld in duizenden euro's

        affected_area = 0.0
        weighted_effect_num = 0.0
        buurt_waardedaling = 0.0
        buurt_compensabel = 0.0
        max_abs_effect = 0.0
        for region, effect in partition:
            inter = region.intersection(geom)
            if inter.is_empty:
                continue
            area = inter.area
            if area <= 0:
                continue
            frac = area / buurt_area
            houses = woningvoorraad * frac
            waardedaling = houses * woz_euro * abs(effect)
            compensabel = houses * woz_euro * max(0.0, abs(effect) - NMR_THRESHOLD)
            affected_area += area
            weighted_effect_num += area * effect
            buurt_waardedaling += waardedaling
            buurt_compensabel += compensabel
            max_abs_effect = max(max_abs_effect, abs(effect))

        if affected_area <= 0:
            continue

        affected_houses = woningvoorraad * (affected_area / buurt_area)
        weighted_effect = weighted_effect_num / affected_area
        zelfrisico = buurt_waardedaling - buurt_compensabel

        # afstand van buurtcentroide tot dichtstbijzijnde turbine (indicatief)
        centroid = geom.centroid
        nearest_dist = min(
            math.hypot(centroid.x - t.x, centroid.y - t.y) for t in turbines
        )

        lon_c, lat_c = _to_wgs84(centroid.x, centroid.y)
        try:
            geom_wgs84 = shp_transform(_to_wgs84, geom)
            geojson_geom = mapping(geom_wgs84)
        except Exception:
            geojson_geom = None

        results.append(
            {
                "buurtcode": code,
                "buurtnaam": props.get("buurtnaam"),
                "gemeentenaam": props.get("gemeentenaam"),
                "woningvoorraad_totaal": woningvoorraad,
                "gemiddelde_woz": woz_euro,
                "afstand_centroide_m": round(nearest_dist),
                "aandeel_binnen_invloedsgebied": round(
                    affected_area / buurt_area, 4
                ),
                "geraakte_woningen": round(affected_houses, 1),
                "gewogen_waardedaling_pct": round(weighted_effect * 100, 2),
                "max_waardedaling_pct": round(max_abs_effect * 100, 2),
                "totale_waardedaling_euro": round(buurt_waardedaling),
                "waardedaling_per_woning_euro": round(
                    buurt_waardedaling / affected_houses
                )
                if affected_houses > 0
                else 0,
                "nadeelcompensatie_euro": round(buurt_compensabel),
                "eigen_risico_euro": round(zelfrisico),
                "centroid_lat": lat_c,
                "centroid_lon": lon_c,
                "geometry": geojson_geom,
            }
        )

        total["woningen"] += affected_houses
        total["waardedaling"] += buurt_waardedaling
        total["compensabel"] += buurt_compensabel
        total["zelfrisico"] += zelfrisico

    results.sort(key=lambda r: r["afstand_centroide_m"])

    gem_waardedaling_per_woning = (
        total["waardedaling"] / total["woningen"] if total["woningen"] > 0 else 0
    )
    gem_compensatie_per_woning = (
        total["compensabel"] / total["woningen"] if total["woningen"] > 0 else 0
    )

    turbine_out = []
    for t in turbines:
        cat = HEIGHT_CATEGORIES[t.category]
        turbine_out.append(
            {
                "label": t.label,
                "lat": t.lat,
                "lon": t.lon,
                "category": t.category,
                "category_label": cat["label"],
                "method": t.method,
                "radius_m": cat["radius_m"],
            }
        )

    return {
        "turbines": turbine_out,
        "warnings": warnings,
        "buurten": results,
        "totalen": {
            "aantal_buurten": len(results),
            "totaal_geraakte_woningen": round(total["woningen"], 1),
            "totale_waardedaling_euro": round(total["waardedaling"]),
            "gemiddelde_waardedaling_per_woning_euro": round(
                gem_waardedaling_per_woning
            ),
            "totaal_normaal_maatschappelijk_risico_euro": round(total["zelfrisico"]),
            "totaal_nadeelcompensatie_euro": round(total["compensabel"]),
            "gemiddelde_nadeelcompensatie_per_woning_euro": round(
                gem_compensatie_per_woning
            ),
        },
    }


# ---------------------------------------------------------------------------
# FastAPI app (Vercel Python runtime detects the ASGI `app` object)
# ---------------------------------------------------------------------------

app = FastAPI(title="Windturbine Waardedaling API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GeocodeIn(BaseModel):
    q: str


class TurbineIn(BaseModel):
    label: str = Field(max_length=120)
    lat: float
    lon: float
    category: str
    method: str = "vlak"


class CalcIn(BaseModel):
    turbines: list[TurbineIn]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def categories():
    out = {}
    for key, v in HEIGHT_CATEGORIES.items():
        out[key] = {
            "label": v["label"],
            "flat_effect_pct": round(v["flat_effect"] * 100, 2),
            "radius_m": v["radius_m"],
            "significant": v["significant"],
            "has_band_method": v["band_effects"] is not None,
        }
    return out


@app.get("/api/geocode")
def api_geocode(q: str):
    try:
        res = geocode_suggestions(q, rows=6)
        if not res:
            raise HTTPException(status_code=404, detail=f"Geen locatie gevonden voor '{q}'")
        return {"suggestions": res}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Geocoding mislukt: {e}")


@app.post("/api/calculate")
def api_calculate(payload: CalcIn):
    try:
        turbines = []
        for t in payload.turbines:
            if t.category not in HEIGHT_CATEGORIES:
                raise HTTPException(status_code=422, detail=f"Onbekende categorie: {t.category}")
            x, y = _to_rd_transformer.transform(t.lon, t.lat)
            turbines.append(
                Turbine(
                    x=x,
                    y=y,
                    lat=t.lat,
                    lon=t.lon,
                    label=t.label or "Turbine",
                    category=t.category,
                    method=t.method,
                )
            )
        result = calculate(turbines)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=422, detail=f"Berekening mislukt: {e}")


@app.post("/api/calculate-noise")
def api_calculate_noise(payload: CalcIn):
    try:
        turbines = []
        for t in payload.turbines:
            x, y = _to_rd_transformer.transform(t.lon, t.lat)
            turbines.append(
                Turbine(
                    x=x,
                    y=y,
                    lat=t.lat,
                    lon=t.lon,
                    label=t.label or "Turbine",
                    category=t.category if t.category in HEIGHT_CATEGORIES else "midden",
                    method=t.method,
                )
            )
        result = calculate_noise(turbines)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=422, detail=f"Geluidsberekening mislukt: {e}")


@app.get("/api/export/csv")
def export_csv(data: str):
    try:
        turbines_raw = json.loads(urllib.parse.unquote(data))
    except Exception:
        raise HTTPException(status_code=422, detail="Ongeldige exportgegevens")

    turbines = []
    for t in turbines_raw:
        x, y = _to_rd_transformer.transform(t["lon"], t["lat"])
        turbines.append(
            Turbine(x=x, y=y, lat=t["lat"], lon=t["lon"], label=t.get("label") or "Turbine",
                    category=t["category"], method=t.get("method", "vlak"))
        )
    try:
        result = calculate(turbines)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow([
        "Buurt", "Gemeente", "Afstand (m)", "Aandeel in invloedsgebied (%)",
        "Geraakte woningen", "Gem. WOZ-waarde (EUR)", "Gewogen waardedaling (%)",
        "Totale waardedaling (EUR)", "Waardedaling per woning (EUR)",
        "Nadeelcompensatie (EUR, > 4% NMR)", "Eigen risico (EUR, tot 4% NMR)",
    ])
    for b in result["buurten"]:
        writer.writerow([
            b["buurtnaam"], b["gemeentenaam"], b["afstand_centroide_m"],
            round(b["aandeel_binnen_invloedsgebied"] * 100, 1),
            b["geraakte_woningen"], b["gemiddelde_woz"], b["gewogen_waardedaling_pct"],
            b["totale_waardedaling_euro"], b["waardedaling_per_woning_euro"],
            b["nadeelcompensatie_euro"], b["eigen_risico_euro"],
        ])
    writer.writerow([])
    t = result["totalen"]
    writer.writerow(["TOTAAL", "", "", "", t["totaal_geraakte_woningen"], "", "",
                      t["totale_waardedaling_euro"], t["gemiddelde_waardedaling_per_woning_euro"],
                      t["totaal_nadeelcompensatie_euro"], t["totaal_normaal_maatschappelijk_risico_euro"]])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=waardedaling_windturbines.csv"},
    )


# ---------------------------------------------------------------------------
# Static frontend (index.html, app.js, style.css, base.css) — served from
# the same process/port so this is a single self-contained web service.
# Mounted last so it never shadows the /api/* routes defined above.
# ---------------------------------------------------------------------------

_STATIC_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/")
def root():
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
