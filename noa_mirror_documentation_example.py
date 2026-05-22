"""
NOA Sentinels Mirror API - Documentation & Example
================================================================

This script demonstrates how to build complex, multi-mission OData queries.
It covers Temporal, Spatial, and Attribute filtering
for Sentinel-1, 2, 3, and 5P.

FEATURES:
- Automatic Token Management (Keycloak)
- "Complex Query" builder for mixing AND/OR logic
- AUTOMATIC PAGINATION (Follows @odata.nextLink)
"""

import os
import logging
import time
import requests
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("NOA_Client")

# =============================================================================
# OData Filter Builder
# =============================================================================

class ODataBuilder:
    """Helper to generate OData attribute filter strings."""

    @staticmethod
    def string_attr(name, value):
        """
        Builds: Attributes/OData.CSC.StringAttribute/any(att:att/Name eq '...' and ... Value in/eq ...)
        """
        if isinstance(value, (list, tuple)):
            # Join list into ('A', 'B')
            val_str = f"({', '.join([f"'{v}'" for v in value])})"
            op = "in"
        else:
            val_str = f"'{value}'"
            op = "eq"

        return (
            f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq '{name}' "
            f"and att/OData.CSC.StringAttribute/Value {op} {val_str})"
        )

    @staticmethod
    def double_attr(name, value, op="eq"):
        """
        Builds: Attributes/OData.CSC.DoubleAttribute/any(... Value op value)
        """
        return (
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq '{name}' "
            f"and att/OData.CSC.DoubleAttribute/Value {op} {value})"
        )

# =============================================================================
# CLIENT CLASS
# =============================================================================

class NOAClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = "https://sentinels.space.noa.gr/catalogue/odata/v1"
        self.auth_url = "https://sentinels.space.noa.gr/auth/realms/mirror/protocol/openid-connect/token"
        self.client_id = "mirror-client"
        self.token = None
        self.token_expiry = 0

    def _get_token(self):
        if self.token and time.time() < self.token_expiry:
            return self.token

        logger.info("Authenticating...")
        payload = {
            "client_id": self.client_id,
            "username": self.username,
            "password": self.password,
            "grant_type": "password"
        }
        try:
            r = requests.post(self.auth_url, data=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            self.token = data["access_token"]
            self.token_expiry = time.time() + data.get("expires_in", 300) - 60
            logger.info("Authentication successful.")
            return self.token
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def search_complex(self, mission_rules, footprint_wkt, time_filter, max_results=1000):
        """
        Constructs and executes the complex OData filter with PAGINATION.

        Args:
            mission_rules (list): List of dicts, where each dict represents a set of OR conditions.
            footprint_wkt (str): WKT Polygon string.
            time_filter (dict): Dictionary with start/end dates for Content and Publication.
            max_results (int): Safety limit for number of results.
        """
        token = self._get_token()

        # --- Temporal Filters ---
        temporal_parts = []
        if "content_start" in time_filter and "content_end" in time_filter:
            temporal_parts.append(f"ContentDate/Start ge {time_filter['content_start']}")
            temporal_parts.append(f"ContentDate/End le {time_filter['content_end']}")

        if "pub_start" in time_filter and "pub_end" in time_filter:
            temporal_parts.append(f"PublicationDate ge {time_filter['pub_start']}")
            temporal_parts.append(f"PublicationDate le {time_filter['pub_end']}")

        temporal_block = f"({' and '.join(temporal_parts)})" if temporal_parts else ""

        # --- Mission Attribute Rules (OR logic) ---
        attr_map = {
            "platform": "platformShortName",
            "serial": "platformSerialIdentifier",
            "product_type": "productType",
            "polarisation": "polarisationChannels",
            "orbit": "orbitDirection",
            "timeliness": "timeliness",
            "instrument": "instrumentShortName",
            "level": "processingLevel",
            "op_mode": "operationalMode",   # S1 specific
            "proc_mode": "processingMode"   # S5P specific
        }

        mission_blocks = []
        for rule in mission_rules:
            conditions = []
            for key, odata_name in attr_map.items():
                if key in rule:
                    conditions.append(ODataBuilder.string_attr(odata_name, rule[key]))

            if "cloud_min" in rule:
                conditions.append(ODataBuilder.double_attr("cloudCover", rule["cloud_min"], "ge"))
            if "cloud_max" in rule:
                conditions.append(ODataBuilder.double_attr("cloudCover", rule["cloud_max"], "le"))

            if conditions:
                mission_blocks.append(f"({' and '.join(conditions)})")

        if len(mission_blocks) > 1:
            missions_filter = f"({' or '.join(mission_blocks)})"
        elif len(mission_blocks) == 1:
            missions_filter = mission_blocks[0]
        else:
            missions_filter = ""

        spatial_filter = ""
        if footprint_wkt:
            spatial_filter = f"OData.CSC.Intersects(area=geography'SRID=4326;{footprint_wkt}')"

        final_parts = []
        if temporal_block: final_parts.append(temporal_block)
        if missions_filter: final_parts.append(missions_filter)
        if spatial_filter: final_parts.append(spatial_filter)

        raw_filter_str = " and ".join(final_parts)

        # --- Encoding ---
        encoded_filter = quote(raw_filter_str, safe="():,=;/")

        # Initial URL (Top 50 per page by default but this can be changed but expect a dip in the query perfomance)
        url = f"{self.base_url}/Products?$filter={encoded_filter}&$orderby=ContentDate/Start asc&$top=50"

        logger.info("Executing Complex Search (with Pagination)...")
        return self._fetch_all_pages(url, max_results)

    def _fetch_all_pages(self, start_url, max_results):
        """Follows @odata.nextLink until done or max_results reached."""
        all_products = []
        url = start_url

        while url and len(all_products) < max_results:
            headers = {"Authorization": f"Bearer {self._get_token()}"}

            try:
                r = requests.get(url, headers=headers, timeout=20)

                if r.status_code == 200:
                    data = r.json()
                    products = data.get("value", [])
                    all_products.extend(products)

                    logger.info(f"Fetched {len(products)} items (Total: {len(all_products)})")

                    url = data.get("@odata.nextLink", None)
                else:
                    logger.error(f"Page fetch failed [{r.status_code}]: {r.text}")
                    break

            except Exception as e:
                logger.error(f"Request error: {e}")
                break

        return all_products[:max_results]

    def download_product(self, product_id, filename):
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/Products({product_id})/$value"

        logger.info(f"Downloading {filename}...")
        try:
            with requests.get(url, headers=headers, stream=True) as r:
                if r.status_code == 200:
                    with open(filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    logger.info("Download complete.")
                    return True
                else:
                    logger.error(f"Download failed [{r.status_code}]")
                    return False
        except Exception as e:
            logger.error(f"Download Error: {e}")
            return False

if __name__ == "__main__":
    USER = os.getenv("USERNAME", "USERNAME")
    PASS = os.getenv("PASSWORD", "PASSWORD")

  # AREA OF INTEREST
    ROI = 'POLYGON((1.2044961305558362 41.78123498842218,26.573288970814286 41.78123498842218,26.573288970814286 34.831324412099384,1.2044961305558362 34.831324412099384,1.2044961305558362 41.78123498842218))'

    # TIME SETTINGS
    TIME_CONFIG = {
        "content_start": "2026-01-11T00:00:00.000Z",
        "content_end":   "2026-05-22T23:59:59.999Z",
        "pub_start":     "2026-05-11T00:00:00.000Z",
        "pub_end":       "2026-05-22T23:59:59.999Z"
    }

    # MISSION RULES
    MISSION_RULES = [
        # --- SENTINEL-1 ---
        {
            "platform": "SENTINEL-1",
            "serial": ["A", "B"],
            "product_type": ["S2_GRDM_1S", "S6_GRDM_1S", "S6_OCN__2S", "IW_OCN__2S"],
            "polarisation": ["HH", "VV", "VV,VH", "VH,VV", "HH,HV", "HV,HH"],
            "op_mode": ["WV", "EW", "IW", "SM"],
            "orbit": ["DESCENDING", "ASCENDING"],
            "timeliness": ["Reprocessing", "Off-line", "Fast-24h", "NRT-3h", "NRT-1h", "NRT-10m"]
        },
        # --- SENTINEL-2 ---
        {
            "platform": "SENTINEL-2",
            "serial": ["A", "B"],
            "product_type": ["S2MSI1C", "S2MSI2A"],
            "cloud_min": 2,
            "cloud_max": 80
        },
        # --- SENTINEL-3 ---
        {
            "platform": "SENTINEL-3",
            "serial": ["A", "B"],
            "product_type": ["SR_2_LAN_LI"],
            "instrument": ["SRAL", "SLSTR", "SYNERGY", "OLCI"],
            "level": ["2", "1"],
            "timeliness": ["ST", "NT", "NR"]
        },
        # --- SENTINEL-5P ---
        {
            "platform": "SENTINEL-5P",
            "product_type": ["L2__AER_AI", "L2__CO____", "L2__O3_TCL"],
            "proc_mode": ["NRTI", "OFFL", "RPRO"],
            "level": ["L1b", "L2"]
        }
    ]

    client = NOAClient(USER, PASS)

    products = client.search_complex(
        mission_rules=MISSION_RULES,
        footprint_wkt=ROI,
        time_filter=TIME_CONFIG,
        max_results=1000  # Set limit to avoid fetching the whole catalog
    )

    if products:
        print("\n--- Download Candidates ---")
        for i, p in enumerate(products):
            print(f"{i+1}. {p['Name']} ({p['ContentLength']} bytes)")

        product = products[i]
        # Uncomment to download products
        for product in products:
            client.download_product(product['Id'], product['Name'])
    else:
        print("\nNo products found. Try expanding dates or ROI.")
