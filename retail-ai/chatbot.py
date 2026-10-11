
import csv
import requests

URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:1.5b"
CSV_FILE = "products.csv"
MIN_MARGIN = 0.20


def get_products():
    with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    results = []

    for row in rows:
        cost = float(row["cost_price"])
        price = float(row["selling_price"])
        stock = int(row["stock"])
        competitor = float(row["competitor_price"])

        margin = (price - cost) / price if price > 0 else 0
        minimum_price = cost / (1 - MIN_MARGIN)
        max_discount = max(0, (price - minimum_price) / price * 100)

        results.append({
            "product": row["product"],
            "cost_price": cost,
            "selling_price": price,
            "stock": stock,
            "competitor_price": competitor,
            "profit_margin_percent": round(margin * 100, 2),
            "max_discount_percent": round(max_discount, 2),
            "minimum_price_at_20_percent_margin": round(minimum_price, 2),
            "stock_clearance_priority": stock
        })

    return results


def show_products(products):
    print("\n--- Verified Product Analysis ---")
    for p in products:
        print(
            f"{p['product']}: Stock={p['stock']}, "
            f"Margin={p['profit_margin_percent']}%, "
            f"Maximum safe discount={p['max_discount_percent']}%, "
            f"Competitor price=₹{p['competitor_price']}"
        )
    print()


def generate_promotion_plan(products):
    # Prioritize products with high stock.
    ranked_products = sorted(
        products,
        key=lambda p: p["stock"],
        reverse=True
    )

    plan = []

    for p in ranked_products:
        discount = p["max_discount_percent"]

        # Do not recommend a discount that violates the 20% margin.
        promotional_price = p["selling_price"] * (1 - discount / 100)
        profit = promotional_price - p["cost_price"]
        actual_margin = profit / promotional_price * 100

        # Compare the promotional price with the competitor.
        competitive = promotional_price <= p["competitor_price"]

        plan.append({
            "product": p["product"],
            "duration_days": 7,
            "stock": p["stock"],
            "original_price": p["selling_price"],
            "competitor_price": p["competitor_price"],
            "recommended_discount_percent": round(discount, 2),
            "promotional_price": round(promotional_price, 2),
            "profit_per_unit": round(profit, 2),
            "margin_after_discount_percent": round(actual_margin, 2),
            "matches_competitor_price": competitive
        })

    return plan



messages = [
    {
        "role": "system",
        "content": """
You are a Retail Promotion Planner AI.
Python provides verified product calculations.
Use those values; do not recalculate or invent them.
Recommend promotions considering stock, profit margin,
safe discount limits, and competitor prices.
Minimum required profit margin after discount is 20%.
Explain when competitor pricing makes a discount unsuitable.
Keep recommendations concise.
"""
    }
]

print("Retail AI Promotion Planner")
print("Minimum profit margin: 20%")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()

    if user_input.lower() == "exit":
        break

    try:
        products = get_products()

        
        if any(word in user_input.lower() for word in
               ["promotion plan", "plan promotions", "recommend promotions"]):
            plan = generate_promotion_plan(products)

            print("\n--- Promotion Plan ---")
            for item in plan:
                print(
                    f"\nProduct: {item['product']}"
                    f"\nPromotion duration: {item['duration_days']} days"
                    f"\nStock: {item['stock']}"
                    f"\nRecommended discount: "
                    f"{item['recommended_discount_percent']}%"
                    f"\nPromotional price: ₹{item['promotional_price']}"
                    f"\nCompetitor price: ₹{item['competitor_price']}"
                    f"\nProfit per unit: ₹{item['profit_per_unit']}"
                    f"\nMargin after discount: "
                    f"{item['margin_after_discount_percent']}%"
                    f"\nAt or below competitor price: "
                    f"{item['matches_competitor_price']}"
                )
            print()
            continue

        
        question = user_input.lower()

        if "highest stock" in question or "most stock" in question:
            product = max(products, key=lambda p: p["stock"])
            print(
                f"\nAI: {product['product']} has the highest stock "
                f"with {product['stock']} units.\n"
            )
            continue


        if any(word in user_input.lower() for word in
               ["show", "list", "highest stock", "profit margin",
                "discount", "promotion", "promote", "recommend"]):
            show_products(products)


        prompt = (
            f"Minimum profit margin: {MIN_MARGIN * 100}%\n"
            f"Verified product analysis: {products}\n\n"
            f"User question: {user_input}"
        )

        response = requests.post(
            URL,
            json={
                "model": MODEL,
                "messages": messages + [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            },
            timeout=300
        )

        response.raise_for_status()
        answer = response.json()["message"]["content"]

        print(f"\nAI: {answer}\n")

        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": answer})

    except Exception as error:
        print(f"Error: {error}\n")
