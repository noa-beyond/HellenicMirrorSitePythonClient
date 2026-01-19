# HellenicMirrorSitePythonClient
NOA Sentinels Mirror API - Python Client Example

This repository contains a robust Python client (`noa_mirror_documentation_example.py`) for querying and downloading satellite imagery from the **NOA Sentinels Mirror**. It demonstrates how to interact with the OData API, handle authentication, build complex multi-mission filters, and manage pagination automatically.

## Service Endpoints

* **Authentication:** `https://sentinels.space.noa.gr/auth`
* **API:** `https://sentinels.space.noa.gr/catalogue/odata/v1`
* **UI:** `https://sentinels.space.noa.gr/copsi`
* **STACAPI:** `https://sentinels.space.noa.gr/copsi/stac` (This feature is currently under development)

## Features

* **Complex Query Builder:** Easily construct advanced filters combining AND/OR logic for multiple missions (e.g., "Get Sentinel-1 GRD OR Sentinel-2 L2A with < 20% cloud cover").
* **Automatic Pagination:** Seamlessly fetches thousands of results by following OData `nextLink`.
* **Safe URL Encoding:** Pre-configured to handle special OData characters (spaces, quotes, parentheses) correctly, preventing "400 Malformed URI" errors.

## Prerequisites

Ensure you have Python 3.8+ installed.

1.  **Install Dependencies:**
    ```bash
    pip install requests python-dateutil
    ```

2.  **Set Environment Variables (Recommended):**
    You can set your credentials in your environment or edit them directly in the script (lines 276-277).
    ```bash
    export ESA_USERNAME="your_username"
    export ESA_PASSWORD="your_password"
    ```

## Usage

### 1. Basic Configuration

Open `noa_mirror_documentation_example.py` and scroll to the `if __name__ == "__main__":` block at the bottom.

**Set your Region of Interest (WKT Polygon):**
```python
ROI = "POLYGON((14.72 41.46, 22.19 41.46, 22.19 37.62, 14.72 37.62, 14.72 41.46))"

**Set your Time Range:**
```python
TIME_CONFIG = {
    "content_start": "2026-01-11T00:00:00.000Z",
    "content_end":   "2026-01-19T23:59:59.999Z",
    "pub_start":     "2026-01-11T00:00:00.000Z",
    "pub_end":       "2026-01-19T23:59:59.999Z"
}
```

### 2. Defining Mission Rules

The `MISSION_RULES` list allows you to define specific criteria for each satellite platform you want. These rules are combined with **OR** logic (find products matching Rule 1 OR Rule 2...).

**Example Configuration:**
```python
MISSION_RULES = [
    # --- Sentinel-1 ---
    {
        "platform": "SENTINEL-1",
        "product_type": ["S2_GRDM_1S", "IW_OCN__2S"],
        "polarisation": ["HH", "VV", "VV,VH"],
        "orbit": ["DESCENDING"]
    },
    # --- Sentinel-2 ---
    {
        "platform": "SENTINEL-2",
        "product_type": ["S2MSI2A"],
        "cloud_min": 0,
        "cloud_max": 20  # Only clean images
    }
]
```

**Supported Keys:**
* `platform`: e.g., "SENTINEL-1", "SENTINEL-2"
* `product_type`: List of product types
* `serial`: ["A", "B"]
* `cloud_min` / `cloud_max`: Cloud coverage range (Sentinel-2 only)
* `polarisation`: ["HH", "VV", ...] (Sentinel-1)
* `orbit`: ["ASCENDING", "DESCENDING"]
* `timeliness`: ["NRT-3h", "Fast-24h", ...]
* `instrument`: ["OLCI", "SLSTR"] (Sentinel-3)
* `level`: ["L1b", "L2"]
* `op_mode`: ["IW", "EW"] (Sentinel-1)
* `proc_mode`: ["NRTI", "OFFL"] (Sentinel-5P)

### 3. Running the Script

Execute the script directly:

```bash
python noa_mirror_documentation_example.py
```

**Output:**
The script will log the authentication status, the generated query URL (for debugging), and list the top found products. By default, download is commented out to prevent disk usage.

```text
[INFO] Authenticating...
[INFO] Authentication successful.
[INFO] Executing Complex Search (with Pagination)...
[INFO] Fetched 50 items (Total: 50)
[INFO] Fetched 50 items (Total: 100)
...
--- Download Candidates ---
1. S1A_IW_GRDH_1SDV_20260111T042011_... (983123 bytes)
2. S2A_MSIL2A_20260112T092321_... (104857600 bytes)
```

## Troubleshooting

* **400 Bad Request:** This usually means a malformed filter. Ensure your WKT polygon is valid and that you are not using `Name` or `Collection` filters directly (use the Attribute builder instead).
* **401 Unauthorized:** Check your username/password. The script handles token refreshing automatically, but the initial login must succeed.
* **0 Results Found:** Double-check your `ROI` (WKT) coordinates and `TIME_CONFIG`. The mirror might not have ingested data for your specific date range yet.

## Support

If you have any questions or encounter issues with the service, please contact the support team at: info.sentinels-el@noa.gr
