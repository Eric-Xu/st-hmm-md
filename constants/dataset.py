# LOC_SLUG = "ca_la"
# LOC_SLUG = "dc_wa"
# LOC_SLUG = "de"
# LOC_SLUG = "fl_mia"
# LOC_SLUG = "ga_atl"
# LOC_SLUG = "il_chi"
LOC_SLUG = "md"
# LOC_SLUG = "mn_min"
# LOC_SLUG = "nh_msa_man_nas"
# LOC_SLUG = "pa_phl"
# LOC_SLUG = "ri_pvd"
# LOC_SLUG = "tx_arl"
# LOC_SLUG = "tx_dal"
# LOC_SLUG = "tx_elp"
# LOC_SLUG = "wa_sea"
# LOC_SLUG = "wy_msa_chy"

LOC_SLUG_TO_LOCATION = {
    "ca_la": "Los Angeles, CA",
    "dc_wa": "Washington, DC",
    "de": "Delaware",
    "fl_mia": "Miami, FL",
    "ga_atl": "Atlanta, GA",
    "il_chi": "Chicago, IL",
    "md": "Maryland",
    "mn_min": "Minneapolis, MN",
    "nh_msa_man_nas": "MSA Manchester-Nashua, NH",
    "pa_phl": "Philadelphia, PA",
    "ri_pvd": "Providence, RI",
    "tx_arl": "Arlington, TX",
    "tx_dal": "Dallas, TX",
    "tx_elp": "El Paso, TX",
    "wa_sea": "Seattle, WA",
    "wy_msa_chy": "MSA Cheyenne, WY",
}
LOCATION = LOC_SLUG_TO_LOCATION[LOC_SLUG]

PROPERTY_TYPES = [
    "Single Family Residential",
    "Condo",
    "Townhouse",
    "Duplex",
    "Triplex",
    "Fourplex",
]

START_DATE = "2024-07-01"
END_DATE = "2025-06-30"

PARTY_TO_COUNTERPARTY = {"borrower": "lender", "lender": "borrower"}
PARTY_TO_DATASET_KEY = {"borrower": "buyerName", "lender": "lenderName"}
