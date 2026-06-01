"""
Company name aliases for supply chain entity resolution.

Maps canonical ticker → list of name variants that may appear in SEC filings.
Only covers companies relevant to the TW-US supply chain.
Entity resolver uses this to augment universe company names.
"""

ALIASES: dict[str, list[str]] = {
    # ── Taiwan ADRs (canonical = .TW ticker) ──────────────────────────────
    "2330.TW": [
        "TSMC", "TSM",
        "Taiwan Semiconductor", "Taiwan Semiconductor Manufacturing",
        "Taiwan Semiconductor Manufacturing Company",
        "Taiwan Semiconductor Manufacturing Company Limited",
        "Taiwan Semiconductor Manufacturing Co.",
        "台積電",
    ],
    "2303.TW": [
        "UMC", "United Microelectronics", "United Microelectronics Corporation",
        "United Microelectronics Corp.",
    ],
    "3711.TW": [
        "ASE", "ASE Technology", "ASE Technology Holdings",
        "Advanced Semiconductor Engineering",
        "日月光投控",
    ],
    "2409.TW": [
        "AUO", "AU Optronics", "AU Optronics Corporation",
        "友達光電",
    ],
    "2412.TW": [
        "CHT", "Chunghwa Telecom", "Chunghwa Telecom Co.",
        "中華電信",
    ],
    "3036.TW": [
        "Himax", "Himax Technologies", "HIMX",
        "奇景光電",
    ],
    "8150.TW": [
        "ChipMOS", "ChipMOS Technologies", "IMOS",
        "南茂科技",
    ],

    # ── Taiwan-only (appear as targets in US filings) ──────────────────────
    "2317.TW": [
        "Foxconn", "Hon Hai", "Hon Hai Precision",
        "Hon Hai Precision Industry", "Foxconn Technology Group",
        "鴻海", "鴻海精密",
    ],
    "2454.TW": [
        "MediaTek", "MediaTek Inc.",
        "聯發科", "聯發科技",
    ],
    "2308.TW": [
        "Delta Electronics", "Delta Electronics Inc.",
        "台達電", "台達電子",
    ],
    "2382.TW": [
        "Quanta", "Quanta Computer", "Quanta Computer Inc.",
        "廣達電腦",
    ],
    "2357.TW": [
        "Asustek", "Asus", "ASUSTeK Computer",
        "華碩電腦",
    ],
    "2353.TW": [
        "Acer", "Acer Inc.",
        "宏碁",
    ],
    "3231.TW": [
        "Wistron", "Wistron Corporation",
        "緯創資通",
    ],
    "2301.TW": [
        "Lite-On", "Lite-On Technology",
        "光寶科技",
    ],
    "2344.TW": [
        "Winbond", "Winbond Electronics",
        "華邦電子",
    ],
    "3008.TW": [
        "Largan", "Largan Precision",
        "大立光",
    ],
    "5347.TW": [
        "Vanguard", "Vanguard International Semiconductor",
        "世界先進",
    ],

    # ── US companies (common name variants in filings) ─────────────────────
    "AAPL": ["Apple", "Apple Inc.", "Apple Computer"],
    "NVDA": ["NVIDIA", "Nvidia", "NVIDIA Corporation"],
    "AMD":  ["Advanced Micro Devices", "AMD Inc."],
    "INTC": ["Intel", "Intel Corporation", "Intel Corp."],
    "QCOM": ["Qualcomm", "Qualcomm Incorporated", "Qualcomm Technologies"],
    "AVGO": ["Broadcom", "Broadcom Inc.", "Broadcom Corporation", "Avago Technologies"],
    "TXN":  ["Texas Instruments", "Texas Instruments Incorporated", "TI"],
    "MU":   ["Micron", "Micron Technology", "Micron Technology Inc."],
    "AMAT": ["Applied Materials", "Applied Materials Inc."],
    "LRCX": ["Lam Research", "Lam Research Corporation"],
    "KLAC": ["KLA", "KLA Corporation", "KLA-Tencor"],
    "ASML": ["ASML", "ASML Holding", "ASML Holding N.V."],
    "MRVL": ["Marvell", "Marvell Technology", "Marvell Technology Group"],
    "MPWR": ["Monolithic Power", "Monolithic Power Systems"],
    "SNPS": ["Synopsys", "Synopsys Inc."],
    "CDNS": ["Cadence", "Cadence Design Systems"],
    "ON":   ["ON Semiconductor", "onsemi", "ON Semiconductor Corporation"],
    "STM":  ["STMicroelectronics", "STMicro", "STMicroelectronics N.V."],
    "NXPI": ["NXP Semiconductors", "NXP", "NXP Semiconductors N.V."],
    "MCHP": ["Microchip Technology", "Microchip Technology Inc."],
    "ADI":  ["Analog Devices", "Analog Devices Inc.", "ADI"],
    "MSFT": ["Microsoft", "Microsoft Corporation"],
    "GOOG": ["Google", "Alphabet", "Alphabet Inc.", "Google LLC"],
    "GOOGL":["Google", "Alphabet", "Alphabet Inc."],
    "AMZN": ["Amazon", "Amazon.com", "Amazon Web Services", "AWS"],
    "META": ["Meta", "Meta Platforms", "Facebook", "Facebook Inc."],
    "TSLA": ["Tesla", "Tesla Inc.", "Tesla Motors"],
    "DELL": ["Dell", "Dell Technologies", "Dell Technologies Inc."],
    "HPQ":  ["HP", "Hewlett-Packard", "HP Inc."],
    "HPE":  ["Hewlett Packard Enterprise", "HPE"],
    "IBM":  ["IBM", "International Business Machines"],
    "CSCO": ["Cisco", "Cisco Systems", "Cisco Systems Inc."],
    "ORCL": ["Oracle", "Oracle Corporation"],
    "CRM":  ["Salesforce", "Salesforce Inc.", "salesforce.com"],
    "PANW": ["Palo Alto Networks", "Palo Alto Networks Inc."],
    "ANET": ["Arista Networks", "Arista Networks Inc."],
    "JNPR": ["Juniper Networks", "Juniper Networks Inc."],

    # ── Samsung (not in universe but appears in many filings) ─────────────
    "_SAMSUNG": [
        "Samsung", "Samsung Electronics", "Samsung Electronics Co.",
        "Samsung Electronics Co., Ltd.",
    ],
}

# Flat reverse lookup: lowercased alias → canonical ticker
ALIAS_REVERSE: dict[str, str] = {}
for ticker, names in ALIASES.items():
    for name in names:
        ALIAS_REVERSE[name.lower().strip()] = ticker
