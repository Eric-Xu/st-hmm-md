from constants.dataset import LOC_SLUG

# --- APP ASSETS ---
CSS_DIR = "css"

CSS_FILE = "styles.css"


# --- APP PAGES ---
PAGE_DIR = "views"

BORROWER_LENDERS_PAGE_FILE = "borrower_lenders_page.py"
BORROWER_LOANS_PAGE_FILE = "borrower_loans_page.py"
BORROWER_TIMELINE_PAGE_FILE = "borrower_timeline_page.py"
LENDER_APPEAL_PAGE_FILE = "lender_appeal_page.py"
LENDER_BORROWER_MIGRATION_PAGE_FILE = "lender_borrower_migration_page.py"
LENDER_CHURNED_BORROWERS_PAGE_FILE = "lender_churned_borrowers_page.py"
LENDER_MARKET_SHARE_PAGE_FILE = "lender_market_share_page.py"
LENDER_ORIGINATION_TIMELINE_PAGE_FILE = "lender_origination_timeline_page.py"
LENDER_REPEAT_BORROWERS_PAGE_FILE = "lender_repeat_borrowers_page.py"
LOAN_ANALYSIS_PAGE_FILE = "loan_analysis_page.py"
MARKET_MONOPOLY_PAGE_FILE = "market_monopoly_page.py"


# --- DATA FILES ---
DATA_DIR = "data"

LOC_SLUG_TO_FILE = {
    "ca_la": "ca_la_20240701_20250630.csv",
    "dc_wa": "va_dc_20240701_20250630.csv",
    "de": "de_20240701_20250630.csv",
    "fl_mia": "fl_mia_20240701_20250630.csv",
    "ga_atl": "ga_atl_20240701_20250630.csv",
    "il_chi": "il_chi_20240701_20250630.csv",
    "md": "md_20240701_20250630.csv",
    "mn_min": "mn_min_20240701_20250630.csv",
    "nh_msa_man_nas": "nh_msa_man_nas_20240701_20250630.csv",
    "pa_phl": "pa_phl_20240701_20250630.csv",
    "ri_pvd": "ri_pvd_20240701_20250630.csv",
    "tx_arl": "tx_arl_20240701_20250630.csv",
    "tx_dal": "tx_dal_20240701_20250630.csv",
    "tx_elp": "tx_elp_20240701_20250630.csv",
    "wa_sea": "wa_sea_20240701_20250630.csv",
    "wy_msa_chy": "wy_msa_chy_20240701_20250630.csv",
}
DATA_FILE = LOC_SLUG_TO_FILE[LOC_SLUG]

# --- TEMP FILES ---
TMP_DIR = "tmp"

TMP_DATA_JSON = "tmp_data.json"
