
# Retail AI Promotion Planner

An AI-assisted retail promotion planning prototype built with Python,
Streamlit, LangChain, and a locally hosted Qwen model through Ollama.

## Features

- Inventory analysis and competitor price comparison
- Discount calculation with a minimum 20% profit margin
- Budget-constrained promotion selection
- Weekend promotion calendar
- Manually configured Dasara and Diwali demo dates
- Illustrative customer segments
- AI assistant with tool calling
- Promotion plan CSV download

## Requirements

- Python 3.11+
- Ollama
- Qwen model: `qwen2.5:1.5b`

## Setup

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Download the model if it is not already installed:

```bash
ollama pull qwen2.5:1.5b
```

Run the application:

```bash
streamlit run app.py
```

## Data and assumptions

- `products.csv` contains sample inventory and pricing data.
- The 5% marketing-cost estimate is an illustrative demo assumption.
- Customer segments are examples, not actual customer data.
- Dasara and Diwali dates are manually configured for the 2026 demo.
- The application proposes promotions; it does not launch campaigns.
