# HellenicMirrorSitePythonClient
NOA Sentinels Mirror API - Python Client Example

This repository contains a robust Python client (`noa_mirror_documentation_example.py`) for querying and downloading satellite imagery from the **NOA Sentinels Mirror**. It demonstrates how to interact with the OData API, handle authentication, build complex multi-mission filters, and manage pagination automatically.

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
