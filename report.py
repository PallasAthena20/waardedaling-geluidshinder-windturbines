"""Module 5: genereert een PDF-rapport van de huidige berekening (Module 1-4)
inclusief kaartafbeeldingen en een worst/middle/best-case scenario-analyse.
Gebouwd met ReportLab (pure Python, geen systeemafhankelijkheden) zodat het
probleemloos draait op Render's standaard Python-runtime.
"""
import base64
import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    HRFlowable,
    KeepTogether,
)

from methodology import METHODOLOGY_SECTIONS

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
try:
    pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))
    FONT_REGULAR = "DejaVuSans"
    FONT_BOLD = "DejaVuSans-Bold"
except Exception:
    pass  # valt terug op Helvetica (core-font, geen Unicode-dekking voor Ł/ń/subscripts)

TEAL = colors.HexColor("#0d6f66")
TEAL_LIGHT = colors.HexColor("#e8f2f0")
TEXT_MUTED = colors.HexColor("#5b6763")
BORDER = colors.HexColor("#d7ded9")
PAGE_SIZE = landscape(A4)
MARGIN = 1.4 * cm


def _styles():
    ss = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "ReportTitle", parent=ss["Title"], fontSize=24, leading=28,
            textColor=colors.HexColor("#12211d"), spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=ss["Normal"], fontSize=12.5, leading=17,
            textColor=TEXT_MUTED, spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "H1", parent=ss["Heading1"], fontSize=15, leading=19,
            textColor=TEAL, spaceBefore=4, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2", parent=ss["Heading2"], fontSize=11.5, leading=15,
            textColor=colors.HexColor("#12211d"), spaceBefore=10, spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "H3", parent=ss["Heading3"], fontSize=9.5, leading=13,
            textColor=TEAL, spaceBefore=8, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body", parent=ss["Normal"], fontSize=8.7, leading=12.5,
            textColor=colors.HexColor("#22302b"), spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "Small", parent=ss["Normal"], fontSize=7.3, leading=10.2,
            textColor=TEXT_MUTED, spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "Cell", parent=ss["Normal"], fontSize=7.2, leading=9.2,
            textColor=colors.HexColor("#22302b"),
        ),
        "cellnum": ParagraphStyle(
            "CellNum", parent=ss["Normal"], fontSize=7.2, leading=9.2,
            textColor=colors.HexColor("#22302b"), alignment=2,
        ),
        "cellhead": ParagraphStyle(
            "CellHead", parent=ss["Normal"], fontSize=7.0, leading=9.0,
            textColor=colors.white, alignment=1,
        ),
        "cellhead_xs": ParagraphStyle(
            "CellHeadXs", parent=ss["Normal"], fontSize=5.9, leading=7.4,
            textColor=colors.white, alignment=1,
        ),
        "cellnum_xs": ParagraphStyle(
            "CellNumXs", parent=ss["Normal"], fontSize=5.9, leading=7.4,
            textColor=colors.HexColor("#22302b"), alignment=2,
        ),
        "kpi_label": ParagraphStyle(
            "KpiLabel", parent=ss["Normal"], fontSize=7.6, leading=10,
            textColor=TEXT_MUTED,
        ),
        "kpi_value": ParagraphStyle(
            "KpiValue", parent=ss["Normal"], fontSize=13.5, leading=16,
            textColor=colors.HexColor("#12211d"),
        ),
        "disclaimer": ParagraphStyle(
            "Disclaimer", parent=ss["Normal"], fontSize=8, leading=11.5,
            textColor=colors.HexColor("#7a4b1e"),
        ),
        "footer": ParagraphStyle(
            "Footer", parent=ss["Normal"], fontSize=6.8, leading=9,
            textColor=TEXT_MUTED,
        ),
    }
    for key, sty in styles.items():
        sty.fontName = FONT_REGULAR
    for key in ("title", "h1", "h2", "h3", "kpi_value"):
        styles[key].fontName = FONT_BOLD
    return styles


def fmt_euro(v):
    if v is None:
        return "\u2014"
    try:
        v = round(float(v))
    except (TypeError, ValueError):
        return "\u2014"
    s = f"{abs(v):,.0f}".replace(",", ".")
    sign = "-" if v < 0 else ""
    return f"{sign}\u20ac\u00a0{s}"


def fmt_num(v, decimals=1):
    if v is None:
        return "\u2014"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "\u2014"
    s = f"{v:,.{decimals}f}".replace(",", "TMP").replace(".", ",").replace("TMP", ".")
    return s


def fmt_pct(v, decimals=1):
    if v is None:
        return "\u2014"
    return f"{fmt_num(v, decimals)}%"


def fmt_euro_compact(v):
    """Compacte euro-notatie (k/mln) voor zeer dichte tabellen (Module 3-bijlage)."""
    if v is None:
        return "\u2014"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "\u2014"
    sign = "-" if v < 0 else ""
    av = abs(v)
    if av >= 1_000_000:
        s = f"{av / 1_000_000:.2f}".replace(".", ",")
        return f"{sign}\u20ac\u00a0{s}M"
    if av >= 1000:
        s = f"{av / 1000:.1f}".replace(".", ",")
        return f"{sign}\u20ac\u00a0{s}k"
    return f"{sign}\u20ac\u00a0{av:.0f}"


def fmt_dist(m):
    if m >= 1000:
        km = m / 1000
        return f"{fmt_num(km, 1)} km" if km % 1 else f"{int(km)} km"
    return f"{m} m"


def _decode_image(b64_str):
    if not b64_str:
        return None
    try:
        if "," in b64_str[:60]:
            b64_str = b64_str.split(",", 1)[1]
        raw = base64.b64decode(b64_str)
        return raw
    except Exception:
        return None


def _map_image_flowable(b64_str, max_w=17.5 * cm, max_h=8.2 * cm):
    raw = _decode_image(b64_str)
    if raw is None:
        return None
    reader = ImageReader(io.BytesIO(raw))
    iw, ih = reader.getSize()
    scale = min(max_w / iw, max_h / ih)
    return Image(io.BytesIO(raw), width=iw * scale, height=ih * scale)


def _p(text, style):
    return Paragraph(text if text else "", style)


def _section_rule():
    return HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceBefore=2, spaceAfter=10)


def _table_style(header_rows=1, group_spans=None, zebra=True, num_cols_start=1):
    cmds = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, header_rows - 1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if zebra:
        cmds.append(("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, TEAL_LIGHT]))
    if group_spans:
        for (c1, r1, c2, r2) in group_spans:
            cmds.append(("SPAN", (c1, r1), (c2, r2)))
    return TableStyle(cmds)


def _kpi_row(items):
    """items: list of (label, value) -> een rij KPI-kaartjes als 1-rij tabel."""
    st = _styles()
    cells = []
    for label, value in items:
        cell = Table(
            [[_p(label, st["kpi_label"])], [_p(value, st["kpi_value"])]],
            colWidths=[None],
        )
        cell.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7faf9")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        cells.append(cell)
    row = Table([cells], colWidths=[(PAGE_SIZE[0] - 2 * MARGIN) / len(cells)] * len(cells))
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return row


# ---------------------------------------------------------------------------
# Module-secties
# ---------------------------------------------------------------------------

def _build_cover(story, st, data):
    story.append(Spacer(1, 1.4 * cm))
    story.append(_p("Windturbine Impactrapport", st["title"]))
    story.append(_p(
        "Waardedaling woningen, geluidshinder &amp; zorgkosten, gezondheidslast (DALY's) "
        "en investeringskosten \u2014 automatisch gegenereerd overzicht.", st["subtitle"]
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(_section_rule())

    turbines = data.get("turbines") or []
    if turbines:
        story.append(_p("Ingevoerde windturbinelocatie(s)", st["h2"]))
        rows = [[_p("Naam", st["cellhead"]), _p("Co\u00f6rdinaten", st["cellhead"]),
                 _p("Categorie", st["cellhead"]), _p("Methode", st["cellhead"])]]
        for t in turbines:
            rows.append([
                _p(t.get("label", "Turbine"), st["cell"]),
                _p(f"{t.get('lat'):.5f}, {t.get('lon'):.5f}", st["cell"]),
                _p(t.get("category_label", t.get("category", "")), st["cell"]),
                _p(t.get("method", ""), st["cell"]),
            ])
        tbl = Table(rows, colWidths=[5 * cm, 5 * cm, 7.5 * cm, 3 * cm])
        tbl.setStyle(_table_style())
        story.append(tbl)
        story.append(Spacer(1, 0.5 * cm))

    now = data.get("generated_at") or datetime.now().strftime("%d-%m-%Y %H:%M")
    story.append(_p(f"Gegenereerd op {now} via het windturbine-rekenmodel.", st["small"]))
    story.append(Spacer(1, 0.6 * cm))

    disclaimer = Table(
        [[_p(
            "Dit rapport is een indicatief, evidence-based rekenmodel op basis van openbare bronnen en "
            "peer-reviewed onderzoek (zie bijlage \u2014 Methodologie &amp; bronnen). Het vormt geen juridisch "
            "advies en geen exacte schadeclaim. Raadpleeg bij een concrete planschade- of vergunningsprocedure "
            "een onafhankelijk deskundige.", st["disclaimer"]
        )]],
        colWidths=[PAGE_SIZE[0] - 2 * MARGIN],
    )
    disclaimer.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e0b06b")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf3e2")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(disclaimer)
    story.append(PageBreak())


def _build_module1(story, st, module1, map_img_b64):
    if not module1:
        return
    story.append(_p("Module 1 \u2014 Waardedaling woningen", st["h1"]))
    story.append(_p(
        "Berekend volgens het model van Dro\u00ebs &amp; Koster (2021), inclusief de 4%-NMR-splitsing "
        "(normaal maatschappelijk risico).", st["body"]
    ))

    img_flow = _map_image_flowable(map_img_b64)
    if img_flow:
        story.append(img_flow)
        story.append(Spacer(1, 0.3 * cm))

    t = module1.get("totalen", {})
    story.append(_kpi_row([
        ("Geraakte woningen", fmt_num(t.get("totaal_geraakte_woningen"), 1)),
        ("Totale waardedaling", fmt_euro(t.get("totale_waardedaling_euro"))),
        ("Gem. per woning", fmt_euro(t.get("gemiddelde_waardedaling_per_woning_euro"))),
        ("Nadeelcompensatie (>4%)", fmt_euro(t.get("totaal_nadeelcompensatie_euro"))),
    ]))
    story.append(Spacer(1, 0.35 * cm))

    buurten = module1.get("buurten", [])
    if buurten:
        header = [_p(h, st["cellhead"]) for h in [
            "Buurt", "Gemeente", "Afstand", "Ger. won.", "Gem. WOZ",
            "Waardedaling %", "Totaal", "Per woning", "Nadeelcomp."
        ]]
        rows = [header]
        for b in buurten[:40]:
            rows.append([
                _p(b.get("buurtnaam") or "\u2014", st["cell"]),
                _p(b.get("gemeentenaam") or "\u2014", st["cell"]),
                _p(fmt_dist(b.get("afstand_centroide_m", 0)), st["cellnum"]),
                _p(fmt_num(b.get("geraakte_woningen"), 1), st["cellnum"]),
                _p(fmt_euro(b.get("gemiddelde_woz")), st["cellnum"]),
                _p(fmt_pct(b.get("gewogen_waardedaling_pct"), 2), st["cellnum"]),
                _p(fmt_euro(b.get("totale_waardedaling_euro")), st["cellnum"]),
                _p(fmt_euro(b.get("waardedaling_per_woning_euro")), st["cellnum"]),
                _p(fmt_euro(b.get("nadeelcompensatie_euro")), st["cellnum"]),
            ])
        col_w = [3.4*cm, 2.7*cm, 1.8*cm, 1.7*cm, 2.2*cm, 2.3*cm, 2.3*cm, 2.2*cm, 2.3*cm]
        tbl = Table(rows, colWidths=col_w, repeatRows=1)
        tbl.setStyle(_table_style())
        story.append(tbl)
        if len(buurten) > 40:
            story.append(_p(
                f"Toont de eerste 40 van {len(buurten)} getroffen buurten, gesorteerd op afstand. "
                "De totalen hierboven omvatten alle buurten.", st["small"]
            ))
    story.append(PageBreak())


def _build_module23(story, st, module23, map_img_b64):
    if not module23:
        return
    story.append(_p("Module 2 \u2014 Geluidshinder &amp; Zorgkosten", st["h1"]))
    story.append(_p(
        "Geluidsniveau en geschatte zorgkosten op vijf vaste beoordelingsafstanden, bij drie "
        "hindernormen: 9% (RIVM-basisscenario), 30% (tussenscenario) en 46% (kritisch scenario).",
        st["body"]
    ))
    img_flow = _map_image_flowable(map_img_b64)
    if img_flow:
        story.append(img_flow)
        story.append(Spacer(1, 0.3 * cm))

    rows_data = module23.get("rijen", [])
    if rows_data:
        header1 = [
            _p("Afstand", st["cellhead"]), _p("Woningen", st["cellhead"]),
            _p("dB(A)", st["cellhead"]), _p("dB", st["cellhead"]),
            _p("Pers./hh", st["cellhead"]),
            _p("Geluidshinder 9%", st["cellhead"]), "", "",
            _p("Geluidshinder 30%", st["cellhead"]), "", "",
            _p("Geluidshinder 46%", st["cellhead"]), "", "",
        ]
        header2 = [
            "", "", "", "", "",
            _p("Won.", st["cellhead"]), _p("Kosten/jr", st["cellhead"]), _p("Kosten 25jr", st["cellhead"]),
            _p("Won.", st["cellhead"]), _p("Kosten/jr", st["cellhead"]), _p("Kosten 25jr", st["cellhead"]),
            _p("Won.", st["cellhead"]), _p("Kosten/jr", st["cellhead"]), _p("Kosten 25jr", st["cellhead"]),
        ]
        rows = [header1, header2]
        for r in rows_data:
            d9, d30, d46 = r["drempels"]
            row = [
                _p(fmt_dist(r["afstand_m"]), st["cellnum"]),
                _p(fmt_num(r["aantal_woningen"], 1), st["cellnum"]),
                _p(fmt_num(r["dba_7ms"], 1), st["cellnum"]),
                _p(fmt_num(r["db_onweighted"], 1), st["cellnum"]),
                _p(fmt_num(r["personen_per_huishouden"], 2), st["cellnum"]),
            ]
            for d in (d9, d30, d46):
                row += [
                    _p(fmt_num(d["aantal_woningen"], 1), st["cellnum"]),
                    _p(fmt_euro(d["kosten_per_jaar_euro"]), st["cellnum"]),
                    _p(fmt_euro(d["kosten_25jaar_euro"]), st["cellnum"]),
                ]
            rows.append(row)
        col_w = [1.6*cm, 1.7*cm, 1.4*cm, 1.3*cm, 1.5*cm] + [1.55*cm, 1.9*cm, 2.0*cm] * 3
        tbl = Table(rows, colWidths=col_w, repeatRows=2)
        style = _table_style(header_rows=2, group_spans=[(5, 0, 7, 0), (8, 0, 10, 0), (11, 0, 13, 0)])
        tbl.setStyle(style)
        story.append(tbl)
    story.append(PageBreak())

    story.append(_p("Module 3 \u2014 Gezondheidslast (DALY's)", st["h1"]))
    story.append(_p(
        "Dezelfde afstanden en hindernormen omgezet in Disability-Adjusted Life Years (WHO-maat voor "
        "gezondheidsverlies), gemonetariseerd volgens drie officiele Nederlandse overheidswaarden: "
        "RIVM (\u20ac 50.000/DALY), PBL (\u20ac 70.000/DALY) en Zorginstituut Nederland (\u20ac 80.000/DALY).",
        st["body"]
    ))
    if rows_data:
        header1 = [
            _p("Afstand", st["cellhead_xs"]),
            _p("DALY-last 9%", st["cellhead_xs"]), "", "", "", "", "", "",
            _p("DALY-last 30%", st["cellhead_xs"]), "", "", "", "", "", "",
            _p("DALY-last 46%", st["cellhead_xs"]), "", "", "", "", "", "",
        ]
        sub = ["Pers.", "DALY", "RIVM/j", "RIVM25j", "PBL/j", "PBL25j", "ZiN/j", "ZiN25j"]
        header2 = [""]
        for _ in range(3):
            header2 += [_p(s, st["cellhead_xs"]) for s in sub]
        rows = [header1, header2]
        for r in rows_data:
            row = [_p(fmt_dist(r["afstand_m"]), st["cellnum_xs"])]
            for d in r["drempels"]:
                daly = d["daly"]
                row += [
                    _p(fmt_num(d["aantal_personen"], 0), st["cellnum_xs"]),
                    _p(fmt_num(daly["daly_totaal_jaar"], 1), st["cellnum_xs"]),
                    _p(fmt_euro_compact(daly["waarde_rivm_jaar_euro"]), st["cellnum_xs"]),
                    _p(fmt_euro_compact(daly["waarde_rivm_25jaar_euro"]), st["cellnum_xs"]),
                    _p(fmt_euro_compact(daly["waarde_pbl_jaar_euro"]), st["cellnum_xs"]),
                    _p(fmt_euro_compact(daly["waarde_pbl_25jaar_euro"]), st["cellnum_xs"]),
                    _p(fmt_euro_compact(daly["waarde_zin_jaar_euro"]), st["cellnum_xs"]),
                    _p(fmt_euro_compact(daly["waarde_zin_25jaar_euro"]), st["cellnum_xs"]),
                ]
            rows.append(row)
        col_w = [1.3*cm] + [0.75*cm, 0.7*cm, 0.95*cm, 1.15*cm, 0.95*cm, 1.15*cm, 0.95*cm, 1.15*cm] * 3
        tbl = Table(rows, colWidths=col_w, repeatRows=2)
        style = _table_style(
            header_rows=2,
            group_spans=[(1, 0, 8, 0), (9, 0, 16, 0), (17, 0, 24, 0)],
        )
        style.add("LEFTPADDING", (0, 0), (-1, -1), 2)
        style.add("RIGHTPADDING", (0, 0), (-1, -1), 2)
        style.add("TOPPADDING", (0, 0), (-1, -1), 2)
        style.add("BOTTOMPADDING", (0, 0), (-1, -1), 2)
        tbl.setStyle(style)
        story.append(tbl)
        story.append(_p(
            "j = per jaar; 25j = cumulatief over 25 jaar; k = duizend euro, M = miljoen euro. "
            "RIVM = \u20ac 50.000/DALY, PBL = \u20ac 70.000/DALY, "
            "ZiN = Zorginstituut Nederland = \u20ac 80.000/DALY.", st["small"]
        ))
    story.append(PageBreak())


def _build_module4(story, st, module4):
    if not module4:
        return
    story.append(_p("Module 4 \u2014 Bouw-/investeringskosten per turbine", st["h1"]))
    story.append(_p(
        "Berekend volgens het PBL-eindadvies \u201cAdvies basisbedragen SDE++ 2026\u201d (turbineprijs "
        "\u20ac 1.090/kW; totale investeringskosten \u20ac 1.540-1.770/kW afhankelijk van categorie).",
        st["body"]
    ))
    t = module4.get("totalen", {})
    story.append(_kpi_row([
        ("Totaal vermogen", f"{fmt_num(t.get('vermogen_totaal_mw'), 2)} MW"),
        ("Aantal turbines", str(t.get("aantal_turbines_totaal", "\u2014"))),
        ("Totale investering", fmt_euro(t.get("investering_totaal_euro"))),
        ("Gem. \u20ac/MWh (20 jr)", fmt_euro(t.get("gem_kosten_per_mwh_levensduur_euro"))),
    ]))
    story.append(Spacer(1, 0.35 * cm))

    rijen = module4.get("rijen", [])
    if rijen:
        header = [_p(h, st["cellhead"]) for h in [
            "Groep", "Categorie", "Windcat.", "Vermogen/turb.", "Aantal",
            "Totaal verm.", "Investering totaal", "\u20ac/MWh jr1", "\u20ac/MWh 20jr"
        ]]
        rows = [header]
        for g in rijen:
            rows.append([
                _p(g.get("label", ""), st["cell"]),
                _p(g.get("hoofdcategorie_label", ""), st["cell"]),
                _p(g.get("windcategorie", ""), st["cellnum"]),
                _p(f"{fmt_num(g.get('vermogen_per_turbine_mw'), 2)} MW", st["cellnum"]),
                _p(str(g.get("aantal_turbines", "")), st["cellnum"]),
                _p(f"{fmt_num(g.get('vermogen_totaal_mw'), 2)} MW", st["cellnum"]),
                _p(fmt_euro(g.get("investering_totaal_euro")), st["cellnum"]),
                _p(fmt_euro(g.get("kosten_per_mwh_jaar1_euro")), st["cellnum"]),
                _p(fmt_euro(g.get("kosten_per_mwh_levensduur_euro")), st["cellnum"]),
            ])
        col_w = [3.2*cm, 4.5*cm, 1.8*cm, 2.3*cm, 1.8*cm, 2.3*cm, 3.0*cm, 2.1*cm, 2.1*cm]
        tbl = Table(rows, colWidths=col_w, repeatRows=1)
        tbl.setStyle(_table_style())
        story.append(tbl)
    story.append(PageBreak())


def _extract_scenario_row(module23, distance_m=5000):
    rows_data = (module23 or {}).get("rijen", [])
    for r in rows_data:
        if r.get("afstand_m") == distance_m:
            return r
    return rows_data[-1] if rows_data else None


def _build_scenario(story, st, module1, module23, module4):
    story.append(_p("Module 5 \u2014 Scenario-analyse: worst / middle / best case", st["h1"]))
    story.append(_p(
        "Combineert de drie modules tot \u00e9\u00e9n totaalbeeld over 25 jaar, in drie scenario\u2019s op basis "
        "van de bestaande hindernormen uit Module 2/3. Best case = 9% hindernorm (RIVM-basisscenario) "
        "gewaardeerd tegen \u20ac 50.000/DALY (RIVM); middle case = 30% (tussenscenario) tegen \u20ac 70.000/DALY "
        "(PBL); worst case = 46% (kritisch scenario, Pawlaczyk-\u0141uszczy\u0144ska e.a. 2018) tegen "
        "\u20ac 80.000/DALY (Zorginstituut Nederland). De geluidshinder- en DALY-cijfers zijn gebaseerd op "
        "het volledige invloedsgebied van 5 km. Module 1 (waardedaling) kent geen percentage-bandbreedte "
        "en is in alle drie de scenario\u2019s gelijk. Module 4 (investeringskosten) is een apart, "
        "vergelijkbaar referentiecijfer \u2014 de kosten van de turbines zelf, niet van de externe effecten "
        "\u2014 en telt daarom niet mee in het \u201ctotaal maatschappelijke kosten\u201d-bedrag.", st["body"]
    ))

    row5km = _extract_scenario_row(module23, 5000)
    m1_total = (module1 or {}).get("totalen", {}).get("totale_waardedaling_euro")
    m4_total = (module4 or {}).get("totalen", {}).get("investering_totaal_euro")

    scenarios = []
    if row5km:
        d9, d30, d46 = row5km["drempels"]
        scenarios = [
            ("Best case", "9% \u00b7 RIVM \u20ac 50k/DALY", d9["kosten_25jaar_euro"], d9["daly"]["waarde_rivm_25jaar_euro"]),
            ("Middle case", "30% \u00b7 PBL \u20ac 70k/DALY", d30["kosten_25jaar_euro"], d30["daly"]["waarde_pbl_25jaar_euro"]),
            ("Worst case", "46% \u00b7 ZiN \u20ac 80k/DALY", d46["kosten_25jaar_euro"], d46["daly"]["waarde_zin_25jaar_euro"]),
        ]

    if scenarios:
        header = [_p(h, st["cellhead"]) for h in [
            "Scenario", "Uitgangspunt", "Waardedaling (Mod. 1)",
            "Zorgkosten 25 jr (Mod. 2)", "DALY-waarde 25 jr (Mod. 3)",
            "Totaal maatschappelijke kosten"
        ]]
        rows = [header]
        for name, basis, cost2, cost3 in scenarios:
            total = (m1_total or 0) + cost2 + cost3
            rows.append([
                _p(name, st["cell"]),
                _p(basis, st["cell"]),
                _p(fmt_euro(m1_total), st["cellnum"]),
                _p(fmt_euro(cost2), st["cellnum"]),
                _p(fmt_euro(cost3), st["cellnum"]),
                _p(fmt_euro(total), st["cellnum"]),
            ])
        col_w = [2.6*cm, 4.3*cm, 3.6*cm, 3.8*cm, 3.8*cm, 4.0*cm]
        tbl = Table(rows, colWidths=col_w, repeatRows=1)
        style = _table_style()
        style.add("FONTNAME", (0, 1), (0, -1), FONT_BOLD)
        style.add("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eaf5ee"))
        style.add("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#fbeceb"))
        tbl.setStyle(style)
        story.append(tbl)
        story.append(Spacer(1, 0.35 * cm))

        if m4_total is not None:
            story.append(_p(
                f"Ter referentie \u2014 totale investeringskosten van de turbine(s) zelf (Module 4, "
                f"constant in alle scenario\u2019s): {fmt_euro(m4_total)}.", st["body"]
            ))
    else:
        story.append(_p(
            "Geen Module 2/3-resultaten beschikbaar \u2014 bereken eerst een locatie om het scenario te vullen.",
            st["small"]
        ))
    story.append(PageBreak())


def _build_methodology_appendix(story, st):
    story.append(_p("Bijlage \u2014 Methodologie &amp; bronnen", st["h1"]))
    story.append(_p(
        "Volledige onderbouwing van alle vier de modules, overgenomen uit de verantwoording op de "
        "website.", st["body"]
    ))
    story.append(_section_rule())
    for section in METHODOLOGY_SECTIONS:
        story.append(_p(section["title"], st["h3"]))
        for para in section["paragraphs"]:
            story.append(_p(para, st["small"]))
        story.append(Spacer(1, 0.15 * cm))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_p(
        "Geen juridisch advies. Raadpleeg bij een concrete planschade- of vergunningsprocedure een "
        "onafhankelijk deskundige.", st["disclaimer"]
    ))


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_REGULAR, 6.8)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(MARGIN, 0.7 * cm, "Windturbine Impactrapport \u2014 automatisch gegenereerd, geen juridisch advies")
    canvas.drawRightString(PAGE_SIZE[0] - MARGIN, 0.7 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def build_report_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=PAGE_SIZE,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=1.3 * cm,
        title="Windturbine Impactrapport",
    )
    st = _styles()
    story = []

    _build_cover(story, st, data)
    _build_module1(story, st, data.get("module1"), data.get("map1_image"))
    _build_module23(story, st, data.get("module23"), data.get("map2_image"))
    _build_module4(story, st, data.get("module4"))
    _build_scenario(story, st, data.get("module1"), data.get("module23"), data.get("module4"))
    _build_methodology_appendix(story, st)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
