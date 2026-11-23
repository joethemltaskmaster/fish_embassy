import json
import os
from datetime import date, timedelta
from django.utils import timezone  # <-- Add this import
from openai import OpenAI
from .tools import TOOL_REGISTRY, TOOL_SCHEMAS

api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    raise ValueError("NVIDIA_API_KEY is missing from your .env file.")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key
)

MODEL = "meta/llama-3.3-70b-instruct"


def get_system_prompt() -> str:
    """Dynamically builds the prompt with the current real-time date."""
    today = timezone.localdate()
    day_of_week = today.strftime("%A")

    return f"""You are the RAO Fish Embassy Business Intelligence Assistant. 
You answer questions for the Super Admin.
You have access to tools that query the database for verified metrics.
ALWAYS use the provided tools to fetch data. Never guess or invent numbers.

CRITICAL CONTEXT:
- Today's date is {today.isoformat()} ({day_of_week}).
- The business timezone is Africa/Lagos.
- Use this exact date to calculate relative timeframes. For example:
  - "last week" means the 7 days prior to today.
  - "this month" means from the 1st of the current month to today.
  - "yesterday" means {(today - timedelta(days=1)).isoformat()}.

If a user asks for data without specifying dates, assume they mean the last 30 days.
When you receive tool results, explain them clearly and highlight important trends."""


def process_chat_message(user_message: str, chat_history: list) -> dict:
    """Handles the LLM interaction, tool calling, and final response generation."""

    # 1. Inject the dynamic system prompt
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_message})

    try:
        # First call: Ask the LLM what to do
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=1024
        )
    except Exception as e:
        return {"error": f"AI Provider Error: {str(e)}"}

    response_message = response.choices[0].message

    # Check if the LLM decided to call a tool
    if response_message.tool_calls:
        tool_call = response_message.tool_calls[0]
        function_name = tool_call.function.name

        try:
            arguments = json.loads(tool_call.function.arguments)

            # Convert dates if passed as strings
            if 'start_date' in arguments:
                arguments['start_date'] = date.fromisoformat(arguments['start_date'])
            if 'end_date' in arguments:
                arguments['end_date'] = date.fromisoformat(arguments['end_date'])

            # Execute Analytics
            func = TOOL_REGISTRY[function_name]
            tool_result = func(**arguments)

            # Convert Decimals to strings for JSON serialization
            serializable_result = json.loads(json.dumps(tool_result, default=str))

        except Exception as e:
            return {"error": f"Analytics execution failed: {str(e)}"}

        # Second call: Generate the text response based on the data
        messages.append(response_message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": function_name,
            "content": json.dumps(serializable_result)
        })

        try:
            second_response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.1,
                max_tokens=1024
            )
            return {
                "reply": second_response.choices[0].message.content,
                "tool_used": function_name,
                "tool_data": serializable_result
            }
        except Exception as e:
            return {"error": f"AI explanation error: {str(e)}"}

    else:
        return {
            "reply": response_message.content,
            "tool_used": None,
            "tool_data": None
        }