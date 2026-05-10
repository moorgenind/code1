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


# ============ DECORATIVE IMAGE MAP ============
DEC_IMAGE_MAP = {
    # Table Lamps
    "melting blossom": "1K4NuNE974b2Q5hK6tWFeVOfPoJ4cGcWK",
    "yulong": "1glo8Jenly7oBNAIdxq9LCSkSQd76-Oel",
    "angling": "1IM7EQe1XBLAL9wqcqjvPYB7hL_glgAIS",
    "extragalactic": "1DAWfws3CBwikgFlY4lFINftu-OxFqcQM",
    "matcha": "195fvAgwMhhT8VEnU6msi3s9mfl7e69my",
    "clove": "1eU8IJ2YUkddZsHB-ndN8ezzTee_D9fru",
    "guzzle": "1IIjZepS4PN4OiB2O_3KtKVz9AbWCwD5c",
    "fair lady.w": "17Mcnrl3bKSFoPj8xMpFioO9qqFLyke1m",
    "brownie": "114SPLrQIzKFWmtno4fdu9vbtat4djUnl",
    "lychee": "10qvWYxIe6TUO7rSeMIQewcqvKmj0oBIF",
    "bowknot": "1OTOSzzlpiWKa_Dzxm8W9nlZtwBt45-cM",
    "amber": "1MRQCEQ-dWgWbxWlAGxx318PCIMyMb9gv",
    "fair lady.k": "1pMzZjcNcyw3-VylTvliI9Qd4H6CndGWs",
    "s series": "1ggdohWZN9aevp3YDQxZK74JHnEh1YSTq",
    "zhizai·1": "1_hTNjw_MR7ULx6nTKBf6DKaRlCWqnpMu",
    "nacre": "1YKYhAJbl4y5IMfqt2TMRCSC4v4rJeBGH",
    "zhizai·9": "1c-nkj3fhGWk-_U8mKy_BYh1V30heA0Vr",
    "zhizai·6": "1VPXF2tEy965cd3n-0wBmIHU5rDtUBlEh",
    "pearl": "12HCWnBkbxH7Ow72MGXkPpfx2DSFDMgyb",
    "royal series - square": "1WQj9HqOWPqRC-cbSI2nsxlnvbo5ReGR0",
    "royal palace": "1WQj9HqOWPqRC-cbSI2nsxlnvbo5ReGR0",
    "ruth france": "1CGruXhJ7FFGoB99zP-t865jWFSRyGlaG",
    "good night": "1WHH5DkLLgIPzqSNjDRLQJigcE3aDvEDd",
    "magic": "15aWQqHh9Mg7OGrGQApq5007n6EyyXw-V",
    "hennessy": "19sCJZVSgRDgoEZMW4ztW4ireI5SU3FrB",
    "oud royal": "1t1C0Iw5xsLRCEQFeN2RmmAidjcNsJq4I",
    "zhizai·7": "1yZGRnqZ4W5AqyXqUK3UpkKloqOvYLnOW",
    "perfumer": "1--xqxprkj-T34AApy-upw59wy9K-LXo2",
    "dunhuang": "1irMs4ypwquwwR-oOWocFOTWrgLXHnOX3",
    "aurora": "1kYEGzimG45d8Z_yCL9SH4DxQLdUJXFsg",
    "royal series - round": "1-fQcJO5wfjhCjUxokC1Bn5pd-wjTf7tr",
    "diana": "1QaYHLJ8F_5T3vYrO8BmGwbVRX2r3CENJ",
    "aurea": "1e_9WkRvA23Iq7-73hDTllWXDdjds-EuG",
    "ridge": "1SxZsn9icSxXtjrNoXLiZa7-rRDl8Y3w1",
    "lily": "1J41doWtbwKfZCFs7tHj9LYKHMjhN92sT",
    "jade butterfly": "1AZOx4KG5iL5ftxqyZeREHBbPqSs3Zjib",
    "zhizai·8": "1nl8nLay8Zoy6T6zadYQmeO67skzZB1R_",
    "cloud": "1VDYOdAjati7LLOf_OGbLDsOyoZrdYs1r",
    "agate": "1LXYiIVunfdUm8CG9YZBp8iME_gDxuS7i",
    "bella": "1mW9epr-vqVM0HbOIp8xMBwCqeuwCizdK",
    "ivory": "1BS6zTOLYYLrieIeAxOPA6aqlg3YnzXdB",
    "monroe": "1hU7FmMuarBSwAgeD1TRjXEv-2-06RQZH",
    "dreame": "1kF2Ufx416skQWuKu3ctPE1RvKb7UwgQJ",
    "scepter": "1TULyQgt0ssMyCV5Fk2WdRvLaqarPPGjZ",
    "serenity": "13EXglfElRwalZZ0HMApq0yVu9chFCxZD",
    "godfather": "1xAyAJuNleEUWZGw_h9DEYGOvlucjpfsm",
    "king": "14YJ2RhXvV6oj7CPTstCOvPFj90Zv6EEV",
    # Rechargeable Table Lamps
    "\"x\"": "1vd4DzvpWMQMau0IEj6KVzMKtbtVTKMtW",
    "quietvale": "1cjyFcbvm2Py-3yAT7fzBElHu2d_yPKA0",
    "fire": "11UCrPMAh0jy1HXmnDl6y0au_OLBzGRFC",
    "crystal series - curved": "1M5lvy_T2gtHvUKjYonIUtBiu57jBDf-P",
    "metal series": "1qV04QJQWmbULe00H-oGJtUaklgIpNjY-",
    "solitude": "1QbWEQUfYTAdBh48U__4rXGozvGZRDsxG",
    "fluid": "1EWgso2eg6E7fnizhmkbZh7mLw62F7KyN",
    "cheese": "1PkVpLZCAAOeDKPmdMKoojAhwQSqFs9wQ",
    "candlelight": "1G-hSuomIMZfOmanV3fSLvKAYxguaYi7m",
    "whisky": "1oHBHbNjHCCCxF3SFG0wEk_goIuQ_CGTF",
    "air series": "1fCW-t6OAanrM1eY0QT-07UgOIs7tDwRn",
    "luminate series - bevel": "1WCUxVjSFNkx8rpONLj_aCwaAE_ZYG61J",
    "hyponex": "1U6VOTGRoXTvuZqfHK3y4-xrxrQ1qLfZ6",
    "salute": "1xLHoPPjiaUIBwwwpOZQBG0kojmA40Vje",
    "luminate": "1sASkHeHdFOgFD8m1vAMIJd2aDWymba9v",
    "crystal series": "1nHG0B7ezwMxh8q6XelN5L1GglUblHhzm",
    "lumia": "1GQI_9fCTFsje999Qgob0Ivp6Ol_rjXbN",
    "champagne": "1H8IYabWH6jl-KQztBvPsWTkvbY1aeKZg",
    # Floor Lamps
    "black label": "1gI9xp84BrP_heH2Ex39ktyfmmGZQJ0dR",
    "madeline": "1jrQzFvabh3btz3jyyDfpLXUxTmI05byh",
    "flambeau": "15vObMrbrhRk9BrI19v4kLVmChZjR8GAS",
    "hydrogen": "1yumGzqSBft0L6rFlu_36s7DtLEyfo9F8",
    "glacier.n": "1mXp7zCrON-QJV_VRT-jRWQUhkZQE0d0T",
    "madagascar": "10XMVDKHjmSF8IPIoF_57VlPz06cpIJxx",
    "innersun": "1fkgOiQ7v6tyebQ0FuF0dHJkhuSq_AzT8",
    "black amber": "1Juurd1lR_7NZ4Z5l1xHp5-8Tq3h6GeE-",
    "glacier series": "1MFcc9IQfZ-KdRIUQo_3CjwW7WNph0tfX",
    "hillbilly cat": "1ly6hU3Y_h2cj362V7L2zIhwz-CNpVwei",
    "business": "1mdTatVqz0CX2h4ibwljzmFAZrbcszBek",
    "clear shadow": "1Lm2t80Udaj8qJXbNp25eO9V-c4OZZn7N",
    "zhizai·2": "1lcffRuvdJd3Cse3KvqcRjuTjdPWb4j_0",
    "floating light": "1q9kqE5Bm1jvcNzpvTQ_duxwe6u3nvgSp",
    "red label": "1G7jsKB8LxEo_guPJ6dYXZu7_wkSVUvfp",
    "chenin blanc": "1wqr9IVQpc2f9g0aogVx3AxvejmB9BT3m",
    "glow angler": "1R7p0BHLnZcGz5E8qN4s_XkbAPI0Sce-K",
    # Pendant Lamps
    "gabriel": "1WF61xl7oiihcz7KcnyzF9_Qs8Fyk7Lfd",
    "stockholm": "13KFhph_OQTD5UuqZiyzm0igHG3VWnGrO",
    "tequila": "1LR0iSRYpeKO60g6kcZCpTjeKiwMYk2Hf",
    "himalayas": "1rkIvkZ3J5_3SzVM-yVhUDHrHMH3ENX8r",
    "ness": "1Y6gJs6w1GZed6DDRlCmZ1tPcY7m1Mj2y",
    "meteor": "1YoCEIfvlsLR67f2EkPj37S5NfTNmNTgV",
    "sun star": "1nhhrSW6Zg1ZfriU42Et1jEFlCBZHY0i5",
    "ballet": "12-wCbl0n5Q9aPEzlUfH6umRVK_33Xgv8",
    "star of south africa": "1ji-cdQPEkGgAMiMCH6V6ohaL_67yOkUS",
    "instant": "1wgMFhmdIJkUFjIABhqc5MC3oJJ1xpdR4",
    # Wall Lamps
    "tuberose": "1YuIAooiDZO8HfCbukqTAS0XniF_cP3cN",
    "tux": "1LoO845TvNeFOrmV6CRKFNj_jDgsI575Z",
    "barcadi": "1wZB1mDK_Ni_vdzGrhG9_jj84qR1f-Bys",
    "stilton": "1JAIXZhKo341VhNe-ZL10Jb9wQalilLKx",
    "conquistador": "1vsMKYcvbSEVcWZXT1fyFUcG9rUKMIQ-Y",
    # Outdoor
    "defense": "1nW9JhBFaiWxWN628I1v4qBERbZ_sWv",
}


def get_dec_image_url(family: str, product_name: str = None) -> str:
    """Find best matching image for a decorative product by series name."""
    if not family:
        return None
    search = family.lower()

    # Try direct keyword match
    for keyword, file_id in DEC_IMAGE_MAP.items():
        if keyword in search:
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w300"

    # Try matching against product name
    if product_name:
        name_search = product_name.lower()
        for keyword, file_id in DEC_IMAGE_MAP.items():
            if keyword in name_search:
                return f"https://drive.google.com/thumbnail?id={file_id}&sz=w300"

    return None
