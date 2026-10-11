
import csv
import requests
from pathlib import Path
from datetime import date, timedelta

from langchain_ollama import ChatOllama
from langchain_core.tools import tool

CSV_FILE = Path(__file__).with_name("products.csv")
MIN_MARGIN = 0.20


def load_products():
    with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


@tool
def check_inventory() -> str:
    """Return products sorted by highest stock first."""
    products = sorted(
        load_products(),
        key=lambda p: int(p["stock"]),
        reverse=True
    )
    return "\n".join(
        f"{p['product']}: stock={p['stock']}, "
        f"selling_price=₹{p['selling_price']}, "
        f"cost_price=₹{p['cost_price']}, "
        f"competitor_price=₹{p['competitor_price']}"
        for p in products
    )


@tool
def calculate_safe_discounts() -> str:
    """Calculate competitor-matching discounts while preserving minimum margin."""
    results = []

    for p in load_products():
        cost = float(p["cost_price"])
        price = float(p["selling_price"])
        competitor = float(p["competitor_price"])

        if price <= 0 or cost < 0 or competitor < 0:
            results.append(f"{p['product']}: invalid pricing data")
            continue

        max_discount = max(
            0, (price - cost / (1 - MIN_MARGIN)) / price * 100
        )
        competitor_discount = max(
            0, (price - competitor) / price * 100
        )
        discount = min(max_discount, competitor_discount)
        promo_price = price * (1 - discount / 100)
        margin = (promo_price - cost) / promo_price * 100

        results.append(
            f"{p['product']}: discount={discount:.2f}%, "
            f"promo_price=₹{promo_price:.2f}, "
            f"margin_after_discount={margin:.2f}%"
        )

    return "\n".join(results)


@tool
def recommend_products() -> str:
    """Rank products by stock and return safe promotion calculations."""
    inventory = check_inventory.invoke({})
    pricing = calculate_safe_discounts.invoke({})

    return (
        "Inventory (highest stock first):\n"
        f"{inventory}\n\n"
        "Verified pricing:\n"
        f"{pricing}\n\n"
        "Prioritize high-stock products, but preserve the 20% minimum margin."
    )


@tool
def create_budgeted_promotion_plan(
    marketing_budget: float = 50000
) -> str:
    """Create a promotion plan prioritizing high stock within the marketing budget."""
    products = sorted(
        load_products(),
        key=lambda p: int(p["stock"]),
        reverse=True
    )

    plan = []
    remaining_budget = max(0, float(marketing_budget))

    for p in products:
        stock = int(p["stock"])
        price = float(p["selling_price"])
        cost = float(p["cost_price"])
        competitor = float(p["competitor_price"])

        if stock <= 0 or price <= 0 or cost < 0 or competitor < 0:
            continue

        max_discount = max(
            0, (price - cost / (1 - MIN_MARGIN)) / price * 100
        )
        competitor_discount = max(
            0, (price - competitor) / price * 100
        )
        discount = min(max_discount, competitor_discount)
        promo_price = price * (1 - discount / 100)

        # Demo marketing cost: 5% of the promotional value of selected stock.
        estimated_cost = stock * promo_price * 0.05

        if estimated_cost <= remaining_budget:
            remaining_budget -= estimated_cost
            plan.append(
                f"{p['product']}: stock={stock}, "
                f"discount={discount:.2f}%, "
                f"promo_price=₹{promo_price:.2f}, "
                f"margin={(promo_price-cost)/promo_price*100:.2f}%, "
                f"estimated_marketing_cost=₹{estimated_cost:.2f}"
            )

    return (
        "\n".join(plan) if plan
        else "No products fit the available marketing budget."
    ) + f"\nRemaining budget: ₹{remaining_budget:.2f}"


@tool
def get_upcoming_holidays(country_code: str = "IN") -> str:
    """Get public holidays in the next 90 days for promotion planning."""
    today = date.today()
    end_date = today + timedelta(days=90)
    holidays = []

    for year in range(today.year, end_date.year + 1):
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            yearly_holidays = response.json()

            for holiday in yearly_holidays:
                holiday_date = date.fromisoformat(holiday["date"])

                if today <= holiday_date <= end_date:
                    holidays.append(
                        f"{holiday['date']}: {holiday['localName']}"
                    )

        except (requests.RequestException, ValueError, KeyError):
            continue

    if not holidays:
        return (
            "No holidays retrieved. The API may be unavailable or "
            "no holidays were returned. Do not invent holiday dates."
        )

    return "Upcoming public holidays:\n" + "\n".join(sorted(set(holidays)))

@tool
def get_upcoming_weekends() -> str:
    """Find Saturdays and Sundays in the next 30 days."""
    today = date.today()
    end_date = today + timedelta(days=30)
    days = []
    current = today

    while current <= end_date:
        if current.weekday() == 5:
            days.append(f"{current.isoformat()}: Saturday")
        elif current.weekday() == 6:
            days.append(f"{current.isoformat()}: Sunday")

        current += timedelta(days=1)

    return "Upcoming weekend promotion opportunities:\n" + "\n".join(days)


@tool
def get_promotion_calendar() -> str:
    """Find weekends and available Indian public holidays over the next 30 days."""
    from datetime import date, timedelta
    import requests

    today = date.today()
    end_date = today + timedelta(days=30)
    events = []

    # Weekend opportunities
    current = today
    while current <= end_date:
        if current.weekday() == 5:
            events.append(f"{current.isoformat()} | Saturday | Weekend opportunity")
        elif current.weekday() == 6:
            events.append(f"{current.isoformat()} | Sunday | Weekend opportunity")
        current += timedelta(days=1)

    # Public holidays from Nager.Date
    holiday_data_available = False

    for year in range(today.year, end_date.year + 1):
        url = f"https://date.nager.at/api/v4/Holidays/IN/{year}"

        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 204:
                continue

            response.raise_for_status()
            holidays = response.json()

            if not isinstance(holidays, list):
                continue

            for holiday in holidays:
                holiday_date = date.fromisoformat(holiday["date"])

                if today <= holiday_date <= end_date:
                    events.append(
                        f"{holiday_date.isoformat()} | PUBLIC HOLIDAY | "
                        f"{holiday.get('name', 'Unnamed holiday')}"
                    )
                    holiday_data_available = True

        except (requests.RequestException, ValueError, KeyError) as error:
            print(f"Holiday lookup issue: {error}")

    events.sort()

    result = "\n".join(events)

    if not holiday_data_available:
        result += (
            "\nPublic holiday data unavailable for this period. "
            "Do not invent holidays; weekends are still listed."
        )

    return result


from langchain_core.tools import tool

@tool
def get_customer_segments() -> str:
    """Return demo customer segments and suitable promotion strategies."""
    return """DEMO CUSTOMER SEGMENTS (sample assumptions, not real customer data):
1. Budget-conscious shoppers:
   Strategy: Highlight affordable prices and percentage discounts.
2. Frequent buyers:
   Strategy: Offer bundles or loyalty promotions.
3. Electronics enthusiasts:
   Strategy: Highlight product features and competitive pricing.

These are illustrative segments. Actual customer data has not been provided."""



tools = [check_inventory, calculate_safe_discounts, recommend_products, create_budgeted_promotion_plan, get_promotion_calendar, get_customer_segments]

llm = ChatOllama(model="qwen2.5:1.5b", temperature=0)
llm_with_tools = llm.bind_tools(tools)

messages = [
    (
        "system",
        "You are a retail promotion agent. Use tools for inventory and "
        "pricing questions. Base recommendations on tool results. "
        "Never claim a promotion was launched."
    ),
    (
    "human",
    "Create a budgeted promotion plan using the "
    "create_budgeted_promotion_plan tool with a "
    "marketing budget of ₹50000. Show the estimated "
    "marketing cost and remaining budget."
)
]

# Allow up to 4 tool-calling rounds.
for _ in range(4):
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    if not response.tool_calls:
        print("\nFinal agent recommendation:")
        print(response.content)
        break

    for call in response.tool_calls:
        selected_tool = next(
            (t for t in tools if t.name == call["name"]), None
        )

        if selected_tool is None:
            result = "Error: requested tool is unavailable."
        else:
            try:
                result = selected_tool.invoke(call["args"])
            except Exception as error:
                result = f"Tool error: {error}"

        print(f"\nTool executed: {call['name']}")
        print(result)

        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": str(result)
        })
else:
    print("\nAgent stopped after the tool-call limit.")
    print("Review the tool outputs above.")


print(get_upcoming_holidays.invoke({"country_code": "IN"}))

print(get_upcoming_weekends.invoke({}))
print("\n--- PROMOTION CALENDAR TEST ---")
print(get_promotion_calendar.invoke({}))
print(get_customer_segments.invoke({}))