"""ITU geographical designations, retrieved 2026-10-24."""

import re
from html.parser import HTMLParser

from .utils import fetch

URL = "https://www.itu.int/gladapp/GeographicalArea/List"

# Values are (official ITU designation, short display name, ISO 3166-1 alpha-2).
# Prefer the applicable ISO area/territory code; otherwise use the parent country.
# Multiple possibilities use a list: disputed claims or a historical area spanning countries.
# CG7 maps geographically to Cuba despite its USA-station designation.
# ISO assignments checked against pycountry iso3166-1.json on 2026-10-25.
AREAS = {
    "ABW": ("Aruba", "Aruba", "AW"),
    "AFG": ("Afghanistan", "Afghanistan", "AF"),
    "AFS": ("South Africa (Republic of)", "South Africa", "ZA"),
    "AGL": ("Angola (Republic of)", "Angola", "AO"),
    "AIA": ("Anguilla", "Anguilla", "AI"),
    "ALB": ("Albania (Republic of)", "Albania", "AL"),
    "ALG": ("Algeria (People's Democratic Republic of)", "Algeria", "DZ"),
    "ALS": ("Alaska (State of)", "Alaska", "US"),
    "AMS": (
        "Saint Paul and Amsterdam Islands",
        "Saint Paul and Amsterdam Islands",
        "TF",
    ),
    "AND": ("Andorra (Principality of)", "Andorra", "AD"),
    "AOE": ("Western Sahara", "Western Sahara", "EH"),
    "ARG": ("Argentine Republic", "Argentina", "AR"),
    "ARM": ("Armenia (Republic of)", "Armenia", "AM"),
    "ARS": ("Saudi Arabia (Kingdom of)", "Saudi Arabia", "SA"),
    "ASC": ("Ascension Island", "Ascension Island", "SH"),
    "ATA": ("Antarctic", "Antarctic", "AQ"),
    "ATG": ("Antigua and Barbuda", "Antigua and Barbuda", "AG"),
    "AUS": ("Australia", "Australia", "AU"),
    "AUT": ("Austria", "Austria", "AT"),
    "AZE": ("Azerbaijan (Republic of)", "Azerbaijan", "AZ"),
    "AZR": ("Azores", "Azores", "PT"),
    "B": ("Brazil (Federative Republic of)", "Brazil", "BR"),
    "BAH": ("Bahamas (Commonwealth of the)", "Bahamas", "BS"),
    "BDI": ("Burundi (Republic of)", "Burundi", "BI"),
    "BEL": ("Belgium", "Belgium", "BE"),
    "BEN": ("Benin (Republic of)", "Benin", "BJ"),
    "BER": ("Bermuda", "Bermuda", "BM"),
    "BES": (
        "Bonaire, Sint Eustatius and Saba",
        "Bonaire, Sint Eustatius and Saba",
        "BQ",
    ),
    "BFA": ("Burkina Faso", "Burkina Faso", "BF"),
    "BGD": ("Bangladesh (People's Republic of)", "Bangladesh", "BD"),
    "BHR": ("Bahrain (Kingdom of)", "Bahrain", "BH"),
    "BIH": ("Bosnia and Herzegovina", "Bosnia and Herzegovina", "BA"),
    "BIO": ("Chagos Islands (Indian Ocean)", "Chagos Islands (Indian Ocean)", "IO"),
    "BLM": ("Saint Barthélemy (French Department of)", "Saint Barthélemy", "BL"),
    "BLR": ("Belarus (Republic of)", "Belarus", "BY"),
    "BLZ": ("Belize", "Belize", "BZ"),
    "BOL": ("Bolivia (Plurinational State of)", "Bolivia", "BO"),
    "BOT": ("Botswana (Republic of)", "Botswana", "BW"),
    "BRB": ("Barbados", "Barbados", "BB"),
    "BRM": ("Myanmar (Union of)", "Myanmar", "MM"),
    "BRU": ("Brunei Darussalam", "Brunei", "BN"),
    "BTN": ("Bhutan (Kingdom of)", "Bhutan", "BT"),
    "BUL": ("Bulgaria (Republic of)", "Bulgaria", "BG"),
    "BVT": ("Bouvet Island", "Bouvet Island", "BV"),
    "CAF": ("Central African Republic", "Central African Republic", "CF"),
    "CAN": ("Canada", "Canada", "CA"),
    "CBG": ("Cambodia (Kingdom of)", "Cambodia", "KH"),
    "CG7": (
        'CUB(Guantanamo) (7), as defined in Appendix 26 to the Radio Regulations, Geneva, 1959; (7) means "USA stations".',
        "Guantanamo (USA stations)",
        "CU",
    ),
    "CHL": ("Chile", "Chile", "CL"),
    "CHN": ("China (People's Republic of)", "China", "CN"),
    "CHR": ("Christmas Island (Indian Ocean)", "Christmas Island (Indian Ocean)", "CX"),
    "CKH": ("Cook Islands", "Cook Islands", "CK"),
    "CLM": ("Colombia (Republic of)", "Colombia", "CO"),
    "CLN": ("Sri Lanka (Democratic Socialist Republic of)", "Sri Lanka", "LK"),
    "CME": ("Cameroon (Republic of)", "Cameroon", "CM"),
    "CNR": ("Canary Islands", "Canary Islands", "ES"),
    "COD": ("Democratic Republic of the Congo", "DR Congo", "CD"),
    "COG": ("Congo (Republic of the)", "Republic of the Congo", "CG"),
    "COM": ("Comoros (Union of the)", "Comoros", "KM"),
    "CPT": ("Clipperton Island", "Clipperton Island", "FR"),
    "CPV": ("Cabo Verde (Republic of)", "Cabo Verde", "CV"),
    "CRO": ("Crozet Archipelago", "Crozet Archipelago", "TF"),
    "CTI": ("Côte d'Ivoire (Republic of)", "Côte d'Ivoire", "CI"),
    "CTR": ("Costa Rica", "Costa Rica", "CR"),
    "CUB": ("Cuba", "Cuba", "CU"),
    "CUW": ("Curaçao", "Curaçao", "CW"),
    "CVA": ("Vatican City State", "Vatican City", "VA"),
    "CYM": ("Cayman Islands", "Cayman Islands", "KY"),
    "CYP": ("Cyprus (Republic of)", "Cyprus", "CY"),
    "CZE": ("Czech Republic", "Czechia", "CZ"),
    "D": ("Germany (Federal Republic of)", "Germany", "DE"),
    "DGA": ("Diego Garcia", "Diego Garcia", "IO"),
    "DJI": ("Djibouti (Republic of)", "Djibouti", "DJ"),
    "DMA": ("Dominica (Commonwealth of)", "Dominica", "DM"),
    "DNK": ("Denmark", "Denmark", "DK"),
    "DOM": ("Dominican Republic", "Dominican Republic", "DO"),
    "E": ("Spain", "Spain", "ES"),
    "EGY": ("Egypt (Arab Republic of)", "Egypt", "EG"),
    "EQA": ("Ecuador", "Ecuador", "EC"),
    "ERI": ("Eritrea", "Eritrea", "ER"),
    "EST": ("Estonia (Republic of)", "Estonia", "EE"),
    "ETH": ("Ethiopia (Federal Democratic Republic of)", "Ethiopia", "ET"),
    "F": ("France", "France", "FR"),
    "FIN": ("Finland", "Finland", "FI"),
    "FJI": ("Fiji (Republic of)", "Fiji", "FJ"),
    "FLK": ("Falkland Islands (Malvinas)", "Falkland Islands (Malvinas)", "FK"),
    "FRO": ("Faroe Islands", "Faroe Islands", "FO"),
    "FSM": ("Micronesia (Federated States of)", "Micronesia", "FM"),
    "G": (
        "United Kingdom of Great Britain and Northern Ireland",
        "United Kingdom",
        "GB",
    ),
    "GAB": ("Gabonese Republic", "Gabon", "GA"),
    "GCA": (
        "United Kingdom (Non-metropolitan) - Region 1",
        "United Kingdom (Non-metropolitan) - Region 1",
        "GB",
    ),
    "GCC": ("United Kingdom - Region 3", "United Kingdom - Region 3", "GB"),
    "GEO": ("Georgia", "Georgia", "GE"),
    "GHA": ("Ghana", "Ghana", "GH"),
    "GIB": ("Gibraltar", "Gibraltar", "GI"),
    "GLP": ("Guadeloupe (French Department of)", "Guadeloupe", "GP"),
    "GMB": ("Gambia (Republic of the)", "Gambia", "GM"),
    "GNB": ("Guinea-Bissau (Republic of)", "Guinea-Bissau", "GW"),
    "GNE": ("Equatorial Guinea (Republic of)", "Equatorial Guinea", "GQ"),
    "GRC": ("Greece", "Greece", "GR"),
    "GRD": ("Grenada", "Grenada", "GD"),
    "GRL": ("Greenland", "Greenland", "GL"),
    "GTM": ("Guatemala (Republic of)", "Guatemala", "GT"),
    "GUF": ("Guiana (French Department of)", "French Guiana", "GF"),
    "GUI": ("Guinea (Republic of)", "Guinea", "GN"),
    "GUM": ("Guam", "Guam", "GU"),
    "GUY": ("Guyana", "Guyana", "GY"),
    "HKG": ("Hong Kong (Special Administrative Region of China)", "Hong Kong", "HK"),
    "HMD": ("Heard and McDonald Islands", "Heard and McDonald Islands", "HM"),
    "HND": ("Honduras (Republic of)", "Honduras", "HN"),
    "HNG": ("Hungary", "Hungary", "HU"),
    "HOL": ("Netherlands (Kingdom of the)", "Netherlands", "NL"),
    "HRV": ("Croatia (Republic of)", "Croatia", "HR"),
    "HTI": ("Haiti (Republic of)", "Haiti", "HT"),
    "HWA": ("Hawaii (State of)", "Hawaii", "US"),
    "HWL": ("Howland Island", "Howland Island", "UM"),
    "I": ("Italy", "Italy", "IT"),
    "ICO": ("Cocos (Keeling) Islands", "Cocos (Keeling) Islands", "CC"),
    "IND": ("India (Republic of)", "India", "IN"),
    "INS": ("Indonesia (Republic of)", "Indonesia", "ID"),
    "IRL": ("Ireland", "Ireland", "IE"),
    "IRN": ("Iran (Islamic Republic of)", "Iran", "IR"),
    "IRQ": ("Iraq (Republic of)", "Iraq", "IQ"),
    "ISL": ("Iceland", "Iceland", "IS"),
    "ISR": ("Israel (State of)", "Israel", "IL"),
    "J": ("Japan", "Japan", "JP"),
    "JAR": ("Jarvis Island", "Jarvis Island", "UM"),
    "JMC": ("Jamaica", "Jamaica", "JM"),
    "JON": ("Johnston Island", "Johnston Island", "UM"),
    "JOR": ("Jordan (Hashemite Kingdom of)", "Jordan", "JO"),
    "KAZ": ("Kazakhstan (Republic of)", "Kazakhstan", "KZ"),
    "KEN": ("Kenya (Republic of)", "Kenya", "KE"),
    "KER": ("Kerguelen Islands", "Kerguelen Islands", "TF"),
    "KGZ": ("Kyrgyz Republic", "Kyrgyzstan", "KG"),
    "KIR": ("Kiribati (Republic of)", "Kiribati", "KI"),
    "KNA": ("Saint Kitts and Nevis (Federation of)", "Saint Kitts and Nevis", "KN"),
    "KOR": ("Korea (Republic of)", "South Korea", "KR"),
    "KRE": ("Democratic People's Republic of Korea", "North Korea", "KP"),
    "KWT": ("Kuwait (State of)", "Kuwait", "KW"),
    "LAO": ("Lao People's Democratic Republic", "Laos", "LA"),
    "LBN": ("Lebanon", "Lebanon", "LB"),
    "LBR": ("Liberia (Republic of)", "Liberia", "LR"),
    "LBY": ("Libya (State of)", "Libya", "LY"),
    "LCA": ("Saint Lucia", "Saint Lucia", "LC"),
    "LIE": ("Liechtenstein (Principality of)", "Liechtenstein", "LI"),
    "LSO": ("Lesotho (Kingdom of)", "Lesotho", "LS"),
    "LTU": ("Lithuania (Republic of)", "Lithuania", "LT"),
    "LUX": ("Luxembourg", "Luxembourg", "LU"),
    "LVA": ("Latvia (Republic of)", "Latvia", "LV"),
    "MAC": ("Macao (Special Administrative Region of China)", "Macao", "MO"),
    "MAF": ("Saint Martin (French Department of)", "Saint Martin", "MF"),
    "MAU": ("Mauritius (Republic of)", "Mauritius", "MU"),
    "MCO": ("Monaco (Principality of)", "Monaco", "MC"),
    "MDA": ("Moldova (Republic of)", "Moldova", "MD"),
    "MDG": ("Madagascar (Republic of)", "Madagascar", "MG"),
    "MDR": ("Madeira", "Madeira", "PT"),
    "MDW": ("Midway Islands", "Midway Islands", "UM"),
    "MEX": ("Mexico", "Mexico", "MX"),
    "MHL": ("Marshall Islands (Republic of the)", "Marshall Islands", "MH"),
    "MKD": ("North Macedonia (Republic of)", "North Macedonia", "MK"),
    "MLA": ("Malaysia", "Malaysia", "MY"),
    "MLD": ("Maldives (Republic of)", "Maldives", "MV"),
    "MLI": ("Mali (Republic of)", "Mali", "ML"),
    "MLT": ("Malta", "Malta", "MT"),
    "MNE": ("Montenegro", "Montenegro", "ME"),
    "MNG": ("Mongolia", "Mongolia", "MN"),
    "MOZ": ("Mozambique (Republic of)", "Mozambique", "MZ"),
    "MRA": (
        "Northern Mariana Islands (Commonwealth of the)",
        "Northern Mariana Islands",
        "MP",
    ),
    "MRC": ("Morocco (Kingdom of)", "Morocco", "MA"),
    "MRN": ("Marion Island", "Marion Island", "ZA"),
    "MRT": ("Martinique (French Department of)", "Martinique", "MQ"),
    "MSR": ("Montserrat", "Montserrat", "MS"),
    "MTN": ("Mauritania (Islamic Republic of)", "Mauritania", "MR"),
    "MWI": ("Malawi", "Malawi", "MW"),
    "MYT": ("Mayotte (Territorial Collectivity of)", "Mayotte", "YT"),
    "NCG": ("Nicaragua", "Nicaragua", "NI"),
    "NCL": ("New Caledonia", "New Caledonia", "NC"),
    "NFK": ("Norfolk Island", "Norfolk Island", "NF"),
    "NGR": ("Niger (Republic of the)", "Niger", "NE"),
    "NIG": ("Nigeria (Federal Republic of)", "Nigeria", "NG"),
    "NIU": ("Niue", "Niue", "NU"),
    "NMB": ("Namibia (Republic of)", "Namibia", "NA"),
    "NOR": ("Norway", "Norway", "NO"),
    "NPL": ("Nepal (Federal Democratic Republic of)", "Nepal", "NP"),
    "NRU": ("Republic of Naoero", "Nauru", "NR"),
    "NZL": ("New Zealand", "New Zealand", "NZ"),
    "OCE": ("French Polynesia", "French Polynesia", "PF"),
    "OMA": ("Oman (Sultanate of)", "Oman", "OM"),
    "PAK": ("Pakistan (Islamic Republic of)", "Pakistan", "PK"),
    "PAQ": ("Easter Island", "Easter Island", "CL"),
    "PHL": ("Philippines (Republic of the)", "Philippines", "PH"),
    "PHX": ("Phoenix Islands", "Phoenix Islands", "KI"),
    "PLM": ("Palmyra Island", "Palmyra Island", "UM"),
    "PLW": ("Palau (Republic of)", "Palau", "PW"),
    "PNG": ("Papua New Guinea", "Papua New Guinea", "PG"),
    "PNR": ("Panama (Republic of)", "Panama", "PA"),
    "POL": ("Poland (Republic of)", "Poland", "PL"),
    "POR": ("Portugal", "Portugal", "PT"),
    "PRG": ("Paraguay (Republic of)", "Paraguay", "PY"),
    "PRU": ("Peru", "Peru", "PE"),
    "PTC": ("Pitcairn Island", "Pitcairn Island", "PN"),
    "PTR": ("Puerto Rico", "Puerto Rico", "PR"),
    "QAT": ("Qatar (State of)", "Qatar", "QA"),
    "REU": ("Reunion (French Department of)", "Reunion", "RE"),
    "ROD": ("Rodrigues", "Rodrigues", "MU"),
    "ROU": ("Romania", "Romania", "RO"),
    "RRW": ("Rwanda (Republic of)", "Rwanda", "RW"),
    "RUS": ("Russian Federation", "Russia", "RU"),
    "S": ("Sweden", "Sweden", "SE"),
    "SDN": ("Sudan (Republic of the)", "Sudan", "SD"),
    "SEN": ("Senegal (Republic of)", "Senegal", "SN"),
    "SEY": ("Seychelles (Republic of)", "Seychelles", "SC"),
    "SHN": ("Saint Helena", "Saint Helena", "SH"),
    "SLM": ("Solomon Islands", "Solomon Islands", "SB"),
    "SLV": ("El Salvador (Republic of)", "El Salvador", "SV"),
    "SMA": ("American Samoa", "American Samoa", "AS"),
    "SMO": ("Samoa (Independent State of)", "Samoa", "WS"),
    "SMR": ("San Marino (Republic of)", "San Marino", "SM"),
    "SNG": ("Singapore (Republic of)", "Singapore", "SG"),
    "SOM": ("Somalia (Federal Republic of)", "Somalia", "SO"),
    "SPM": (
        "Saint Pierre and Miquelon (Territorial Collectivity of)",
        "Saint Pierre and Miquelon",
        "PM",
    ),
    "SRB": ("Serbia (Republic of)", "Serbia", "RS"),
    "SRL": ("Sierra Leone", "Sierra Leone", "SL"),
    "SSD": ("South Sudan (Republic of)", "South Sudan", "SS"),
    "STP": (
        "Sao Tome and Principe (Democratic Republic of)",
        "Sao Tome and Principe",
        "ST",
    ),
    "SUI": ("Switzerland (Confederation of)", "Switzerland", "CH"),
    "SUR": ("Suriname (Republic of)", "Suriname", "SR"),
    "SVK": ("Slovak Republic", "Slovakia", "SK"),
    "SVN": ("Slovenia (Republic of)", "Slovenia", "SI"),
    "SWN": ("Swan Islands", "Swan Islands", "HN"),
    "SWZ": ("Eswatini (Kingdom of)", "Eswatini", "SZ"),
    "SXM": ("Sint Maarten (Dutch part)", "Sint Maarten (Dutch part)", "SX"),
    "SYR": ("Syrian Arab Republic", "Syria", "SY"),
    "TCA": ("Turks and Caicos Islands", "Turks and Caicos Islands", "TC"),
    "TCD": ("Chad (Republic of)", "Chad", "TD"),
    "TGO": ("Togolese Republic", "Togo", "TG"),
    "THA": ("Thailand", "Thailand", "TH"),
    "TJK": ("Tajikistan (Republic of)", "Tajikistan", "TJ"),
    "TKL": ("Tokelau", "Tokelau", "TK"),
    "TKM": ("Turkmenistan", "Turkmenistan", "TM"),
    "TLS": ("Timor-Leste (Democratic Republic of)", "Timor-Leste", "TL"),
    "TON": ("Tonga (Kingdom of)", "Tonga", "TO"),
    "TRC": ("Tristan da Cunha", "Tristan da Cunha", "SH"),
    "TRD": ("Trinidad and Tobago", "Trinidad and Tobago", "TT"),
    "TUN": ("Tunisia", "Tunisia", "TN"),
    "TUR": ("Republic of Türkiye", "Türkiye", "TR"),
    "TUV": ("Tuvalu", "Tuvalu", "TV"),
    "TZA": ("Tanzania (United Republic of)", "Tanzania", "TZ"),
    "UAE": ("United Arab Emirates", "United Arab Emirates", "AE"),
    "UGA": ("Uganda (Republic of)", "Uganda", "UG"),
    "UKR": ("Ukraine", "Ukraine", "UA"),
    "URG": ("Uruguay (Eastern Republic of)", "Uruguay", "UY"),
    "USA": ("United States of America", "United States", "US"),
    "UZB": ("Uzbekistan (Republic of)", "Uzbekistan", "UZ"),
    "VCT": (
        "Saint Vincent and the Grenadines",
        "Saint Vincent and the Grenadines",
        "VC",
    ),
    "VEN": ("Venezuela (Bolivarian Republic of)", "Venezuela", "VE"),
    "VIR": ("United States Virgin Islands", "United States Virgin Islands", "VI"),
    "VRG": ("British Virgin Islands", "British Virgin Islands", "VG"),
    "VTN": ("Viet Nam (Socialist Republic of)", "Vietnam", "VN"),
    "VUT": ("Vanuatu (Republic of)", "Vanuatu", "VU"),
    "WAK": ("Wake Island", "Wake Island", "UM"),
    "WAL": ("Wallis and Futuna Islands", "Wallis and Futuna Islands", "WF"),
    "XBY": ("Abyei area", "Abyei area", ["SD", "SS"]),
    "XGZ": ("Gaza Strip", "Gaza Strip", "PS"),
    "XSD": (
        "Territory of the former Republic of the Sudan (prior to 14 July 2011)",
        "Former Sudan (before 14 July 2011)",
        ["SD", "SS"],
    ),
    "XSP": ("Spratly Islands", "Spratly Islands", ["CN", "TW", "VN", "PH", "MY"]),
    "XWB": ("West Bank", "West Bank", "PS"),
    "YEM": ("Yemen (Republic of)", "Yemen", "YE"),
    "ZMB": ("Zambia (Republic of)", "Zambia", "ZM"),
    "ZWE": ("Zimbabwe (Republic of)", "Zimbabwe", "ZW"),
}


def parse(data):
    """Read the published table, checking its headings and declared row count."""

    class Tables(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tables = []
            self.table = None
            self.row = None
            self.cell = None
            self.page_text = []

        def handle_starttag(self, tag, attrs):
            if tag == "table":
                self.table = []
            elif tag == "tr" and self.table is not None:
                self.row = []
            elif tag in {"td", "th"} and self.row is not None:
                self.cell = []

        def handle_data(self, value):
            self.page_text.append(value)
            if self.cell is not None:
                self.cell.append(value)

        def handle_endtag(self, tag):
            if tag in {"td", "th"} and self.cell is not None:
                self.row.append(" ".join("".join(self.cell).split()))
                self.cell = None
            elif tag == "tr" and self.row is not None:
                self.table.append(self.row)
                self.row = None
            elif tag == "table" and self.table is not None:
                self.tables.append(self.table)
                self.table = None

    parser = Tables()
    parser.feed(data.decode("utf-8-sig"))
    parser.close()
    tables = [t for t in parser.tables if t and t[0] == ["Symbol", "Designation"]]
    counts = re.findall(
        r"Number of symbols found\s*=\s*([0-9]+)", " ".join(parser.page_text)
    )
    if len(tables) != 1 or len(counts) != 1:
        raise ValueError("ITU: unrecognized table headings or row count")
    areas = {}
    for row in tables[0][1:]:
        if (
            len(row) != 2
            or not re.fullmatch(r"[A-Z][A-Z0-9]{0,2}", row[0])
            or not row[1]
        ):
            raise ValueError(f"ITU: invalid table row: {row}")
        code, name = row
        if code in areas:
            raise ValueError(f"ITU: duplicate code: {code}")
        areas[code] = name
    if not areas or len(areas) != int(counts[0]):
        raise ValueError("ITU: table does not match the published row count")
    return areas


def check():
    """Return upstream differences without modifying the bundled snapshot."""
    current = parse(fetch(URL))
    changes = []
    for code in sorted(AREAS.keys() | current.keys()):
        if code not in AREAS:
            changes.append(f"Added {code}: {current[code]}")
        elif code not in current:
            changes.append(f"Removed {code}: {AREAS[code][0]}")
        elif AREAS[code][0] != current[code]:
            changes.append(f"Changed {code}: {AREAS[code][0]} -> {current[code]}")
    return changes
