
import csv
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage

st.set_page_config(
    page_title="Retail AI Promotion Planner",
    page_icon="🛍️",
    layout="wide"
)

CSV_FILE = Path(__file__).with_name("products.csv")
MODEL = "qwen2.5:1.5b"
MIN_MARGIN = 0.20
PROMOTION_DAYS = 7

st.title("🛍️ Retail AI Promotion Planner")
st.caption("Inventory-aware promotion planning with verified calculations")


@st.cache_data
def load_products():
    with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def calculate_plan(rows):
    results = []

    for row in rows:
        cost = float(row["cost_price"])
        price = float(row["selling_price"])
        stock = int(row["stock"])
        competitor = float(row["competitor_price"])

        if price <= 0 or cost < 0 or competitor < 0 or stock < 0:
            raise ValueError(f"Invalid product data: {row['product']}")

        max_discount = max(
            0, (price - cost / (1 - MIN_MARGIN)) / price * 100
        )
        competitor_discount = max(
            0, (price - competitor) / price * 100
        )
        discount = min(max_discount, competitor_discount)
        promo_price = price * (1 - discount / 100)
        margin = (promo_price - cost) / promo_price * 100

        results.append({
            "Product": row["product"],
            "Stock": stock,
            "Cost Price (₹)": round(cost, 2),
            "Selling Price (₹)": round(price, 2),
            "Competitor Price (₹)": round(competitor, 2),
            "Discount (%)": round(discount, 2),
            "Promo Price (₹)": round(promo_price, 2),
            "Margin After Discount (%)": round(margin, 2),
            "Duration (days)": PROMOTION_DAYS
        })

    return sorted(results, key=lambda x: x["Stock"], reverse=True)


def make_budget_plan(plan, budget):
    selected = []
    remaining = float(budget)

    for item in plan:
        # DEMO ASSUMPTION: marketing costs 5% of promotional value
        estimated_cost = (
            item["Stock"] * item["Promo Price (₹)"] * 0.05
        )

        if estimated_cost <= remaining:
            selected.append({
                **item,
                "Estimated Marketing Cost (₹)": round(estimated_cost, 2)
            })
            remaining -= estimated_cost

    return selected, round(remaining, 2)



def get_calendar():
    today = date.today()
    end = today + timedelta(days=30)
    events = []
    current = today

    # Weekend opportunities
    while current <= end:
        if current.weekday() in (5, 6):
            events.append({
                "Date": current.isoformat(),
                "Event": "Saturday" if current.weekday() == 5 else "Sunday",
                "Type": "Weekend opportunity"
            })
        current += timedelta(days=1)

    # Manually configured festival dates for the 2026 demo.
    # Update these dates when preparing the demo for another year.
    festival_dates = [
        (date(2026, 10, 20), "Dasara"),
        (date(2026, 11, 8), "Diwali")
    ]

    for holiday_date, name in festival_dates:
        if today <= holiday_date <= end:
            events.append({
                "Date": holiday_date.isoformat(),
                "Event": name,
                "Type": "Festival promotion opportunity (demo date)"
            })

    events.sort(key=lambda event: event["Date"])

    return events, "Using manually configured Dasara and Diwali dates for 2026"


SEGMENTS = [
    {
        "Segment": "Budget-conscious shoppers",
        "Strategy": "Highlight affordable prices and percentage discounts"
    },
    {
        "Segment": "Frequent buyers",
        "Strategy": "Consider bundles or loyalty promotions"
    },
    {
        "Segment": "Electronics enthusiasts",
        "Strategy": "Highlight product features and competitive pricing"
    }
]


# Agent tools use the same verified calculations as the UI.
@tool
def check_inventory() -> str:
    """Show products ranked by highest stock."""
    return str([
        {"product": p["Product"], "stock": p["Stock"]}
        for p in plan
    ])


@tool
def calculate_safe_discounts() -> str:
    """Show verified discounts and margins for all products."""
    return pd.DataFrame(plan).to_json(orient="records")


@tool
def create_budgeted_promotion_plan(marketing_budget: float) -> str:
    """Select high-stock promotions that fit the supplied marketing budget."""
    selected, remaining = make_budget_plan(plan, marketing_budget)
    return (
        f"Selected promotions: {selected}\n"
        f"Remaining budget: ₹{remaining:.2f}\n"
        "Marketing cost uses the clearly labeled 5% demo assumption."
    )


@tool
def get_promotion_calendar() -> str:
    """Return upcoming weekend opportunities and any retrieved public holidays."""
    return f"Calendar events: {calendar_events}\nHoliday status: {holiday_status}"


@tool
def get_customer_segments() -> str:
    """Return illustrative customer segments and possible strategies."""
    return (
        "These are sample segments, not actual customer data: "
        + str(SEGMENTS)
    )


@tool
def get_product_details(product_name: str) -> str:
    """Look up one specific product by name and return its verified pricing details."""
    matches = [
        item for item in plan
        if item["Product"].strip().casefold()
        == product_name.strip().casefold()
    ]

    if not matches:
        available = ", ".join(item["Product"] for item in plan)
        return f"Product '{product_name}' not found. Available products: {available}"

    return str(matches[0])


TOOLS = [
    check_inventory,
    calculate_safe_discounts,
    create_budgeted_promotion_plan,
    get_promotion_calendar,
    get_customer_segments,
    get_product_details
]


def ask_agent(question, history, budget):
    llm = ChatOllama(model=MODEL, temperature=0)
    agent_llm = llm.bind_tools(TOOLS)

    messages = [
        (
            "system",
            "You are a retail promotion planning agent. Use tools for "
            "inventory, pricing, budget, calendar, and customer-segment "
            "questions. Python calculates prices and margins; do not alter "
            "them. Minimum margin is 20%. The budget cost formula is a demo "
            "assumption, not actual advertising pricing. Customer segments "
            "are illustrative, not real customer data. Do not invent holidays "
            "or claim promotions have been launched. Keep answers concise."
            "When the user asks about one named product, call get_product_details"
            "for that exact product and answer only about it. Do not call the"
            "budgeted promotion tool unless the user asks for a promotion plan"
            "or budget calculation. Never substitute another product."
        )
    ]

    messages.extend(history[-6:])
    messages.append((
        "human",
        f"Marketing budget: ₹{budget:.2f}. User question: {question}"
    ))

    for _ in range(4):
        response = agent_llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return response.content

        for call in response.tool_calls:
            selected_tool = next(
                (item for item in TOOLS if item.name == call["name"]),
                None
            )

            try:
                result = (
                    selected_tool.invoke(call["args"])
                    if selected_tool else "Tool unavailable."
                )
            except Exception as error:
                result = f"Tool error: {error}"

            messages.append(ToolMessage(
                content=str(result),
                tool_call_id=call["id"]
            ))

    return "Agent reached its tool-call limit. Please ask a more specific question."


try:
    products = load_products()
    plan = calculate_plan(products)
    calendar_events, holiday_status = get_calendar()

    st.sidebar.header("Business Rules")
    budget = st.sidebar.number_input(
        "Marketing budget (₹)",
        min_value=0.0,
        value=50000.0,
        step=5000.0
    )
    st.sidebar.metric("Minimum profit margin", "20%")
    st.sidebar.metric("Promotion duration", f"{PROMOTION_DAYS} days")
    st.sidebar.caption("Marketing-cost estimate: 5% demo assumption")

    selected, remaining = make_budget_plan(plan, budget)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products", len(products))
    c2.metric("Units in stock", sum(p["Stock"] for p in plan))
    c3.metric("Budget used (estimate)", f"₹{budget - remaining:,.2f}")
    c4.metric("Budget remaining", f"₹{remaining:,.2f}")

    tab_ai, tab_inventory, tab_promotions, tab_calendar, tab_segments = st.tabs([
        "AI Assistant",
        "Inventory",
        "Promotion Plan",
        "Calendar",
        "Customer Segments"
    ])

    with tab_ai:
        st.subheader("Retail promotion agent")
        st.caption("Ask about inventory, pricing, budgets, timing, or audiences.")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        question = st.chat_input("Ask your promotion planner...")

        if question:
            st.session_state.chat_history.append(
                {"role": "user", "content": question}
            )
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Planning with Qwen..."):
                    try:
                        answer = ask_agent(
                            question,
                            st.session_state.chat_history[:-1],
                            budget
                        )
                        st.markdown(answer)
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": answer}
                        )
                    except Exception as error:
                        st.error(f"Agent error: {error}")
                        st.caption(
                            "Check that Ollama is running and the Qwen model "
                            "is installed."
                        )

    with tab_inventory:
        st.subheader("Current inventory")
        st.dataframe(
            pd.DataFrame(products),
            use_container_width=True,
            hide_index=True
        )
        st.caption("Source: products.csv")

    with tab_promotions:
        st.subheader("Calculated promotion plan")
        st.info(
            "Proposed promotions only; nothing is launched. "
            "The budget estimate assumes a 5% marketing cost."
        )
        st.dataframe(
            pd.DataFrame(selected),
            use_container_width=True,
            hide_index=True
        )
        st.write(f"Unselected products: {len(plan) - len(selected)}")
        st.download_button(
            "Download promotion plan CSV",
            pd.DataFrame(selected).to_csv(index=False),
            file_name="promotion_plan.csv",
            mime="text/csv"
        )

    with tab_calendar:
        st.subheader("Next 30 days")
        st.caption(holiday_status)
        st.dataframe(
            pd.DataFrame(calendar_events),
            use_container_width=True,
            hide_index=True
        )
        st.caption(
            "Weekends are promotion opportunities, not automatically public "
            "holidays. The holiday API may omit regional festivals."
        )

    with tab_segments:
        st.subheader("Illustrative customer segments")
        st.dataframe(
            pd.DataFrame(SEGMENTS),
            use_container_width=True,
            hide_index=True
        )
        st.warning(
            "Sample assumptions only. Connect real customer data before "
            "using these segments for business decisions."
        )

except FileNotFoundError:
    st.error("products.csv must be in the same folder as app.py.")
except (ValueError, KeyError) as error:
    st.error(f"Check the CSV columns and numeric values: {error}")
