from langchain_core.tools import tool

@tool
def calculator(expression: str) -> str:
    """Useful for performing mathematical calculations. Input should be a valid math expression string like '200 * 3'."""
    try:
        return str(eval(expression))
    except Exception as e:
        return "Invalid calculation."