"""
Automated Ordering Agent - Generates and executes purchase orders
Connects to shared MCP servers (NO local tools)
"""

import asyncio
import os
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import DefaultAzureCredential

class AutomatedOrderingAgent:
    """
    Automated purchase order generation and execution
    """
    
    def __init__(self):
        # MCP server URLs (shared)
        self.supplier_mcp_url = os.getenv("SUPPLIER_MCP_URL", "http://supplier-data-server:8000/mcp")
        self.inventory_mcp_url = os.getenv("INVENTORY_MCP_URL", "http://inventory-mgmt-server:8001/mcp")
        self.finance_mcp_url = os.getenv("FINANCE_MCP_URL", "http://finance-data-server:8002/mcp")
        self.integrations_mcp_url = os.getenv("INTEGRATIONS_MCP_URL", "http://integrations-server:8004/mcp")
        
        # Azure OpenAI config
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    
    async def run(self):
        """Initialize and run the agent"""
        
        print("🛒 Initializing Automated Ordering Agent...")
        
        async with (
            DefaultAzureCredential() as credential,
            
            # Connect to relevant MCP servers
            MCPStreamableHTTPTool(
                name="supplier_mcp",
                url=self.supplier_mcp_url
            ) as supplier_mcp,
            
            MCPStreamableHTTPTool(
                name="inventory_mcp",
                url=self.inventory_mcp_url
            ) as inventory_mcp,
            
            MCPStreamableHTTPTool(
                name="finance_mcp",
                url=self.finance_mcp_url
            ) as finance_mcp,
            
            MCPStreamableHTTPTool(
                name="integrations_mcp",
                url=self.integrations_mcp_url
            ) as integrations_mcp,
            
            AzureOpenAIChatClient(
                endpoint=self.azure_endpoint,
                credential=credential,
                deployment_name=self.deployment_name
            ) as chat_client
        ):
            agent = ChatAgent(
                chat_client=chat_client,
                name="AutomatedOrderingAgent",
                instructions=self._get_instructions(),
            )
            
            print("Automated Ordering Agent ready!")
            
            await self._interactive_mode(agent, [supplier_mcp, inventory_mcp, finance_mcp, integrations_mcp])
    
    def _get_instructions(self) -> str:
        """Agent system instructions"""
        return """You are an automated ordering agent for a supply chain management system.

CORE RESPONSIBILITIES:
1. Generate purchase orders based on inventory needs
2. Optimize supplier selection (price + delivery + quality)
3. Execute orders via EDI, API, or email
4. Adapt to disruptions (delays, stockouts)

AVAILABLE MCP TOOLS:

SUPPLIER_MCP:
- get_supplier_prices(supplier, sku_list) → Current pricing
- compare_suppliers(sku, criteria) → Rank suppliers
- get_supplier_payment_terms(supplier) → Payment terms
- get_supplier_min_order(supplier, sku) → Min order qty

INVENTORY_MCP:
- get_inventory_levels(sku) → Current stock
- predict_stockout(sku) → Days until stockout
- update_inventory(sku, qty, type) → Update stock

FINANCE_MCP:
- get_cash_position() → Available cash
- calculate_payment_terms_value(amount, terms) → NPV calculation
- get_accounts_payable() → Outstanding payments

INTEGRATIONS_MCP:
- send_purchase_order_edi(supplier, order_data) → EDI transmission
- send_purchase_order_api(supplier, order_data) → API order
- send_purchase_order_email(supplier, order_data) → Email order
- send_email(to, subject, body) → Confirmation email

WORKFLOW - When creating order:
1. Check inventory levels (inventory_mcp.get_inventory_levels)
2. Check cash position (finance_mcp.get_cash_position)
3. Get supplier options (supplier_mcp.compare_suppliers)
4. Consider:
   - Price (50% weight)
   - Delivery time (30% weight)
   - Payment terms (20% weight)
5. Respect minimum order quantities
6. Execute order via appropriate channel
7. Update inventory (inventory_mcp.update_inventory)
8. Send confirmation

RESPONSE FORMAT:
🛒 PURCHASE ORDER GENERATED

ORDER DETAILS:
Supplier: Supplier B
Items:
  • Butter: 500 lbs @ $3.40/lb = $1,700
  • Flour: 100 lbs @ $2.45/lb = $245
TOTAL: $1,945
Payment Terms: Net-30
Delivery: Friday 2 PM

SELECTION REASONING:
✓ Supplier B selected over A & C:
  - Price: 2nd best ($3.40 vs $3.25 vs $3.68)
  - Delivery: Fastest (2 days vs 3 days vs 5 days)
  - Reliability: 95% on-time delivery
  - Meets minimum order: $1,945 > $150 minimum

ORDER EXECUTION:
✓ Sent via: EDI (fastest)
✓ Confirmation: PO-2026-001
✓ Tracking: Will receive ASN 856 when shipped

INVENTORY UPDATE:
✓ Expected arrival: Jan 7, 2026
✓ System updated: Butter pending +500 lbs

Always optimize total cost of ownership, not just unit price."""

    async def _interactive_mode(self, agent: ChatAgent, mcp_tools: list):
        """Run agent in interactive mode"""
        
        print("\n" + "="*60)
        print("AUTOMATED ORDERING AGENT")
        print("="*60)
        
        examples = [
            "Order 500 lbs butter from best supplier",
            "Generate orders for all low-stock items",
            "Place emergency order for eggs (stockout predicted)"
        ]
        print("\nTry these:")
        for i, ex in enumerate(examples, 1):
            print(f"   {i}. {ex}")
        print()
        
        while True:
            try:
                user_input = input("🛒 Query: ").strip()
                if not user_input or user_input.lower() in ['exit', 'quit']:
                    break
                
                print("\n🤖 Agent: ", end="", flush=True)
                result = await agent.run(user_input, tools=mcp_tools)
                print(result.text, "\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}\n")

async def main():
    agent = AutomatedOrderingAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())