import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from db import get_connection 

FIRST = ["Het","Ferin","Janak","Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Rohan", "Kavya",
         "Arjun", "Neha", "Karan", "Pooja", "Siddharth", "Meera", "Aditya", "Riya"]
LAST = ["Shah", "Patel", "Sharma", "Mehta", "Iyer", "Reddy", "Singh", "Desai", "Joshi", "Nair"]
PRODUCTS = {
    "Tata Nexon": ["Regular servicing", "Brake noise", "AC not cooling", "Battery issue"],
    "Tata Harrier": ["Engine check light on", "Wheel alignment", "Infotainment not working"],
    "Tata Punch": ["Oil change", "Clutch problem", "Headlight not working"],
    "Titan Edge watch": ["Battery replacement", "Strap broken", "Glass scratched"],
    "Titan Raga watch": ["Watch running slow", "Clasp loose", "Water inside dial"],
    "Tanishq ring": ["Resizing", "Stone loose", "Polishing"],
}
STATUSES = ["Pending", "In Progress", "Completed"]


def main(count):
    rows = []
    for _ in range(count):
        product = random.choice(list(PRODUCTS))
        rows.append((
            f"{random.choice(FIRST)} {random.choice(LAST)}",
            product,
            random.choice(PRODUCTS[product]),
            random.choice(STATUSES),
        ))
    with get_connection() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO service_requests (customer_name, product_name, issue, status) "
            "VALUES (%s, %s, %s, %s)",
            rows,
        )
    print(f"Inserted {count} rows.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
