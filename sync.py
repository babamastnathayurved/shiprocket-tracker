import os
import sys
import requests
from supabase import create_client, Client

SHIPROCKET_EMAIL = os.environ.get("SHIPROCKET_EMAIL")
SHIPROCKET_PASSWORD = os.environ.get("SHIPROCKET_PASSWORD")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

def get_shiprocket_token():
    url = "https://apiv2.shiprocket.in/v1/external/auth/login"
    payload = {"email": SHIPROCKET_EMAIL, "password": SHIPROCKET_PASSWORD}
    res = requests.post(url, json=payload, timeout=15).json()
    return res.get("token")

def fetch_orders(token):
    headers = {"Authorization": f"Bearer {token}"}
    processed = {}

    try:
        ndr_url = "https://apiv2.shiprocket.in/v1/external/ndr/orders"
        res = requests.get(ndr_url, headers=headers, timeout=15).json()
        for item in res.get("data", []):
            oid = str(item.get("id") or item.get("order_id"))
            processed[oid] = {
                "id": int(item.get("id")),
                "order_id": str(item.get("order_id")),
                "channel_order_id": str(item.get("channel_order_id", "") or ""),
                "customer_name": str(item.get("customer_name", "N/A")),
                "customer_phone": str(item.get("customer_phone", "N/A")),
                "status": "NDR",
                "awb_code": str(item.get("awb_code", "N/A")),
                "courier_name": str(item.get("courier_name", "Unassigned")),
                "ndr_status": str(item.get("ndr_status", "Action Required")),
                "ndr_reason": str(item.get("ndr_reason", "Undelivered")),
                "is_on_hold": False
            }
    except Exception as e:
        print(f"NDR fetch error: {e}")

    try:
        hold_url = "https://apiv2.shiprocket.in/v1/external/orders?status=ON%20HOLD"
        res = requests.get(hold_url, headers=headers, timeout=15).json()
        for item in res.get("data", []):
            oid = str(item.get("id") or item.get("order_id"))
            processed[oid] = {
                "id": int(item.get("id")),
                "order_id": str(item.get("order_id")),
                "channel_order_id": str(item.get("channel_order_id", "") or ""),
                "customer_name": str(item.get("customer_name", "N/A")),
                "customer_phone": str(item.get("customer_phone", "N/A")),
                "status": "ON HOLD",
                "awb_code": str(item.get("awb_code", "N/A")),
                "courier_name": str(item.get("courier_name", "Unassigned")),
                "ndr_status": "N/A",
                "ndr_reason": str(item.get("hold_reason", "On Hold")),
                "is_on_hold": True
            }
    except Exception as e:
        print(f"On-Hold fetch error: {e}")

    return list(processed.values())

def main():
    token = get_shiprocket_token()
    if not token:
        print("Failed to authenticate with Shiprocket.")
        return
    orders = fetch_orders(token)
    if orders:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        for order in orders:
            supabase.table("shiprocket_orders").upsert(order).execute()
        print(f"Synced {len(orders)} orders successfully.")

if __name__ == "__main__":
    main()
