
from llm import generate_with_tools
from tools.financial_tools import get_customer_transactions

response = generate_with_tools(
    prompt="""
    Investigate customer C101.

    Retrieve their transactions for the last 7 days.
    Identify any transactions that deserve further investigation.
    Explain your observations, but in as less tokens as possible.
    Summarize your answer to max one paragraph.
    """,
    
    tools=[get_customer_transactions],
    
    system_instruction="""
    You are a financial crime investigation assistant.

    Use the available tools to retrieve transaction data.
    Never invent transactions or claim that an alert is confirmed
    without sufficient evidence.

    Clearly distinguish observations from suspicions.
    """
)

print("\nFINAL LLM RESPONSE:\n")
print(response)
