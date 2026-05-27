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


    # ============ AUTOMATION - KEYPADS ============
    # Swiss Plastic Panel
    {"family": "automation", "name": "swiss plastic three-channel panel", "color": "champagne silver", "id": "1ubr2EtNoOz2QhMEZ2yrYnPn5mlVY9hWF"},
    {"family": "automation", "name": "swiss plastic three-channel panel", "color": "champagne gold", "id": "1UqksBEQAE8hkoMVvPfks_1Zt74gdXPRz"},
    {"family": "automation", "name": "swiss plastic three-channel panel", "color": "mica black", "id": "1U6zprfEDpCnXGByRKWNNhX1IxX7yozyo"},
    {"family": "automation", "name": "swiss plastic three-channel panel", "color": "warm white", "id": "1N8p-NNf66uFIjmCruBhMZOPUWSmcVEe5"},
    {"family": "automation", "name": "swiss plastic two-channel", "color": "champagne silver", "id": "1ubr2EtNoOz2QhMEZ2yrYnPn5mlVY9hWF"},
    {"family": "automation", "name": "swiss plastic two-channel", "color": "champagne gold", "id": "1UqksBEQAE8hkoMVvPfks_1Zt74gdXPRz"},
    {"family": "automation", "name": "swiss plastic two-channel", "color": "mica black", "id": "1U6zprfEDpCnXGByRKWNNhX1IxX7yozyo"},
    {"family": "automation", "name": "swiss plastic two-channel", "color": "warm white", "id": "1N8p-NNf66uFIjmCruBhMZOPUWSmcVEe5"},
    # Swiss Plastic Thermostat
    {"family": "automation", "name": "swiss plastic three-in-one", "color": "champagne silver", "id": "1q5yoQYuDWhLVIz2RObFkqwtmld4W0_UR"},
    {"family": "automation", "name": "swiss plastic three-in-one", "color": "champagne gold", "id": "1h0YAbn89ZMqqLqIwU8MwFzoIsPGUt0Vk"},
    {"family": "automation", "name": "swiss plastic three-in-one", "color": "mica black", "id": "1ldvqeEczzQY1yNn92rJxn_kZkSb3dh_N"},
    {"family": "automation", "name": "swiss plastic three-in-one", "color": "warm white", "id": "1mLc7ePECRS0OWdzK76HrSTTILduYhJun"},
    # Swiss Metal Panel
    {"family": "automation", "name": "swiss metal three-channel", "color": "champagne silver", "id": "1zrIF5_WBmA3o8ECrhb1yGBxfw_-jszVX"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "champagne gold", "id": "11loWUd35aO2l_J_MQX8QG_ggOftEIKif"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "mica black", "id": "1F0kFXfj037C-wNi-zLKnRPim5VxIVday"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "snowflake silver", "id": "1l919aFXmhgaR0tC11qD27VJMxTsoY6BL"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "warm white", "id": "1Ee8pMWG9vt6RG_VelAOYyUqnHPvGwrbU"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "ferrari red", "id": "1kbRllxhgoXrBzAXuSIq3zSRG9fX7ffKT"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "glossy silver", "id": "1TNhNm5bKgw2kBRr8Kdj1EnhkJ3rh-xaV"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "glossy gold", "id": "1dShS4Bx2X3d52Ym9N1tDrlWMnbU2ZgJN"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "brass", "id": "14IzMjsxF8v4V_3bukUOxBAjvhOnfdtUG"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "swarovski crystal gold", "id": "1VqpaBaz6ayMS00Ynxt5W2vqWYrvg9uBs"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "swarovski crystal silver", "id": "1jl4KcBaaJyhkPMLnOYbZ3rxB1HMT0ftS"},
    {"family": "automation", "name": "swiss metal three-channel", "color": "gem gray", "id": "15dFy9o46de0qCYqA9GFSp7t483h7JBV_"},
    # Swiss Metal Dimming Panel (same images as panel)
    {"family": "automation", "name": "swiss metal two-channel", "color": "champagne silver", "id": "1zrIF5_WBmA3o8ECrhb1yGBxfw_-jszVX"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "champagne gold", "id": "11loWUd35aO2l_J_MQX8QG_ggOftEIKif"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "mica black", "id": "1F0kFXfj037C-wNi-zLKnRPim5VxIVday"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "snowflake silver", "id": "1l919aFXmhgaR0tC11qD27VJMxTsoY6BL"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "warm white", "id": "1Ee8pMWG9vt6RG_VelAOYyUqnHPvGwrbU"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "ferrari red", "id": "1kbRllxhgoXrBzAXuSIq3zSRG9fX7ffKT"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "glossy silver", "id": "1TNhNm5bKgw2kBRr8Kdj1EnhkJ3rh-xaV"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "glossy gold", "id": "1dShS4Bx2X3d52Ym9N1tDrlWMnbU2ZgJN"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "brass", "id": "14IzMjsxF8v4V_3bukUOxBAjvhOnfdtUG"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "swarovski crystal gold", "id": "1VqpaBaz6ayMS00Ynxt5W2vqWYrvg9uBs"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "swarovski crystal silver", "id": "1jl4KcBaaJyhkPMLnOYbZ3rxB1HMT0ftS"},
    {"family": "automation", "name": "swiss metal two-channel", "color": "gem gray", "id": "15dFy9o46de0qCYqA9GFSp7t483h7JBV_"},
    # Swiss Metal Thermostat
    {"family": "automation", "name": "swiss metal three-in-one", "color": "champagne silver", "id": "1iHeegolcaa6CysyXeXBEuIDpv-F8BO2e"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "champagne gold", "id": "1GUfIfL-tbyQuybErYMtcLd0IatBUcxUp"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "mica black", "id": "1ATP3CpoJWHLX_BFsH2eLcS7THxykSElD"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "snowflake silver", "id": "1kLO2-FvyBEr5R8JaqoQzS87DST-ivQF1"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "warm white", "id": "1i3z2odVAIo1Z97eQjiLL78S5g3IaPThD"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "ferrari red", "id": "1kbRllxhgoXrBzAXuSIq3zSRG9fX7ffKT"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "glossy silver", "id": "1AaknFAv7O4CxhavnDKCzAMa6xRgUjSlQ"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "glossy gold", "id": "15M0YU7vyICqIE7PtXXj71lQ3jVFTWDA9"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "swarovski crystal gold", "id": "1VqpaBaz6ayMS00Ynxt5W2vqWYrvg9uBs"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "swarovski crystal silver", "id": "1jl4KcBaaJyhkPMLnOYbZ3rxB1HMT0ftS"},
    {"family": "automation", "name": "swiss metal three-in-one", "color": "brass", "id": "14IzMjsxF8v4V_3bukUOxBAjvhOnfdtUG"},
    # Steve Leung Panel
    {"family": "automation", "name": "steve leung three-channel", "color": "champagne silver", "id": "1o8-c41ULX4pvKa4A7__5OGrKjyRVulE4"},
    {"family": "automation", "name": "steve leung three-channel", "color": "champagne gold", "id": "10cFd5CZvz_S8-XVFsICXmivBsXMgOoVN"},
    {"family": "automation", "name": "steve leung three-channel", "color": "mica black", "id": "1w_Yqvp1Az9WYo65Wwn0HmdVB_auignoz"},
    {"family": "automation", "name": "steve leung three-channel", "color": "snowflake silver", "id": "10xr7y-9wC30WEVQO1QWNitugsu_RaQc0"},
    {"family": "automation", "name": "steve leung three-channel", "color": "glossy silver", "id": "1CKh5kgMiX2snhSy-UEvxCqMmWw4F0lXU"},
    {"family": "automation", "name": "steve leung three-channel", "color": "glossy gold", "id": "1CTi19cpc219qsCKcmYSIfYMGfQIUJmO7"},
    # Steve Leung Dimming (same images)
    {"family": "automation", "name": "steve leung two-channel", "color": "champagne silver", "id": "1o8-c41ULX4pvKa4A7__5OGrKjyRVulE4"},
    {"family": "automation", "name": "steve leung two-channel", "color": "champagne gold", "id": "10cFd5CZvz_S8-XVFsICXmivBsXMgOoVN"},
    {"family": "automation", "name": "steve leung two-channel", "color": "mica black", "id": "1w_Yqvp1Az9WYo65Wwn0HmdVB_auignoz"},
    {"family": "automation", "name": "steve leung two-channel", "color": "snowflake silver", "id": "10xr7y-9wC30WEVQO1QWNitugsu_RaQc0"},
    {"family": "automation", "name": "steve leung two-channel", "color": "glossy silver", "id": "1CKh5kgMiX2snhSy-UEvxCqMmWw4F0lXU"},
    {"family": "automation", "name": "steve leung two-channel", "color": "glossy gold", "id": "1CTi19cpc219qsCKcmYSIfYMGfQIUJmO7"},
    # Steve Leung Thermostat
    {"family": "automation", "name": "steve leung three-in-one", "color": "champagne silver", "id": "1gY5VB7Wy-w3akyypuZ-mSY8AJpUs_cA6"},
    {"family": "automation", "name": "steve leung three-in-one", "color": "champagne gold", "id": "1A4FELn7bbAnbXPYR9rA2evXgb-ahz_F9"},
    {"family": "automation", "name": "steve leung three-in-one", "color": "mica black", "id": "1rfPuVWFP4g51f8Ifo-789RIs31cmUX3T"},
    {"family": "automation", "name": "steve leung three-in-one", "color": "snowflake silver", "id": "1D35EEpsHIdkngDPZImdT7ZWkjsYpZzRJ"},
    {"family": "automation", "name": "steve leung three-in-one", "color": "glossy silver", "id": "1hC3pdgYThIYhwL2tKfVVRmiYHCJV72fW"},
    {"family": "automation", "name": "steve leung three-in-one", "color": "glossy gold", "id": "1QmhJgfVDtDz5MY5XlzIqCl8cSluyct1H"},
    # Zaha Panel
    {"family": "automation", "name": "zaha three-channel", "color": "aluminum", "id": "18a97yZOomRj2DieMFkwlQEMimfDgx6qG"},
    {"family": "automation", "name": "zaha three-channel", "color": "glossy silver", "id": "1zefzx4O6CDzV3k-mwExL3ecWFzaHJnfC"},
    {"family": "automation", "name": "zaha three-channel", "color": "glossy gold", "id": "1-jXbe61ANfD-v0DGIhzlQvLmofjDYegL"},
    {"family": "automation", "name": "zaha two-channel", "color": "aluminum", "id": "18a97yZOomRj2DieMFkwlQEMimfDgx6qG"},
    {"family": "automation", "name": "zaha two-channel", "color": "glossy silver", "id": "1zefzx4O6CDzV3k-mwExL3ecWFzaHJnfC"},
    {"family": "automation", "name": "zaha two-channel", "color": "glossy gold", "id": "1-jXbe61ANfD-v0DGIhzlQvLmofjDYegL"},
    # Zaha Thermostat
    {"family": "automation", "name": "zaha three-in-one", "color": "aluminum", "id": "1HDWYWTvPhbgfHgt8DDtsbDtAfxezvgHC"},
    {"family": "automation", "name": "zaha three-in-one", "color": "glossy silver", "id": "1NG3j8iEAj5s2XoHxH7zQX6P9fafm8S5L"},
    {"family": "automation", "name": "zaha three-in-one", "color": "glossy gold", "id": "1q9YUGT4VItdLrJDcxdqwZag90zDQIQum"},
    # Iceland
    {"family": "automation", "name": "iceland three-channel", "color": "champagne silver", "id": "1fKLYuHhUTUaX7_2hKfUebNIFbnT4XFaQ"},
    {"family": "automation", "name": "iceland three-channel", "color": "mica black", "id": "17WlRl-kh06Yg8BP2SypvwkML128xK5Xt"},
    {"family": "automation", "name": "iceland three-in-one", "color": "champagne silver", "id": "1uks2KgjcXrGw92KanGLkDWMRSNzWvIEl"},
    {"family": "automation", "name": "iceland three-in-one", "color": "mica black", "id": "1uUbef8fVBfZXM_SvaSLlclBxWRn6Js8c"},
    # Bali
    {"family": "automation", "name": "bali three-channel", "color": "champagne silver", "id": "1qNTErV_rcieiItVxb6sVY0Dg6PgCm8q_"},
    {"family": "automation", "name": "bali three-channel", "color": "warm white", "id": "1T6BrV7vwHGF92J3qbHPJx6X6Aq7U8YQQ"},
    {"family": "automation", "name": "bali thermostat", "color": "champagne silver", "id": "1py165LggaJzdZQ7k2CTYjMJWauanawSk"},
    {"family": "automation", "name": "bali thermostat", "color": "warm white", "id": "1gxGumpTP-SFMaAQ58I5DS4XuKBVb-fYf"},
    # Newton
    {"family": "automation", "name": "newton 2-key", "color": "aluminum 1-gang", "id": "1UaCwDU9Y53iZrTxYQKs8bmJe6ZEWaRzD"},
    {"family": "automation", "name": "newton 2-key", "color": "aluminum 2-gang", "id": "1FegVX_xCDeXVtqz-UXx8xTNAJZtP6m83"},
    {"family": "automation", "name": "newton 2-key", "color": "aluminum 3-gang", "id": "1OANaRX3QXCkkhvTs_ecOTaXW3JewiX5G"},
    {"family": "automation", "name": "newton 2-key", "color": "brass 1-gang", "id": "14bqoNgTilpq02k8LXfsPFRWysqV-YAWb"},
    {"family": "automation", "name": "newton 2-key", "color": "brass 2-gang", "id": "1d1uy8qx767zSFpM4qTPLvXtcHNjpoV-m"},
    {"family": "automation", "name": "newton 2-key", "color": "brass 3-gang", "id": "1EVFeYUNtot7CM2GQaKBWAeJInos8Xx7p"},

    # ============ AUTOMATION - DIALERS ============
    {"family": "automation", "name": "king touchscreen", "id": "1-jMVNtIsUl5gkaV8s3dGcY2IKK_gDoTI"},
    {"family": "automation", "name": "m18 smart dimming knob", "color": "glossy black", "id": "1Ttua949tNNwGYEX6s5LuBZoTP4YZBKMv"},
    {"family": "automation", "name": "m18 smart dimming knob", "color": "glossy gold", "id": "14sEXUnq2VtPJzyM3LlmmhhPO-3zGIdNN"},
    {"family": "automation", "name": "m18 smart dimming knob", "color": "glossy silver", "id": "1-Dn1NmmMutUOZhmIC0tJrK2CDgDZ5XYW"},
    {"family": "automation", "name": "m52", "id": "1i6IfcmvEDcLtSH5Mdf1lGQ9FWat0hzPR"},
    {"family": "automation", "name": "m56 four-key", "color": "glossy black", "id": "11Q0oN03cH5rd-ZjdyI-PmMfx-9TJOolS"},
    {"family": "automation", "name": "m56 four-key", "color": "glossy gold", "id": "1io7xMO5zRi1rhMEL31QUpSLYgxw6RGZ9"},
    {"family": "automation", "name": "m56 four-key", "color": "glossy silver", "id": "1UjHF978s9bXRxczhEQsMai3rKh3hychh"},
    {"family": "automation", "name": "m58 four-key", "color": "glossy black", "id": "18PFBiAe-QF23MMgY_LHtZP5GjMSpX_c1"},
    {"family": "automation", "name": "m58 four-key", "color": "glossy gold", "id": "1TYUH1vwYGOWIg1bme7KGxH8O6B_vGKEF"},
    {"family": "automation", "name": "m58 four-key", "color": "glossy silver", "id": "1_S0Hg1161O2iAGv3k9GWc1anEveFzGz4"},
    {"family": "automation", "name": "m78 crystal", "color": "gold ring black base", "id": "1y41MIxTC5RSs3QEaK9cfboihMHa8QqC2"},
    {"family": "automation", "name": "m78 crystal", "color": "silver ring black base", "id": "1Fes7ljSumOvximn52B6lHtGJcZP1fVVK"},
    {"family": "automation", "name": "m78 crystal", "color": "silver ring silver base", "id": "1dgA5Ct3kc4RvikpxmDEh21M0VBtvLXSz"},
    {"family": "automation", "name": "m78 tourbillon", "color": "gold ring black base", "id": "1jSoEvBeI55OTuNfzRfJQfYg3tEhObaBC"},
    {"family": "automation", "name": "m78 tourbillon", "color": "silver ring black base", "id": "1lZqsLJqd-Bj_Gw_NsAdQ6_EILOfj4UJ8"},
    {"family": "automation", "name": "m78 tourbillon", "color": "silver ring silver base", "id": "1sC6nCPW9Twc0XJXKl0x5aw9qssbSuk6R"},
    {"family": "automation", "name": "milan crystal", "color": "belgium silver", "id": "18vFX21yb-5L_Z8m-aCOQcda_9sbEk4IK"},
    {"family": "automation", "name": "milan crystal", "color": "monaco gold", "id": "1rkxnYcLll-mu25mGnUe5-x5Z42dIOQCs"},
    {"family": "automation", "name": "milan tourbillon", "color": "belgium silver", "id": "1ARnpCFKcQ9tzSHrUCPrMlcY0JIKiNvpX"},
    {"family": "automation", "name": "milan tourbillon", "color": "monaco gold", "id": "11BK4RrAekpCLT8hD9bXyAIUNbc-MZZni"},
    {"family": "automation", "name": "queen crystal", "id": "1fkDmcIv25_HiM1mS127sUUcQyyjFldW7"},
    {"family": "automation", "name": "queen tourbillon", "id": "1exSMfGIi78Szqvk5mh2i-VIQKBcI4vYC"},
    {"family": "automation", "name": "wu bin travelogue mountain series 4-button", "id": "1vl5EAUESBZZ8RwQ4kCt1BV9gQa9vebZz"},
    {"family": "automation", "name": "wu bin travelogue mountain series battery", "id": "1jqndC2FMdEn3I5r_brVfrkJcJ7EhVRdm"},
    {"family": "automation", "name": "wu bin travelogue mountain series lcd", "id": "1RgxRaKZneTKdqjO0Zodjq2ac6XhzdPsm"},

    # ============ AUTOMATION - REMOTES ============
    {"family": "automation", "name": "m1 single key", "id": "1vBgYwjOTxbOJ4Ye4hqCuqQ6eD6g2UE-1"},
    {"family": "automation", "name": "m2 dual key", "color": "belgian silver", "id": "1pbq4tIR7FkwFEn6_z1tN_NMdLBPNEdHZ"},
    {"family": "automation", "name": "m2 dual key", "color": "black", "id": "1fIXIgzcWELmX3TOYAdVcLHblH-z0SLKH"},
    {"family": "automation", "name": "m2 dual key", "color": "white", "id": "11UsAvgJ4Aj9n5K1NxYo_O7A4kU3XOuRB"},
    {"family": "automation", "name": "m10 smart remote", "color": "brass", "id": "1f5NT5fH6vOy3vXMI93S1Br-AMSzQ1r7U"},
    {"family": "automation", "name": "m10 smart remote", "color": "champagne gold", "id": "1l6YY_VQMH-5y_iJLTvKXmVRLeoTeSIl2"},
    {"family": "automation", "name": "m10 smart remote", "color": "champagne silver", "id": "1kprPQvfDYpLtzCoo9MccY8SDYHciIuUU"},
    {"family": "automation", "name": "m10 smart remote", "color": "ferrari red", "id": "1cjIan8ufpBH_8mcQGYhyH8bVAYszDPhF"},
    {"family": "automation", "name": "m10 smart remote", "color": "gem gray", "id": "1pTSy6Rz3bcuSPSy5YCSuln97PKY1aWkK"},
    {"family": "automation", "name": "m10 smart remote", "color": "glossy gold", "id": "1z42GEUhLvFX5G1w9gyOekoeO4D1xasqV"},
    {"family": "automation", "name": "m10 smart remote", "color": "glossy silver", "id": "1tFHpIiFPJuxNK_2Yh-h2w-6x538aOsZf"},
    {"family": "automation", "name": "m10 smart remote", "color": "mica black", "id": "1m1eSjbABBv5OrPfwhzPVUn3pdfPYUwRh"},
    {"family": "automation", "name": "m10 smart remote", "color": "snowflake silver", "id": "1LDpT727yM4w9aJ628OeYqXK4J5RYY5kR"},
    {"family": "automation", "name": "m10 smart remote", "color": "swarovski crystal gold", "id": "1LH2g9C3sPwfDEqq2kQb_Dmc1TDugWSUI"},
    {"family": "automation", "name": "m10 smart remote", "color": "swarovski crystal silver", "id": "1mcLKDJ3DIftFqVaC_VT7cUtkN-hInR4R"},
    {"family": "automation", "name": "m10 smart remote", "color": "warm white", "id": "1UoQAyzIgmZukV0JCRTUlP7Fu8_2nSj8F"},
    {"family": "automation", "name": "m36 12-key", "color": "glossy black", "id": "1cQqDV8ZfPjO1g8agoELdVs5RpBK8C-eQ"},
    {"family": "automation", "name": "m36 12-key", "color": "glossy gold", "id": "14N_Ub3ALbAd4QkzMA2DP_GXMigHrIK5r"},
    {"family": "automation", "name": "m36 12-key", "color": "glossy silver", "id": "19Zhc4IMlvmO6-GwVXWY-Gv8kGqg7T4EJ"},
    {"family": "automation", "name": "m36 24-key", "color": "glossy black", "id": "10pdlEa6AJkqYuAoH7cBiWSXh9-YOJrC9"},
    {"family": "automation", "name": "m36 24-key", "color": "glossy gold", "id": "1PFqJtGkiTZiQPASRT14k6Y3HnNYO_uDD"},
    {"family": "automation", "name": "m36 24-key", "color": "glossy silver", "id": "17nO63jiRI73NZlIEIO2b2AKsRDBsldJK"},
    {"family": "automation", "name": "m36 remote control dock", "id": "1vkBfEEVpUL2UyfkCa4fagS00Ym_MHEw3"},
    {"family": "automation", "name": "m50 8-key", "color": "glossy black", "id": "1QnkaJeVKHFCNnKzRK3VK1XhIwh3ZX3uA"},
    {"family": "automation", "name": "m50 8-key", "color": "glossy gold", "id": "1EALA3md_l0xdMYiakkPiPv60GGYzmWaD"},
    {"family": "automation", "name": "m50 8-key", "color": "glossy silver", "id": "1WsUld65xzGEG3JLemSAp3XV3OmZOtn-S"},
    {"family": "automation", "name": "m50 16-key", "color": "glossy black", "id": "1ALrkbTtOBbQNXExqymdPNqNNjwDKmcJ-"},
    {"family": "automation", "name": "m50 16-key", "color": "glossy gold", "id": "1keq6WsHtocQ-1UlSByM09P4_cnupzksb"},
    {"family": "automation", "name": "m50 16-key", "color": "glossy silver", "id": "10henT6LSs3fBmAxNzSRRmV0DHuXwCqEg"},
    {"family": "automation", "name": "m56 33-key", "color": "glossy black", "id": "1OR3zvdAU6sZSF69uj3tAOujQPOI5HHwG"},
    {"family": "automation", "name": "m56 33-key", "color": "glossy gold", "id": "1DqilRpOZ2JT7hWg2K8aWTsDR5gq61bFv"},
    {"family": "automation", "name": "m56 33-key", "color": "glossy silver", "id": "1q3xrnnHbtEklnsIxYtTgFKu-B4HJ20Ab"},

    # ============ AUTOMATION - GATEWAYS ============
    {"family": "automation", "name": "air conditioning gateway", "id": "1N9XnVccGAgf_F9Onb35oTaHA0NrLUyYM"},
    {"family": "automation", "name": "decorative lamp wireless gateway", "id": "1mZl2HKGK_hSXy4rYANZU8pEBh2rWG5_u"},
    {"family": "automation", "name": "gateway panel", "color": "champagne silver", "id": "1cBcQVrP5cxMq9u-1Aau7XeO5esJoJiJL"},
    {"family": "automation", "name": "gateway panel", "color": "champagne gold", "id": "17RYedxkVeCoTXxNPeyBZioT6PGx70FrG"},
    {"family": "automation", "name": "gateway panel", "color": "mica black", "id": "1Jdg5HINCayU6rpCcieLFDieSTA9-5gjY"},
    {"family": "automation", "name": "gateway panel", "color": "warm white", "id": "19_Loyp2SR3Nl0_Bp0F-ZiLpZ2yrZb6m5"},
    {"family": "automation", "name": "gateway panel", "id": "1cBcQVrP5cxMq9u-1Aau7XeO5esJoJiJL"},

    # ============ AUTOMATION - HOSTS ============
    {"family": "automation", "name": "wireless super host", "id": "1C4kg91janI4yZDDJdX4WyuwntrIeeUTi"},
    {"family": "automation", "name": "desktop host", "id": "1lIVv0-NCKo7tp5aXo5OvtYmxiyGZubee"},
    {"family": "automation", "name": "swiss plastic host panel", "color": "champagne silver", "id": "1WvuVxNSGaLan77ra-DTp1RlT0smr87Oa"},
    {"family": "automation", "name": "swiss plastic host panel", "color": "champagne gold", "id": "14Q0cz7J4wTnWxyYJyTYdN3_HZH0WGROd"},
    {"family": "automation", "name": "swiss plastic host panel", "color": "mica black", "id": "1u3kmCd2dT9i1ic0RNBspAE-BAhd2d5Dj"},
    {"family": "automation", "name": "swiss plastic host panel", "color": "warm white", "id": "1OfMTA35TOL--6ek6FJD65Nvt39OG5xYn"},

    # ============ AUTOMATION - MODULES ============
    {"family": "automation", "name": "0-10v control module", "id": "1V6Aylsqytji_zdk3q11hYRexIoHt6QfO"},
    {"family": "automation", "name": "dry contact controller", "id": "1cfclVekGm9hw-oNBRlrag_pgJQ74uSB1"},
    {"family": "automation", "name": "two-channel smart module", "id": "1LYm_wLx1e1uW--P7BrQIIZTVyTD6nU3m"},
    {"family": "automation", "name": "wireless infrared module", "id": "1AH4Az0xxciFyhz_2Z9eosEpnK0SfxwY8"},
    {"family": "automation", "name": "zigbee repeater", "id": "1_i0ZtfSOXsxqexNJMkdaZviKldTQXtok"},
    {"family": "automation", "name": "zigbee to 868", "id": "1q55fTz7s4HGH_d-bbfGWbg2h5QuRC5Cf"},
    {"family": "automation", "name": "zigbee to rs485", "id": "1xIPEsE4CzKVSpAEPT-9Fse0asHYJWdrT"},

    # ============ AUTOMATION - MOTORS ============
    {"family": "automation", "name": "series 5 curtain motor", "id": "1d9RZ0Mr_kvhlTuI6XbQDBuM43fX-ksVg"},
    {"family": "automation", "name": "traverse curtain track", "id": "1LQXbVEcDmfR5k85LNQ9y6L6MgjJVeHz8"},
    {"family": "automation", "name": "tubular motor 12v", "id": "1RB3e8dJAXi4EyEzDVHtKdDDKT6SKr7ZH"},
    {"family": "automation", "name": "tubular motor 220v", "id": "1WO1fZMUAo5kKiEeclTF7sH8KRikN8qde"},

    # ============ AUTOMATION - SENSORS ============
    {"family": "automation", "name": "battery gravity sensor", "id": "10966gVBhdxBjrXn8spkLG5Ya-GLfNu61"},
    {"family": "automation", "name": "battery motion sensor", "id": "12FpVhmSGvH27UcTaiwLDQeCWNthZT8Y5"},
    {"family": "automation", "name": "fixed-point sensor", "color": "black", "id": "157vkDweJN2uNIN3_rUEioa-5cBMHKekz"},
    {"family": "automation", "name": "fixed-point sensor", "color": "white", "id": "1pTIzDf80lCst3ol1z2wmdkeF2Bb8Qn1-"},
    {"family": "automation", "name": "light-sensitive motion sensor", "color": "black", "id": "12-_g8DK69vULUxNo3Z89BMpHjgrYp-VZ"},
    {"family": "automation", "name": "light-sensitive motion sensor", "color": "white", "id": "1Qoc4_rQlQ-miE_fYmR_WEoJ0M-PnYiaO"},
    {"family": "automation", "name": "motion sensor", "color": "white", "id": "1JUqfPww2Crkt2EPYkrQLfC-WYlofmtyc"},
    {"family": "automation", "name": "night sensor", "color": "black", "id": "1GDKw6c0C_CfkCJsf21IDCO43z3frOUtw"},
    {"family": "automation", "name": "night sensor", "color": "white", "id": "1djjJjsiOs2UFOLxsi1hWVkOLNB9y7UI9"},
    {"family": "automation", "name": "waterproof presence sensor", "color": "black", "id": "1BBgSR8hZ-pkeSCjxYZjcMxmvARMtvhus"},
    {"family": "automation", "name": "waterproof presence sensor", "color": "white", "id": "1ng7AyHC6h6LDuae8LNOVw7m4Wxprm3wc"},

    {"family": "oem", "name": "10mm magnetic track", "id": "1z7_DKQ4skqmMZPCnXKsOkxZg9W56G5Da"},
    {"family": "oem", "name": "12w bollard", "id": "1gVBGYqStYPEwtK03S0-sPswt0yY9Lo8n"},
    {"family": "oem", "name": "12w cob", "id": "1Be7hkNeyPFrfknmowS4ZEufoUhIvFi3v"},
    {"family": "oem", "name": "16w surface diffused", "id": "15TEHJ1ogW48yDPa6W5tukgGZ-Z0soUaG"},
    {"family": "oem", "name": "18w deep recessed downlight", "id": "11nZLJ3pa80KAu8C19EGw9twKt3sQMvxS"},
    {"family": "oem", "name": "18w surface cob", "id": "1sYCahkcqQzs_59OCxW583zgFG5Nff5SX"},
    {"family": "oem", "name": "20w surface cob", "id": "1CwHtX1sa5JtCS0R4yAXEYyQQzX6WCdr3"},
    {"family": "oem", "name": "30w led suspended linear", "id": "1qf5BK0Ie4gdfBabJWdPat7aCbYc2DZbx"},
    {"family": "oem", "name": "3w recessed cob", "id": "16qMKF3jPkOM9XJwqqLZ5p8HbujCwTuAN"},
    {"family": "oem", "name": "3w spotlight", "id": "1lF8P0Bjm33YLlCna7gAhFdIqXXX9FFyR"},
    {"family": "oem", "name": "50w dali driver", "id": "11xDuXwKQZsOhgTsUG4sc-DtLFMJHPRNK"},
    {"family": "oem", "name": "7w recessed cob 3k", "id": "19ztGJtBZPRnmr24ScWPEA4MDW6pAdrq2"},
    {"family": "oem", "name": "7w recessed cob ip", "id": "1MhBxQ3aHhJvw6aWHT2Yc3D1DJsBne_FH"},
    {"family": "oem", "name": "7w recessed cob", "id": "1iVk8ngXyZauX4ZqEMn9ViU3boGs1VAFs"},
    {"family": "oem", "name": "8mm strip light", "id": "13MBjVZSOR6GpPaeyyhZJ_oP7a6a-vx_t"},
    {"family": "oem", "name": "8w surface downlight", "id": "1snfqVngJDtTF9loKlitGdBZt9NJUIvjE"},
    {"family": "oem", "name": "9-24w dali driver", "id": "1Y84F3lFkm_HJ_kqkkwPUUA5ngybyJmji"},
    {"family": "oem", "name": "cc dali driver", "id": "1zVaAie4WkJ2juutxkMlPsVVkh8DzDHXi"},
    {"family": "oem", "name": "concealed panel lights", "id": "1nbVrvmB5BIffX9zkcAPQYtpPKcz1v0xk"},
    {"family": "oem", "name": "connectors for track", "id": "1xBHnflrCf1kpX8Adxxzwxpc9ZcG7XBKu"},
    {"family": "oem", "name": "cove profile light", "id": "1_TPI8irTSXfOAPlywPy3Z27VDbQF1Eaf"},
    {"family": "oem", "name": "curtain grazer", "id": "17tupG7gdo1Zg7nyZ9LzM1fWWC08j0s8f"},
    {"family": "oem", "name": "curve profile", "id": "1pj4YYFgrJzwjsrgw2uKfqN6xYu0hbQOd"},
    {"family": "oem", "name": "cv dali driver", "id": "115XmcRrRZ91_16z5Voqg67j_ZdNwY-V1"},
    {"family": "oem", "name": "dali driver", "id": "1e7sVkHg3CVXg2O-soXMauXBQred5hm_R"},
    {"family": "oem", "name": "fibre optics", "id": "1mK_BBPrRXqNiR3tuZeaNSa7LwtywGCT8"},
    {"family": "oem", "name": "flex profile light", "id": "1vZZuO1aWKRavF8yPc8EC1dW8KpjBbrkd"},
    {"family": "oem", "name": "laser spots", "id": "1Bi7T_F9QXWlLpKHk8_Fbl78mAhvNoOi5"},
    {"family": "oem", "name": "linear profile", "id": "14JPQk40UUD0T72vqu8999yPEpziI1m0Q"},
    {"family": "oem", "name": "live end", "id": "17eQ7uekM-VVeGYucDP2o2TE2qiKSnsZW"},
    {"family": "oem", "name": "magnetic track driver 100w", "id": "15sOMydHmGkNnCVhaTCue2J6bDw4WIpXe"},
    {"family": "oem", "name": "pixel control stretch ceiling", "id": "1Vsp6va27JUc4N6VQ0jmal2mzTpivhoK_"},
    {"family": "oem", "name": "pullot", "id": "1tOEfVo3KAYTNq64si2CxLVCmMX7_5IZw"},
    {"family": "oem", "name": "recessed diffuse light", "id": "1KmyAsX66PcSt4AlBP4OuqXroHybOJt0F"},
    {"family": "oem", "name": "recessed linear profile", "id": "1ewHPQuwee9dStmk2yUymmW0Dsju9yWbK"},
    {"family": "oem", "name": "stretch ceiling", "id": "1ZIAixKRM_QEnOudaOEmCQflUCSf4E78V"},
    {"family": "oem", "name": "surface cylinders", "id": "1jZuUNTWsUgf8XYSANjW5tVS94G550qxm"},
    {"family": "oem", "name": "surface panels", "id": "1I7lKKj1nHEk4z9eDvTyLSVfthAJtBXc2"},
    {"family": "oem", "name": "track spot", "id": "1A3YPL9UedWAg1H8JqrY_QWeu8KC74tWK"},
    {"family": "oem", "name": "tunable stretch ceiling", "id": "15ZDfZYscBRrZD0yFaXL7GNbDsT57Nysh"},
    {"family": "oem", "name": "under staircase profile", "id": "1kjWEx0mOy-ufshfG65NCoVVGhgiT4TZK"},
    {"family": "oem", "name": "wall grazer profile", "id": "1-T6xP80vnXyxE75eb99FD_o43_-ZyNU6"},
    {"family": "oem", "name": "wall washer", "id": "1eBIyi3wnHH3H1f6bLhZwNutTvTJI_l4i"},
    {"family": "decorative", "name": "rechargeable table lamp", "id": "1jbP9LQvRC2Um7WUWWe_PnUfChE7L6TT3"},
    {"family": "decorative", "name": "table lamp", "id": "1TVAT9oyQV7PuRNP-E_4UCaUJFCFgBt_l"},
    {"family": "decorative", "name": "floor lamp", "id": "1Jn6TiDfWouCpXipT_sPzfbhyWpqsO0Z-"},
    {"family": "decorative", "name": "pendant lamp", "id": "1jQ2c8tT0idB035UtNgDrsOd3rdJifExq"},
    {"family": "decorative", "name": "wall lamp", "id": "1JDPuIS3livu9LqD5yUwdT7qCkWBUzGS8"},
    {"family": "decorative", "name": "outdoor lamp", "id": "1ciUG7btHHH9pHjdd4uxYfWebNnjgkRpI"},
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
# ── Decorative category fallbacks ──────────────────────────────────────────
{"family": "decorative", "name": "rechargeable table lamp", "id": "1jbP9LQvRC2Um7WUWWe_PnUfChE7L6TT3"},
{"family": "decorative", "name": "table lamp", "id": "1TVAT9oyQV7PuRNP-E_4UCaUJFCFgBt_l"},
{"family": "decorative", "name": "floor lamp", "id": "1Jn6TiDfWouCpXipT_sPzfbhyWpqsO0Z-"},
{"family": "decorative", "name": "pendant lamp", "id": "1jQ2c8tT0idB035UtNgDrsOd3rdJifExq"},
{"family": "decorative", "name": "wall lamp", "id": "1JDPuIS3livu9LqD5yUwdT7qCkWBUzGS8"},
{"family": "decorative", "name": "outdoor lamp", "id": "1ciUG7btHHH9pHjdd4uxYfWebNnjgkRpI"},
    # ============ OEM PRODUCTS ============
