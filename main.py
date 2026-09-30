def apply_region_filter(
    results,
    region
):

    region = (
        region or ""
    ).strip()

    if not region:
        return results

    allowed = REGIONS.get(
        region
    )

    if not allowed:
        return results

    # --------------------------------------------------------
    # Nomes de países -> códigos ISO3
    # --------------------------------------------------------

    country_names = {
        "Algeria": "DZA",
        "Angola": "AGO",
        "Benin": "BEN",
        "Botswana": "BWA",
        "Burkina Faso": "BFA",
        "Burundi": "BDI",
        "Cameroon": "CMR",
        "Cape Verde": "CPV",
        "Central African Republic": "CAF",
        "Chad": "TCD",
        "Comoros": "COM",
        "Congo": "COG",
        "Democratic Republic of the Congo": "COD",
        "Djibouti": "DJI",
        "Egypt": "EGY",
        "Equatorial Guinea": "GNQ",
        "Eritrea": "ERI",
        "Eswatini": "SWZ",
        "Ethiopia": "ETH",
        "Gabon": "GAB",
        "Gambia": "GMB",
        "Ghana": "GHA",
        "Guinea": "GIN",
        "Guinea-Bissau": "GNB",
        "Ivory Coast": "CIV",
        "Côte d'Ivoire": "CIV",
        "Kenya": "KEN",
        "Lesotho": "LSO",
        "Liberia": "LBR",
        "Libya": "LBY",
        "Madagascar": "MDG",
        "Malawi": "MWI",
        "Mali": "MLI",
        "Mauritania": "MRT",
        "Mauritius": "MUS",
        "Morocco": "MAR",
        "Mozambique": "MOZ",
        "Namibia": "NAM",
        "Niger": "NER",
        "Nigeria": "NGA",
        "Rwanda": "RWA",
        "Senegal": "SEN",
        "Seychelles": "SYC",
        "Sierra Leone": "SLE",
        "Somalia": "SOM",
        "South Africa": "ZAF",
        "South Sudan": "SSD",
        "Sudan": "SDN",
        "Tanzania": "TZA",
        "United Republic of Tanzania": "TZA",
        "Togo": "TGO",
        "Tunisia": "TUN",
        "Uganda": "UGA",
        "Zambia": "ZMB",
        "Zimbabwe": "ZWE",
    }

    # --------------------------------------------------------
    # Códigos ISO2 -> ISO3
    # --------------------------------------------------------

    iso2_to_iso3 = {
        "DZ": "DZA",
        "AO": "AGO",
        "BJ": "BEN",
        "BW": "BWA",
        "BF": "BFA",
        "BI": "BDI",
        "CM": "CMR",
        "CV": "CPV",
        "CF": "CAF",
        "TD": "TCD",
        "KM": "COM",
        "CG": "COG",
        "CD": "COD",
        "CI": "CIV",
        "DJ": "DJI",
        "EG": "EGY",
        "GQ": "GNQ",
        "ER": "ERI",
        "SZ": "SWZ",
        "ET": "ETH",
        "GA": "GAB",
        "GM": "GMB",
        "GH": "GHA",
        "GN": "GIN",
        "GW": "GNB",
        "KE": "KEN",
        "LS": "LSO",
        "LR": "LBR",
        "LY": "LBY",
        "MG": "MDG",
        "MW": "MWI",
        "ML": "MLI",
        "MR": "MRT",
        "MU": "MUS",
        "MA": "MAR",
        "MZ": "MOZ",
        "NA": "NAM",
        "NE": "NER",
        "NG": "NGA",
        "RW": "RWA",
        "SN": "SEN",
        "SC": "SYC",
        "SL": "SLE",
        "SO": "SOM",
        "ZA": "ZAF",
        "SS": "SSD",
        "SD": "SDN",
        "TZ": "TZA",
        "TG": "TGO",
        "TN": "TUN",
        "UG": "UGA",
        "ZM": "ZMB",
        "ZW": "ZWE",
    }

    filtered = []

    for item in results:

        raw_country = (
            item.get("country")
            or ""
        ).strip()

        if not raw_country:
            continue

        country_upper = raw_country.upper()

        # Já é ISO3
        country_code = country_upper

        # ISO2
        if country_upper in iso2_to_iso3:
            country_code = iso2_to_iso3[
                country_upper
            ]

        # Nome do país
        if raw_country in country_names:
            country_code = country_names[
                raw_country
            ]

        # Comparação final
        if country_code in allowed:
            filtered.append(item)

    return filtered
