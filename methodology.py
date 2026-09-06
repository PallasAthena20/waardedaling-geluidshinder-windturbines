"""Methodologie-tekst voor het PDF-rapport (Module 5), 1:1 overgenomen uit de
accordion-secties van index.html (module methodology.py, auto-gegenereerd).
"""

METHODOLOGY_SECTIONS = [
    {
        "title": 'Hoe rekent het model?',
        "paragraphs": [
            'Voor elke ingevoerde turbine bepaalt het model een invloedscirkel: 1 km voor lage turbines (<50m) en 2 km voor midden- en hoge turbines, conform de afstanden waarbinnen Droës & Koster (2021) een significant effect meten. Voor hoge turbines kan gekozen worden voor het vlakke effectpercentage (Fig. 4b) of het per afstandsband afnemende percentage (Fig. 6).',
            'Binnen deze invloedscirkel(s) bepaalt het model welk deel van elke CBS-buurt overlapt met de invloedszone en rekent het aantal geraakte woningen naar rato van dat oppervlakteaandeel toe (dezelfde grid-logica als gebruikt door TNO in "De impact van windturbines op huizenprijzen", 2022). Als een buurt binnen bereik van meerdere turbines valt, telt het sterkste effect — er wordt niet dubbel geteld.',
            'De gemiddelde WOZ-waarde en het woningaantal per buurt komen rechtstreeks uit de actuele CBS Kerncijfers wijken en buurten, ontsloten via PDOK. Adressen en plaatsnamen worden herkend via de PDOK Locatieserver (BZK).',
        ],
    },
    {
        "title": 'Effectpercentages uit Droës & Koster (2021)',
        "paragraphs": [
            'Bron: M.I. Droës & H.R.A. Koster, "Wind turbines, solar farms, and house prices", Energy Policy 155 (2021), 112327. doi.org/10.1016/j.enpol.2021.112327 (https://doi.org/10.1016/j.enpol.2021.112327).',
            'Voor hoge turbines, afstandsbanden (Methode B, afgeleid uit Fig. 6):',
            'Let op: de afstandsband-percentages zijn afgelezen uit een figuur in het rapport en zijn daarom een benadering, geen exacte regressiecoëfficiënten. Voor lage en midden-turbines publiceert het rapport geen afstandsbanden — het model gebruikt daar bewust alleen het vlakke percentage om geen valse precisie te suggereren.',
        ],
    },
    {
        "title": 'Normaal maatschappelijk risico (4%-regel)',
        "paragraphs": [
            'Volgens vaste jurisprudentie van de Afdeling bestuursrechtspraak van de Raad van State komt bij planschade een waardedaling tot 2-4% doorgaans voor rekening van de eigenaar als "normaal maatschappelijk risico" (NMR). Dit model hanteert 4% als grenswaarde: van de berekende waardedaling per (deel van een) buurt komt het eerste percentage tot 4% voor eigen risico, en alleen het deel daarboven wordt als potentieel compensabele planschade getoond.',
            'Dit is een indicatieve, generieke toepassing van de 4%-vuistregel. De daadwerkelijke planschadevergoeding in een concrete casus wordt per geval vastgesteld door de bevoegde overheid, doorgaans met behulp van een onafhankelijk taxatierapport.',
        ],
    },
    {
        "title": 'Geluidsmodule — voortplanting en niveaus',
        "paragraphs": [
            'Het geluidsniveau op afstand R (meter) van de turbine wordt berekend met de vuistregel uit het RIVM-briefrapport 609333002 "Windturbines: invloed op de beleving en gezondheid van omwonenden" (bijlage 3, afgeleid van Pedersen et al., project WINDFARMperception, 2008):',
            'L_imm = L_w − 20·log₁₀(R) − 9 − 0,005·R dB',
            'Hierbij is L_w het bronvermogenniveau van de turbine (108 dB(A) A-gewogen, resp. 117 dB onweighted/lineair, bij 7 m/s windsnelheid — waarden zoals opgegeven voor dit model) en R de afstand in meter. De formule heeft een nauwkeurigheid van ca. ±3 dB en is bedoeld als representatieve schatting voor één turbine op open, vlak terrein — lokale factoren (bodemdemping, obstakels, meerdere turbines) kunnen afwijkingen geven. Bron: RIVM briefrapport 609333002 (https://www.platformstorm.nl/downloads/windturbines_ggd.pdf).',
            'De dB(A)-kolom gebruikt het A-gewogen bronvermogen (108 dB(A)); de dB-kolom (onweighted) gebruikt hetzelfde afstandsverval maar met het lineaire bronvermogen (117 dB) — een vereenvoudiging die dezelfde geometrische en atmosferische demping toepast op beide grootheden en dus indicatief is voor de onweighted kolom.',
        ],
    },
    {
        "title": 'Geluidsmodule — hinderpercentages en kosten',
        "paragraphs": [
            'De kolommen "Geluidshinder 9%", "30%" en "46%" tonen, per afstand, het aantal woningen binnen die straal vermenigvuldigd met het betreffende percentage: aantal woningen binnen afstand R × 9% (resp. × 30%, × 46%). Dit is een directe toepassing van drie scenario\'s over het aandeel woningen dat bij die afstand hinder ondervindt, onafhankelijk per drempel toegepast op het daar geldende woningaantal — geen drempeltoets op een dosis-effectcurve.',
            '9% — RIVM-basisscenario. Het RIVM meldt zelf dat bij de Nederlandse geluidsnorm (47 dB Lden) circa 8-9% van de omwonenden binnenshuis ernstige hinder ondervindt. Dit model gebruikt het exacte, niet-afgeronde RIVM-cijfer van 9% als basisscenario — op dezelfde manier waarop de 4%-drempel in Module 1 wordt toegepast als de jurisprudentieel erkende grens voor eigen risico bij waardedaling: een breed erkend, conservatief uitgangspunt, geen exact laboratoriumcijfer. Bron: RIVM, Factsheet gezondheidseffecten van windturbinegeluid (https://www.rivm.nl/sites/default/files/2026-02/Factsheet-gezondheidseffecten-van-windturbinegeluid.pdf).',
            '30% — tussenscenario. Een door de gebruiker opgegeven indicatieve waarde, tussen het RIVM-basisscenario en het kritische scenario in.',
            '46% — kritisch scenario. Ontleend aan een veldonderzoek waarin windturbinegeluid van 33-50 dB(A) door 46% van de respondenten die op 204-1.726 m van de dichtstbijzijnde turbine woonden als hinderlijk of zeer hinderlijk werd beoordeeld. Bron: Pawlaczyk-Łuszczyńska, M., Zaborowski, K., Dudarewicz, A., Zamojska-Daniszewska, M., Waszkowska, M. (2018), "Response to Noise Emitted by Wind Farms in People Living in Nearby Areas", International Journal of Environmental Research and Public Health 15(8), 1575, pmc.ncbi.nlm.nih.gov/articles/PMC6121431 (https://pmc.ncbi.nlm.nih.gov/articles/PMC6121431/).',
            'De kosten worden berekend per persoon, niet per woning: aantal getroffen woningen × gemiddeld aantal personen per huishouden (CBS "gemiddelde huishoudensgrootte", gewogen naar de buurten binnen de betreffende straal, met een landelijk gemiddelde van 2,1 als terugvalwaarde) × € 609,60 per persoon per jaar, oplopend tot × 25 jaar. Dit bedrag is een evidence-based kerncijfer voor de totale jaarlijkse zorgkosten (huisarts, POH-GGZ, medicatie, eventuele psychologische zorg inclusief eigen risico) bij aanhoudende hinder en slaapklachten die aan windturbinegeluid worden toegeschreven. Het is afgeleid van de dosis-responsrelatie tussen slaapstoornis en windturbinegeluid uit Godono et al. (2023), "Association between exposure to wind turbines and sleep disorders: a systematic review and meta-analysis", International Journal of Hygiene and Environmental Health (15 studies, n = 8.867), en is het ongewogen gemiddelde van de geschatte zorgkosten op de vijf beoordelingsafstanden (500 m tot 5 km). Gebruik deze kolommen als eerste-orde inschatting, niet als exacte schadeclaim.',
            'Windturbinegeluid bestaat uit hoorbaar geluid, laagfrequent geluid (LFG, ca. 20-100/125 Hz) en infrasoon geluid (< 20 Hz). LFG draagt verder en dringt makkelijker door in woningen, wat de 5 km-afstand in de tabel rechtvaardigt. Bron: Notitie geluidsnorm windturbines, provincie Gelderland (https://repository.officiele-overheidspublicaties.nl/externebijlagen/exb-2026-7801/1/bijlage/exb-2026-7801.PDF).',
        ],
    },
    {
        "title": 'DALY-module — disability weights, hindernormen en waardering',
        "paragraphs": [
            'Module 3 gebruikt exact dezelfde vijf beoordelingsafstanden en dezelfde drie hindernormen (9% RIVM-basisscenario, 30% tussenscenario, 46% kritisch scenario — zie de toelichting bij Module 2) als uitgangspunt. Het model berekent per afstand en per hindernorm hoeveel personen worden getroffen (aantal woningen × hindernorm × gemiddelde CBS-huishoudensgrootte) en vermenigvuldigt dat aantal met de som van twee disability weights: 0,010 voor ernstige slaapverstoring en 0,011 voor ernstige hinder — samen 0,021 DALY per getroffen persoon per jaar. Dit levert de kolom "DALY / jaar" op; vermenigvuldigd met 25 jaar en met de waarde per DALY ontstaat de gemonetariseerde kolom.',
            'De disability weights zijn de meest recente, in 2024 rechtstreeks bij de algemene bevolking (in vier EU-landen, waaronder Nederland) empirisch gemeten WHO-waarden. Bron: WHO Regional Office for Europe (2024), "Disability weights for noise-related health states in the WHO European Region" (https://www.who.int/europe/publications/i/item/WHO-EURO-2024-9196-48968-72969), gebaseerd op Charalampous e.a. (2024), "Estimating disability weights for environmental and non-environmental noise-related health states" (https://bmjpublichealth.bmj.com/content/2/1/e000470), BMJ Public Health. Deze 2024-waarden liggen 79% (slaapverstoring) resp. 45-63% (hinder) lager dan de klassieke WHO-waarden uit 2011 (0,07 / 0,02-0,03) en ook lager dan de RIVM/Van Kamp-waarden uit 2018 (RIVM-rapport 2018-0121: 0,0175 / 0,01). Dit model gebruikt bewust uitsluitend de 2024-cijfers, conform de expliciete keuze in de onderliggende positioning paper, en benoemt de neerwaartse trend hier transparant.',
            'De DALY-last van hart- en vaatziekten en vroegtijdig overlijden — die WHO/EEA eveneens aan omgevingsgeluid toeschrijven — wordt niet meegerekend, omdat daarvoor geen windturbine-specifiek dosis-effectmodel bestaat. De uitkomst van deze module is daarom een conservatieve ondergrens van de werkelijke gezondheidslast, niet een volledige schatting.',
            'Voor de monetaire waardering rekent het model met drie bedragen naast elkaar: € 50.000 per DALY (RIVM, 2025, basisscenario uit de MKBA-handreiking "Werken aan een gezonde leefomgeving"), minimaal € 70.000 per DALY (PBL, 2012, "Gezondheid in maatschappelijke kosten-batenanalyses van omgevingsbeleid", specifiek voor milieubeleid inclusief windturbines, op basis van Viscusi & Aldy 2003) en € 80.000 per DALY (Zorginstituut Nederland, 2024, referentiewaarde zorg, afgeleid via de QALY-DALY-spiegelrelatie uit de kosteneffectiviteitsdrempel van € 80.000/QALY — dit is ook de waarde waarmee de positioning paper zelf in haar conclusie afsluit). Alle drie zijn officiële Nederlandse overheidswaarden; geen ervan is een wettelijk voorgeschreven norm, en het RIVM noemt in dezelfde publicatie ook nog een alternatieve waarde van € 100.000/DALY die dit model niet gebruikt.',
            'Let op: het RIVM concludeert dat er een aangetoond, direct verband bestaat tussen windturbinegeluid en ervaren hinder, maar dat het bewijs voor een oorzakelijk verband tussen windturbinegeluid en objectief gemeten slaapverstoring niet eenduidig is. De DW-component voor slaapverstoring moet daarom als onderbouwd, maar niet onomstreden worden gezien. Bron: RIVM, Factsheet gezondheidseffecten van windturbinegeluid (https://www.rivm.nl/sites/default/files/2026-02/Factsheet-gezondheidseffecten-van-windturbinegeluid.pdf).',
        ],
    },
    {
        "title": 'Databronnen',
        "paragraphs": [
            'Geocoding: PDOK Locatieserver (https://www.pdok.nl/) (Kadaster / BZK), gratis en zonder API-key.',
            'Buurtgrenzen, woningvoorraad en gemiddelde WOZ-waarde: CBS Kerncijfers wijken en buurten (https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/wijk-en-buurtkaart-2024), ontsloten via de PDOK WFS-service.',
            'Achtergrond nationale impact: TNO, "De verwachte impact van windturbines op huizenprijzen in Nederland" (2022), publications.tno.nl/publication/34639293/2ZNonx/TNO-2022-P10374.pdf (https://publications.tno.nl/publication/34639293/2ZNonx/TNO-2022-P10374.pdf), gebruikt ter validatie van de gehanteerde bufferbenadering.',
            'Geluidsvoortplanting: RIVM, briefrapport 609333002 "Windturbines: invloed op de beleving en gezondheid van omwonenden" (https://www.platformstorm.nl/downloads/windturbines_ggd.pdf).',
            '9%-basisscenario (zorgkosten en hinder): RIVM, Factsheet gezondheidseffecten van windturbinegeluid (https://www.rivm.nl/sites/default/files/2026-02/Factsheet-gezondheidseffecten-van-windturbinegeluid.pdf).',
            '46%-hindercijfer: Pawlaczyk-Łuszczyńska, M. e.a., "Response to Noise Emitted by Wind Farms in People Living in Nearby Areas" (https://pmc.ncbi.nlm.nih.gov/articles/PMC6121431/), IJERPH 15(8) (2018).',
            'Zorgkosten-kerncijfer (€ 609,60/persoon/jaar): afgeleid van Godono A. e.a. (2023), "Association between exposure to wind turbines and sleep disorders: a systematic review and meta-analysis" (https://pubmed.ncbi.nlm.nih.gov/37844409/), International Journal of Hygiene and Environmental Health.',
            'Soorten geluid (hoorbaar / LFG / infrasoon): Notitie geluidsnorm windturbines (https://repository.officiele-overheidspublicaties.nl/externebijlagen/exb-2026-7801/1/bijlage/exb-2026-7801.PDF), provincie Gelderland.',
            'Gemiddelde huishoudensgrootte per buurt: CBS Kerncijfers wijken en buurten (https://www.cbs.nl/nl-nl/dossier/nederland-regionaal/geografische-data/wijk-en-buurtkaart-2024), ontsloten via de PDOK WFS-service.',
            'DALY disability weights (0,010 slaapverstoring / 0,011 ernstige hinder, 2024): WHO Regional Office for Europe, "Disability weights for noise-related health states in the WHO European Region" (https://www.who.int/europe/publications/i/item/WHO-EURO-2024-9196-48968-72969), gebaseerd op Charalampous e.a. (2024), BMJ Public Health (https://bmjpublichealth.bmj.com/content/2/1/e000470).',
            "Waarde per DALY — € 50.000 (basisscenario): RIVM (2025), Werken aan een gezonde leefomgeving met behulp van maatschappelijke kosten-batenanalyses (MKBA's) (https://www.rivm.nl/sites/default/files/2025-02/Werken%20aan%20een%20gezonde%20leefomgeving%20met%20behulp%20van%20maatschappelijke%20kosten-batenanalyses%20(MKBA's).pdf).",
            'Waarde per DALY — minimaal € 70.000 (milieubeleid): PBL (2012), Gezondheid in maatschappelijke kosten-batenanalyses van omgevingsbeleid (https://www.pbl.nl/sites/default/files/downloads/PBL_2012_Gezondheid_in_MKBAs_van_omgevingsbeleid_550051004.pdf).',
            'Waarde per DALY — € 80.000 (referentiewaarde zorg, via QALY-DALY-spiegelrelatie): Zorginstituut Nederland (2024), Beoordelingskader kosteneffectiviteit van zorg (https://www.zorginstituutnederland.nl/site/binaries/site-content/collections/documents/2024/11/26/beoordelingskader-kosteneffectiviteit-van-zorg/Beoordelingskader+kosteneffectiviteit+van+zorg.pdf).',
        ],
    },
    {
        "title": 'Module 4 — bouw-/investeringskosten per turbine',
        "paragraphs": [
            'Module 4 staat los van de locaties in Module 1-3 en werkt met vrije invoer: vermogen per turbine (MW), aantal turbines, hoofdcategorie en windsnelheidscategorie. Alle bedragen komen rechtstreeks uit het PBL-eindadvies "Advies basisbedragen SDE++ 2026" (hoofdstuk 7, Windenergie op land).',
            'Turbineprijs (€ 1.090/kW) is de prijs van de turbine zelf; de totale investeringskosten per hoofdcategorie (€ 1.540/kW regulier, € 1.550/kW hoogtebeperkt, € 1.770/kW waterkeringen) tellen daar de "meerkosten" bij op: netaansluiting, funderingen, bekabeling, wegen en voorbereidingskosten. Het verschil tussen beide bedragen wordt in de tabel getoond als "meerkosten".',
            'Voor de kosten per geproduceerde MWh gebruikt het model de vollasturen per jaar uit Tabel 7.4 van het PBL-advies, die per windsnelheidscategorie (I t/m V, van ≥ 8,0 m/s tot < 6,75 m/s) en per hoofdcategorie verschillen. De jaarproductie wordt daarna verlaagd met 13% windparkverlies (zog-, elektrische en overige verliezen, par. 7.2.2). Twee uitkomstmaten worden getoond: de investering gedeeld door de productie in het eerste jaar ("€/MWh jaar 1"), en de investering gedeeld door de totale productie over de economische levensduur van 20 jaar ("€/MWh 20 jaar", par. 6.6/7.1.4) — deze laatste is de meest representatieve langetermijnmaatstaf.',
            'Let op: dit is een vereenvoudigde investeringsmaatstaf. Ze houdt geen rekening met financieringskosten, disconteringsvoet (WACC), inflatie, O&M-kosten of de SDE++-subsidie zelf — voor die elementen verwijst het PBL-advies naar afzonderlijke tabellen (o.a. Tabel 6.3 WACC, en de vaste/variabele O&M-kosten per hoofdcategorie).',
            'Bron: PBL (2026), Advies basisbedragen SDE++ 2026 (https://www.pbl.nl/publicaties/advies-basisbedragen-sde-2026), hoofdstuk 7 (Windenergie op land) — Tabel 7.4 (vollasturen), Tabel 7.5 (investeringskosten regulier), Tabel 7.7 (hoogtebeperkt), Tabel 7.9 (waterkeringen).',
        ],
    },
]