"""
Zielgerichtete Queries für muslimische Premiumpatienten.
Strategie: Geographisch + Sprachlich + Service-basiert
"""

QUERIES_GERMANY = [
    # Berlin – arabisch/türkisch sprechend
    "Zahnarzt arabisch sprechend Berlin Implantate",
    "Zahnarzt türkisch sprechend Berlin Premium",
    "Zahnarzt Neukölln Implantate Veneers",
    "Zahnarzt Wedding Berlin Premium Privatpatient",
    "Zahnarzt Berlin Mitte arabisch Implantologie",

    # NRW – größte muslimische Community Deutschlands
    "Zahnarzt türkisch Duisburg Implantate Premium",
    "Zahnarzt arabisch Köln Veneers Privatpraxis",
    "Zahnarzt Dortmund türkisch Implantologie",
    "Zahnarzt Essen arabisch Premium Klinik",
    "Zahnarzt Krefeld türkisch Implantate",

    # Hamburg
    "Zahnarzt arabisch Hamburg Implantate Premium",
    "Zahnarzt türkisch Hamburg Veneers",
    "Zahnarzt Altona Hamburg Premium Privatpatienten",

    # Frankfurt
    "Zahnarzt arabisch Frankfurt Implantate",
    "Zahnarzt türkisch Frankfurt Premium Klinik",

    # Stuttgart / München
    "Zahnarzt türkisch Stuttgart Implantate Veneers",
    "Zahnarzt arabisch München Premium Privatpraxis",
    "Zahnarzt München türkisch Implantologie",
]

QUERIES_EUROPE = [
    # UK – English queries
    "dentist arabic speaking London implants premium",
    "dentist muslim friendly London veneers",
    "dental clinic East London implants private",
    "dentist arabic London cosmetic dentistry",
    "premium dental clinic Whitechapel London",

    # Österreich
    "Zahnarzt arabisch Wien Implantate Premium",
    "Zahnarzt türkisch Wien Veneers Privatpraxis",
    "Zahnarzt Wien Favoriten Implantologie",

    # Schweiz
    "Zahnarzt arabisch Zürich Implantate",
    "Zahnarzt türkisch Basel Premium Klinik",
    "dentiste arabe Genève implants premium",

    # Niederlande
    "tandarts arabisch Amsterdam implantaten premium",
    "tandarts turks Rotterdam veneers",

    # Frankreich
    "dentiste arabe Paris implants premium",
    "dentiste Paris 16 implants esthétique",
]

QUERIES_GLOBAL = [
    # Dubai / UAE – English
    "dental clinic Dubai premium implants veneers",
    "cosmetic dentist Dubai All-on-4",
    "premium dental clinic Abu Dhabi implants",
    "dental tourism Germany arabic patients",

    # Dental Tourismus – Deutsche Praxen die arabische Patienten anwerben
    "Zahnarzt Dental Tourism arabische Patienten",
    "dental clinic Germany arabic patients implants",
    "Zahnklinik internationale Patienten arabisch",
    "dentist Germany english arabic implants veneers",

    # Istanbul – Premium türkische Praxen
    "diş kliniği istanbul implant veneer premium",
    "dental clinic istanbul english veneers all-on-4",
]

ALL_MUSLIM_TARGET_QUERIES = (
    QUERIES_GERMANY +
    QUERIES_EUROPE +
    QUERIES_GLOBAL
)
