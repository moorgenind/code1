# Maps product attributes to Google Drive file IDs
# Image URL: https://drive.google.com/thumbnail?id=FILE_ID&sz=w200

IMAGE_MAP = [
    # Each entry: (family_key, type_key, name_keywords, body_color_key) -> file_id
    # More specific entries first (higher priority)

    # ============ HAWAII - Downlight (all "spotlight/downlight round" products) ============
    {"family": "hawaii", "name": "compact spotlight", "trim": "trimless", "id": "1cLWBltKN6wbniOZMuAL9NFw5MR8VgLie"},
    {"family": "hawaii", "name": "compact spotlight", "trim": "trim",     "id": "1MnioHLmLBwzb4_mRkb7e4tNz2VDZPcKu"},
    {"family": "hawaii", "name": "spotlight", "trim": "trim",             "id": "1trGzIbGy_tttRdTiqVQ_fy1e-lQ7W0Zw"},
    {"family": "hawaii", "name": "spotlight", "trim": "trimless",         "id": "1XWt03RSxAQYw2Reg_9-ee0llhVyVsuWa"},
    {"family": "hawaii", "name": "55 round", "trim": "trim",              "id": "1LazA7DHBZbACaiSZ1cwLc2dQ4yNUj1RV"},
    {"family": "hawaii", "name": "55 round", "trim": "trimless",          "id": "18W6Gf8A_BnUgRbzfv-hdNQFOxWFLLo_m"},
    {"family": "hawaii", "name": "35 round", "trim": "trim", "color": "black", "id": "1JqmRoUJHKgnoKyQJdiS298G4M2vpoYgm"},
    {"family": "hawaii", "name": "35 round", "trim": "trim",              "id": "1d2ODWUxFh4jIAPdYGmrbj-yE_t41tVl1"},
    {"family": "hawaii", "name": "35 round", "trim": "trimless",          "id": "1NPNjh4TkNwa5QElqK3QgMUUhJKiLb1RG"},
    {"family": "hawaii", "name": "25 round", "trim": "trim", "color": "black", "id": "1y2AOFg86Q4jqwF3oHKNkKoepM7cQQ9Z0"},
    {"family": "hawaii", "name": "25 round", "trim": "trim",              "id": "19Ag0iNwILuKHaDULA3MQz7Qu41euE4I3"},
    {"family": "hawaii", "name": "25 round", "trim": "trimless",          "id": "1yH4GzFr2EPhlGi09YIR7QpuYooBA-fUZ"},
    {"family": "hawaii", "name": "wallwasher", "trim": "trimless",        "id": "1p0Xx4Kw9K2dBh7C7NCaLqYUzPJYLceTb"},
    {"family": "hawaii", "name": "wallwasher", "trim": "trim",            "id": "1p0Xx4Kw9K2dBh7C7NCaLqYUzPJYLceTb"},

    # ============ HAWAII - Motorized ============
    {"family": "hawaii", "name": "motorized downlight", "trim": "trimless", "id": "1QyYxCXOowJPnsDRXqJ6eEGGuSGHTxNrT"},
    {"family": "hawaii", "name": "motorized downlight", "trim": "trim",     "id": "1POdRsgT0MIkmbcaBEw2p7PMhzf1lKWqq"},
    {"family": "hawaii", "name": "motorized spotlight", "color": "black",   "id": "1Y1JP0hss-HJkPO2ks-kZVoGVci7jzzEM"},
    {"family": "hawaii", "name": "motorized spotlight",                     "id": "1nvk_7RvAKskonpX2NHa8UqCsBE42vvjj"},

    # ============ FLOWER OF PARIS ============
    {"family": "flower of paris", "name": "motorized spotlight", "color": "black", "id": "1Y1JP0hss-HJkPO2ks-kZVoGVci7jzzEM"},
    {"family": "flower of paris", "name": "motorized spotlight", "trim": "trim",   "id": "1nvk_7RvAKskonpX2NHa8UqCsBE42vvjj"},
    {"family": "flower of paris", "name": "motorized downlight", "trim": "trimless","id": "1QyYxCXOowJPnsDRXqJ6eEGGuSGHTxNrT"},
    {"family": "flower of paris", "name": "motorized downlight", "trim": "trim",   "id": "1POdRsgT0MIkmbcaBEw2p7PMhzf1lKWqq"},

    # ============ HEPBURN (MAGNETIC TRACK) ============
    {"family": "hepburn", "name": "double head spotlight",   "id": "10k_ZguA86pfxQQAnRfJo8SmyEfwcC4Om"},
    {"family": "hepburn", "name": "spotlight",               "id": "1oK-CN88RV7tet2n6sXPwLPacHChqGASo"},
    {"family": "hepburn", "name": "12 spots",                "id": "11K3UTGHyYG0MoB59KUkKTbY3r-p7X-8O"},
    {"family": "hepburn", "name": "strip 1200",              "id": "1YWdum3uBvqAv8NstwxN8dZM_TD_2wCuX"},
    {"family": "hepburn", "name": "strip 600",               "id": "1l7iMP6L2RrVc3BFffodaAobh_MKq5cjk"},
    {"family": "hepburn", "name": "2000 pre-installed",      "id": "10S0Q_Ga6dx8f0GvX_apeiQkUVIz5jsfp"},
    {"family": "hepburn", "name": "1000 pre-installed",      "id": "16gPFXhTzvgI_qRMWHOplhbaT0V7r61SGWe6U"},
    {"family": "hepburn", "name": "2000 surface",            "id": "1xO8s_K6TyZmlcldCcPyREbajfEbTLIrx"},
    {"family": "hepburn", "name": "1000 surface",            "id": "12c4JLSSR44Cn3GMjNa06_jdROZjvDbJj"},
    {"family": "hepburn", "name": "0-10v",                   "id": "1-uuWygs2fIWMcdODzZe-v09jveQWUq8z"},
    {"family": "hepburn", "name": "power supply",            "id": "1jxMdvmrirsmwu5WaIMiViEaGUrP2y0we"},
    {"family": "hepburn", "name": "vertical corner",         "id": "1v8zHjV9YlRvaPFwFVTUQbP_SCUZ-_mGN"},
    {"family": "hepburn", "name": "flat corner",             "id": "1jcXBir_sbR-Qlq7rzASYJa1F1Y31PnXq"},

    # ============ JAZZ ============
    {"family": "jazz", "name": "75", "name2": "white rose",  "id": "1NR35kWXoH--upp-txE6UCg9sz-GdeQ-0"},
    {"family": "jazz", "name": "75", "color": "black",       "id": "13lpwOzvwwWoQNiMxKJ3gnDGyxBVvcFkF"},
    {"family": "jazz", "name": "75",                         "id": "1t_SFmxy9v4rN7RHKkbMs0_Xx8IXA9NCg"},
    {"family": "jazz", "name": "35", "color": "black",       "id": "1nno3yhDPjzGqSGPHEI68c6hs863gECo4"},
    {"family": "jazz", "name": "35",                         "id": "10LAZw7DleTbhr4yZRSJNJRIwxcLPvhRY"},

    # ============ LOUIS (LASERBLADE) ============
    {"family": "louis", "name": "wallwasher", "trim": "trimless", "color": "black", "id": "15NE9bND5km5xeexCsoCUm_i3JStT_H5C"},
    {"family": "louis", "name": "wallwasher", "trim": "trimless",                   "id": "18N3tEcxRcMm1lzhMeqUrmWrTJprHszMF"},
    {"family": "louis", "name": "wallwasher", "trim": "trim",    "color": "black",  "id": "1mYQTauLkouYOZ7bE8LG16DyWOzh5nFUj"},
    {"family": "louis", "name": "wallwasher", "trim": "trim",                       "id": "1ohJNmD-FsJo5oLoJvgZrDFLM-93vAPVt"},
    {"family": "louis", "name": "12 spots", "trim": "trimless", "color": "black",   "id": "1zIDtgCgs0d0WGyba1fOnju5cCbcYdrLr"},
    {"family": "louis", "name": "6 spots",  "trim": "trimless", "color": "black",   "id": "1oqV6WPOAWXbm3CEEgpiK6YA84R-uM1kh"},
    {"family": "louis", "name": "3 spots",  "trim": "trimless", "color": "black",   "id": "1oRh6_m3Y6fqnNGmhvGEqW6zZ3rgkT8LS"},
    {"family": "louis", "name": "12 spots", "trim": "trimless",                     "id": "1QdOKMEcSBLQZCRYwOnZ9pJHsfLrfA9qi"},
    {"family": "louis", "name": "6 spots",  "trim": "trimless",                     "id": "1Epuv8mf0z4AhB22f3bRxoub0LQfp4yWF"},
    {"family": "louis", "name": "3 spots",  "trim": "trimless",                     "id": "1tMP_jrETLVtAIvQ9YUnwP1jtZ6Bzo1RI"},
    {"family": "louis", "name": "12 spots", "trim": "trim",     "color": "black",   "id": "1-gJ28MkxAFoYtRNKl5UtrnNkfMtR_eFa"},
    {"family": "louis", "name": "6 spots",  "trim": "trim",     "color": "black",   "id": "1xmnmbJKGdDLMCqZybwUhQO7ma1M-UAC8"},
    {"family": "louis", "name": "3 spots",  "trim": "trim",     "color": "black",   "id": "1rM72JUc9--hPVjFkR87wrNODmy-bBnJ9"},
    {"family": "louis", "name": "12 spots", "trim": "trim",                         "id": "1c_0zhIraW6BxpEKKaeeoGw66KMAZqHHD"},
    {"family": "louis", "name": "6 spots",  "trim": "trim",                         "id": "1A7_tgzUx4ZI8HEfkdmyo0Qakurp3n-TP"},
    {"family": "louis", "name": "3 spots",  "trim": "trim",                         "id": "1BsMNYd0vJ3K7g3i5Oer7UGx97S11oHkI"},

    # ============ BAGGIO ============
    {"family": "baggio", "name": "slim narrow", "color": "white",  "id": "16ed_b8c-wd4ZEKoGLnhdm7vUVhUq78H0"},
    {"family": "baggio", "name": "slim narrow",                    "id": "1vODXWh7AN-ap3T-xBa2v8AF2eZoy6BgF"},
    {"family": "baggio", "name": "square wide", "color": "white",  "id": "1WGMEoGr9N2K7SB6Y9IkFYZAtbxl7l4xO"},
    {"family": "baggio", "name": "square wide",                    "id": "1jYdcxenDp1gErRcGQ3f5VJ_wz3USal9K"},
    {"family": "baggio", "name": "square narrow", "color": "white","id": "1RW450IYc6ICQu5pIum6f_1PM1nv50gEj"},
    {"family": "baggio", "name": "square narrow",                  "id": "1aRnHQfQHjJ5RiPCdrhKhhQC5Onom5jpe"},
    {"family": "baggio", "name": "round narrow", "color": "white", "id": "12LNiOF4KuboI9zu9UgaO8q4ViaWZvEiQ"},
    {"family": "baggio", "name": "round narrow",                   "id": "1M8YV-WCffqm-vD6247FGYpU_zotufber"},
    {"family": "baggio", "name": "round ring light", "color": "white", "id": "1-qVd-4HKd-rgikzu6-CvpZklORcy0LMa"},
    {"family": "baggio", "name": "ring light", "color": "white",        "id": "1-qVd-4HKd-rgikzu6-CvpZklORcy0LMa"},
    {"family": "baggio", "name": "round ring light",               "id": "1Nkf_nSVYOMbOF_i7o9Cy55fYSvQRa7hj"},
    {"family": "baggio", "name": "ring light",                      "id": "1Nkf_nSVYOMbOF_i7o9Cy55fYSvQRa7hj"},

    # ============ PATTAYA ============
    {"family": "pattaya series iii", "name": "55 round", "id": "1BhorUvI571aaznGTSHk5SlynmIKaKoia"},
    {"family": "pattaya series iii", "name": "75 round", "id": "1AJHYovKPxUxjL878d6qiunpNSfgZQ-r_"},
    {"family": "pattaya",            "name": "75 round", "id": "1EGr6bmz7RaBPSWL__huLHb8DgUMfjNiw"},
]


def get_image_url(family: str, product_name: str, body_color: str = None, trim: str = None) -> str:
    """Find the best matching Drive thumbnail URL for a product."""
    if not family or not product_name:
        return None

    fam = family.lower()
    name = product_name.lower()
    color = (body_color or "").lower()
    tr = (trim or "").lower()

    best_id = None
    best_score = -1

    for entry in IMAGE_MAP:
        # Check family match
        entry_fam = entry["family"].lower()
        if entry_fam not in fam and fam not in entry_fam:
            continue

        score = 0
        # Check name keywords
        name_kw = entry.get("name", "")
        if name_kw and name_kw in name:
            score += 2
        elif name_kw:
            continue  # name keyword must match

        # Check name2 (secondary name keyword)
        name2_kw = entry.get("name2", "")
        if name2_kw:
            if name2_kw in name:
                score += 2
            else:
                continue

        # Check trim
        trim_kw = entry.get("trim", "")
        if trim_kw:
            if trim_kw == tr:
                score += 2
            else:
                continue

        # Check color (optional bonus)
        color_kw = entry.get("color", "")
        if color_kw:
            if color_kw in color:
                score += 1
            else:
                continue

        if score > best_score:
            best_score = score
            best_id = entry["id"]

    if best_id:
        return f"https://drive.google.com/thumbnail?id={best_id}&sz=w200"
    return None
