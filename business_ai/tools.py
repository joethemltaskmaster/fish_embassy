from analytics import metrics

# This dictionary maps the tool name the LLM sees to the actual Python function.
TOOL_REGISTRY = {
    "get_sales_summary": metrics.get_sales_summary,
    "get_gross_profit_summary": metrics.get_gross_profit_summary,
    "get_stock_valuation": metrics.get_stock_valuation,
    "get_expiring_batches": metrics.get_expiring_batches,
    "get_low_stock_products": metrics.get_low_stock_products,
    "get_top_selling_products": metrics.get_top_selling_products,
}

# These are the JSON schemas we send to NVIDIA to tell it what tools are available.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": "Calculate total revenue, units sold, and transaction count for a specific date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date", "description": "Start date in YYYY-MM-DD format."},
                    "end_date": {"type": "string", "format": "date", "description": "End date in YYYY-MM-DD format."}
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_gross_profit_summary",
            "description": "Calculate revenue, COGS, gross profit, and gross margin for a specific date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_valuation",
            "description": "Get the current total inventory value and total units in stock.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expiring_batches",
            "description": "Get a list of batches with remaining stock that are expiring soon.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Number of days to look ahead (default is 30)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_stock_products",
            "description": "Get a list of SKUs where the current balance is at or below the reorder level.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_selling_products",
            "description": "Rank products by revenue generated in a specific date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "limit": {"type": "integer", "description": "Number of top products to return (default is 5)."}
                },
                "required": ["start_date", "end_date"]
            }
        }
    }
]