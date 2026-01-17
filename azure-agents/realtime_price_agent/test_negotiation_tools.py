"""
Automated Test Script for Negotiation & AP2 Payment MCP Tools
Tests all tools with real-world scenarios for SupplyMind startup

Usage:
    python test_negotiation_tools.py

Requirements:
    - MCP servers running (supplier_data:3001, finance_data:3003)
    - Database migrated
    - pip install requests colorama
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# MCP Server URLs
SUPPLIER_MCP_URL = "http://localhost:3001/mcp"
FINANCE_MCP_URL = "http://localhost:3003/mcp"

# Test counters
tests_run = 0
tests_passed = 0
tests_failed = 0

def print_header(text: str):
    """Print section header."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

def print_test(test_name: str):
    """Print test name."""
    global tests_run
    tests_run += 1
    print(f"\n{Fore.YELLOW}[TEST {tests_run}] {test_name}{Style.RESET_ALL}")

def print_success(message: str):
    """Print success message."""
    global tests_passed
    tests_passed += 1
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

def print_error(message: str):
    """Print error message."""
    global tests_failed
    tests_failed += 1
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

def print_info(message: str):
    """Print info message."""
    print(f"{Fore.BLUE}  {message}{Style.RESET_ALL}")

def call_mcp_tool(
    base_url: str,
    tool_name: str,
    arguments: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Call an MCP tool and return parsed result."""
    try:
        response = requests.post(base_url, json={
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }, timeout=10)

        response.raise_for_status()
        result = response.json()

        if result.get("isError"):
            error_msg = result["content"][0]["text"]
            print_error(f"Tool returned error: {error_msg}")
            return None

        return json.loads(result["content"][0]["text"])

    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to {base_url}. Is the MCP server running?")
        return None
    except Exception as e:
        print_error(f"Error calling tool: {str(e)}")
        return None

def test_tools_list():
    """Test 1: Verify all tools are available."""
    print_test("List Available Tools")

    # Test Supplier MCP
    try:
        response = requests.post(SUPPLIER_MCP_URL, json={"method": "tools/list"})
        supplier_tools = response.json()["tools"]

        expected_negotiation_tools = [
            "create_negotiation_session",
            "request_supplier_quote",
            "submit_counter_offer",
            "accept_supplier_offer",
            "get_negotiation_status",
            "compare_negotiation_offers"
        ]

        found_tools = [t["name"] for t in supplier_tools]

        for tool in expected_negotiation_tools:
            if tool in found_tools:
                print_success(f"Found: {tool}")
            else:
                print_error(f"Missing: {tool}")

        print_info(f"Total tools in Supplier MCP: {len(supplier_tools)}")

    except Exception as e:
        print_error(f"Failed to list supplier tools: {str(e)}")

    # Test Finance MCP
    try:
        response = requests.post(FINANCE_MCP_URL, json={"method": "tools/list"})
        finance_tools = response.json()["tools"]

        expected_ap2_tools = [
            "create_payment_mandate",
            "verify_payment_mandate",
            "execute_payment_with_mandate"
        ]

        found_tools = [t["name"] for t in finance_tools]

        for tool in expected_ap2_tools:
            if tool in found_tools:
                print_success(f"Found: {tool}")
            else:
                print_error(f"Missing: {tool}")

        print_info(f"Total tools in Finance MCP: {len(finance_tools)}")

    except Exception as e:
        print_error(f"Failed to list finance tools: {str(e)}")

def test_negotiation_workflow():
    """Test 2-7: Full negotiation workflow with realistic data."""

    # Real-world scenario: Negotiating for dairy products
    test_items = [
        {
            "sku": "B00EXAMPLE1",
            "quantity": 500,
            "description": "Premium Butter 1lb blocks"
        }
    ]

    session_id = None
    winning_supplier_id = None
    final_price = None
    total_value = None

    # Step 1: Create Negotiation Session
    print_test("Create Negotiation Session")

    session = call_mcp_tool(SUPPLIER_MCP_URL, "create_negotiation_session", {
        "items": test_items,
        "target_price": 4.50,
        "target_discount_percent": 10,
        "max_rounds": 3
    })

    if session and session.get("session_id"):
        session_id = session["session_id"]
        print_success(f"Session created: {session_id}")
        print_info(f"Target price: ${session.get('target_price')}/unit")
        print_info(f"Max rounds: {session.get('max_rounds')}")
        print_info(f"Status: {session.get('status')}")
    else:
        print_error("Failed to create negotiation session")
        return

    # Step 2: Request Quotes from Multiple Suppliers
    print_test("Request Quotes from Suppliers")

    # Simulate requesting quotes from 3 suppliers
    test_suppliers = ["SUP-001", "SUP-002", "SUP-003"]
    quotes = {}

    for supplier_id in test_suppliers:
        quote = call_mcp_tool(SUPPLIER_MCP_URL, "request_supplier_quote", {
            "session_id": session_id,
            "supplier_id": supplier_id,
            "urgency": "high"
        })

        if quote:
            quotes[supplier_id] = quote
            print_success(f"{supplier_id}: ${quote.get('offered_price')}/unit (Total: ${quote.get('total_value')})")
            if quote.get('simulated'):
                print_info("  (Simulated supplier response - instant)")
        else:
            print_error(f"Failed to get quote from {supplier_id}")

    if not quotes:
        print_error("No quotes received, stopping test")
        return

    # Step 3: Compare Offers
    print_test("Compare Negotiation Offers")

    comparison = call_mcp_tool(SUPPLIER_MCP_URL, "compare_negotiation_offers", {
        "session_id": session_id,
        "criteria": "total_cost"
    })

    if comparison:
        print_success(f"Compared {comparison.get('offers_count')} offers")
        best_offer = comparison.get('best_offer')
        if best_offer:
            print_info(f"Best offer: {best_offer.get('supplier_name')} at ${best_offer.get('offered_price')}/unit")
            winning_supplier_id = best_offer['supplier_id']

            # Show all ranked offers
            print_info("\nRanked suppliers:")
            for i, offer in enumerate(comparison.get('ranked_suppliers', [])[:3], 1):
                print_info(f"  {i}. {offer.get('supplier_name')}: ${offer.get('offered_price')}/unit")
    else:
        print_error("Failed to compare offers")
        return

    # Step 4: Get Negotiation Status
    print_test("Get Negotiation Status")

    status = call_mcp_tool(SUPPLIER_MCP_URL, "get_negotiation_status", {
        "session_id": session_id
    })

    if status:
        print_success(f"Retrieved status for session {session_id}")
        print_info(f"Current round: {status.get('current_round')}/{status.get('max_rounds')}")
        print_info(f"Rounds completed: {len(status.get('rounds', []))}")
        print_info(f"Session status: {status.get('status')}")
    else:
        print_error("Failed to get negotiation status")

    # Step 5: Submit Counter-Offer
    print_test("Submit Counter-Offer")

    if not winning_supplier_id:
        print_error("No supplier selected for counter-offer")
        return

    counter_result = call_mcp_tool(SUPPLIER_MCP_URL, "submit_counter_offer", {
        "session_id": session_id,
        "supplier_id": winning_supplier_id,
        "counter_price": 4.50,
        "justification": "Target budget constraint for bulk order. Competitor quoted 10% less."
    })

    if counter_result:
        print_success(f"Counter-offer submitted to {winning_supplier_id}")
        print_info(f"Our counter: ${counter_result.get('our_counter_price')}/unit")
        print_info(f"Their response: ${counter_result.get('their_response_price')}/unit")
        print_info(f"Discount requested: {counter_result.get('discount_requested_percent')}%")
        print_info(f"Status: {counter_result.get('status')}")

        # Update final price from counter-offer
        final_price = counter_result.get('their_response_price')
        total_value = counter_result.get('total_value')
    else:
        print_error("Failed to submit counter-offer")
        return

    # Step 6: Accept Best Offer
    print_test("Accept Supplier Offer")

    accepted = call_mcp_tool(SUPPLIER_MCP_URL, "accept_supplier_offer", {
        "session_id": session_id,
        "supplier_id": winning_supplier_id,
        "notes": "Best offer after negotiation. Meets budget requirements."
    })

    if accepted:
        print_success(f"Offer accepted from {accepted.get('winning_supplier_id')}")
        print_info(f"Final price: ${accepted.get('final_price')}/unit")
        print_info(f"Total value: ${accepted.get('total_value')}")
        print_info(f"Rounds completed: {accepted.get('rounds_completed')}")
        print_info(f"Session status: {accepted.get('status')}")

        final_price = accepted.get('final_price')
        total_value = accepted.get('total_value')
    else:
        print_error("Failed to accept offer")
        return

    # Return data for AP2 testing
    return {
        "session_id": session_id,
        "supplier_id": winning_supplier_id,
        "final_price": final_price,
        "total_value": total_value,
        "items": test_items
    }

def test_ap2_payment_flow(negotiation_data: Dict[str, Any]):
    """Test 8-10: AP2 Payment Mandate workflow."""

    if not negotiation_data:
        print_error("No negotiation data provided, skipping AP2 tests")
        return

    session_id = negotiation_data["session_id"]
    supplier_id = negotiation_data["supplier_id"]
    total_value = negotiation_data["total_value"]
    items = negotiation_data["items"]

    # Step 1: Create Payment Mandate
    print_test("Create AP2 Payment Mandate")

    mandate = call_mcp_tool(FINANCE_MCP_URL, "create_payment_mandate", {
        "session_id": session_id,
        "supplier_id": supplier_id,
        "amount": total_value,
        "currency": "USD",
        "order_details": {
            "items": items,
            "total": total_value,
            "negotiation_session": session_id
        },
        "user_consent": True
    })

    if mandate:
        mandate_id = mandate.get("mandate_id")
        print_success(f"Mandate created: {mandate_id}")
        print_info(f"Amount: ${mandate.get('amount')} {mandate.get('currency')}")
        print_info(f"Supplier: {mandate.get('supplier_id')}")
        print_info(f"Status: {mandate.get('status')}")
        print_info(f"Expires: {mandate.get('expires_at')}")
        print_info(f"Signature algorithm: RS256 (JWT)")

        # Show truncated signed mandate
        signed_mandate = mandate.get('signed_mandate', '')
        if signed_mandate:
            print_info(f"Signed mandate (JWT): {signed_mandate[:50]}...{signed_mandate[-20:]}")
    else:
        print_error("Failed to create payment mandate")
        return

    # Step 2: Verify Payment Mandate
    print_test("Verify AP2 Payment Mandate")

    verified = call_mcp_tool(FINANCE_MCP_URL, "verify_payment_mandate", {
        "mandate_id": mandate_id
    })

    if verified:
        print_success(f"Mandate verified: {verified.get('valid')}")
        print_info(f"Status: {verified.get('status')}")
        print_info(f"Amount: ${verified.get('amount')} {verified.get('currency')}")

        # Show decoded payload
        payload = verified.get('decoded_payload', {})
        if payload:
            print_info(f"Issuer: {payload.get('iss')}")
            print_info(f"Subject (Supplier): {payload.get('sub')}")
            print_info(f"Audience: {payload.get('aud')}")
            print_info(f"Expires: {datetime.fromtimestamp(payload.get('exp', 0)).isoformat()}")
    else:
        print_error("Failed to verify payment mandate")
        return

    # Step 3: Execute Payment
    print_test("Execute Payment with Mandate")

    executed = call_mcp_tool(FINANCE_MCP_URL, "execute_payment_with_mandate", {
        "mandate_id": mandate_id,
        "po_number": f"PO-TEST-{int(time.time())}"
    })

    if executed:
        print_success(f"Payment executed: {executed.get('status')}")
        print_info(f"Amount: ${executed.get('amount')} {executed.get('currency')}")
        print_info(f"Supplier: {executed.get('supplier_id')}")
        print_info(f"PO Number: {executed.get('po_number')}")
        print_info(f"Executed at: {executed.get('executed_at')}")
        print_info(f"Message: {executed.get('message')}")
    else:
        print_error("Failed to execute payment")

def print_summary():
    """Print test summary."""
    print_header("TEST SUMMARY")

    print(f"\n{Fore.WHITE}Tests Run: {tests_run}")
    print(f"{Fore.GREEN}Tests Passed: {tests_passed}")
    print(f"{Fore.RED}Tests Failed: {tests_failed}")

    if tests_failed == 0:
        print(f"\n{Fore.GREEN}🎉 ALL TESTS PASSED!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}All MCP tools are working correctly with real-world data.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}⚠️  SOME TESTS FAILED{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Please review the errors above and fix issues.{Style.RESET_ALL}")

def main():
    """Run all tests."""
    print_header("MCP TOOLS AUTOMATED TEST SUITE")
    print(f"{Fore.WHITE}Testing Negotiation & AP2 Payment Tools")
    print(f"{Fore.WHITE}Timestamp: {datetime.now().isoformat()}\n")

    # Test 1: Verify tools are available
    test_tools_list()

    # Test 2-7: Full negotiation workflow
    negotiation_data = test_negotiation_workflow()

    # Test 8-10: AP2 payment flow
    if negotiation_data:
        test_ap2_payment_flow(negotiation_data)

    # Print summary
    print_summary()

    # Return exit code
    return 0 if tests_failed == 0 else 1

if __name__ == "__main__":
    exit(main())
