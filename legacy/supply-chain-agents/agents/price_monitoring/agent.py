"""
Price Monitoring Agent - Real-time price detection and supplier optimization
Connects to shared MCP servers (NO local tools)
"""

import asyncio
import os
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import DefaultAzureCredential

class PriceMonitoringAgent:
    """
    Real-time price monitoring and supplier optimization agent
    """
    
    def __init__(self):
        # MCP server URLs (shared across all agents)
        self.supplier_mcp_url = os.getenv("SUPPLIER_MCP_URL", "http://supplier-data-server:8000/mcp")
        self.inventory_mcp_url = os.getenv("INVENTORY_MCP_URL", "http://inventory-mgmt-server:8001/mcp")
        self.finance_mcp_url = os.getenv("FINANCE_MCP_URL", "http://finance-data-server:8002/mcp")
        self.integrations_mcp_url = os.getenv("INTEGRATIONS_MCP_URL", "http://integrations-server:8004/mcp")
        
        # Azure OpenAI config
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        
        # Agent properties
        self.optimization_criteria = {
            "price": 0.50,
            "delivery": 0.30,
            "quality": 0.20
        }
    
    async def run(self):
        """Initialize and run the agent"""
        
        print("💰 Initializing Price Monitoring Agent...")
        
        async with (
            DefaultAzureCredential() as credential,
            
            # Connect to shared MCP servers
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
                name="PriceMonitoringAgent",
                instructions=self._get_instructions(),
            )
            
            print("Price Monitoring Agent ready!")
            print(f"   Connected to {len([supplier_mcp, inventory_mcp, finance_mcp, integrations_mcp])} MCP servers")
            
            await self._interactive_mode(agent, [supplier_mcp, inventory_mcp, finance_mcp, integrations_mcp])
    
    def _get_instructions(self) -> str:
        """Agent system instructions"""
        return """You are a real-time price monitoring agent for a supply chain management system.

CORE RESPONSIBILITIES:
1. Detect supplier price changes instantly
2. Find "best place to buy" through multi-supplier optimization
3. Calculate impact on product margins
4. Generate actionable recommendations

AVAILABLE MCP TOOLS:
You have access to 4 shared MCP servers:

SUPPLIER_MCP (supplier-data-server):
- get_supplier_prices(supplier_name, sku_list) → Current prices
- fuzzy_match_product(sku, suppliers) → Match SKUs across suppliers
- get_supplier_reliability(supplier_name) → Quality/delivery metrics
- compare_suppliers(sku, criteria) → Rank by price/delivery/quality
- get_alternative_suppliers(sku) → Backup suppliers

INVENTORY_MCP (inventory-mgmt-server):
- get_product_details(sku) → Product info, BOM, recipe
- get_inventory_levels(sku) → Current stock
- get_sales_velocity(sku) → Usage rate

FINANCE_MCP (finance-data-server):
- calculate_margin_impact(price_changes, products) → Profit impact
- get_product_cost_structure(sku) → Full cost breakdown
- convert_currency(amount, from, to) → Currency conversion

INTEGRATIONS_MCP (integrations-server):
- parse_email_invoice(email_body) → Extract invoice data
- send_email(to, subject, body) → Send notifications
- send_slack_alert(channel, message) → Slack alerts

WORKFLOW - When price change detected:
1. Extract pricing data (use integrations_mcp if from email/PDF)
2. Get affected products (use inventory_mcp.get_product_details)
3. Calculate margin impact (use finance_mcp.calculate_margin_impact)
4. Find alternatives (use supplier_mcp.get_alternative_suppliers)
5. Rank suppliers (use supplier_mcp.compare_suppliers with weights: 50% price, 30% delivery, 20% quality)
6. Generate recommendations with specific numbers
7. Send alerts if critical (margins < 5%)

RESPONSE FORMAT:
✅ Always provide specific numbers and calculations
✅ Show comparison matrix for alternatives
✅ Explain reasoning transparently
✅ Prioritize CRITICAL alerts (margin < 5%)

Example output:
"🚨 CRITICAL: Butter price increased 15% ($3.20 → $3.68/lb)

IMPACT ANALYSIS:
- Steak Frites: Margin dropped 18% → 2% ⚠️ CRITICAL
- Croissants: Margin dropped 25% → 15% ⚠️ WARNING

SUPPLIER COMPARISON:
1. Supplier B: $3.40/lb (saves $0.28) • 2-day delivery • 95% reliability
2. Supplier C: $3.55/lb (saves $0.13) • 1-day delivery • 92% reliability

RECOMMENDATIONS:
Option 1: Switch to Supplier B (saves $140/week, maintains margin at 16%)
Option 2: Raise Steak Frites price by $1.50 (restores 18% margin)
Option 3: Reformulate recipe to use 20% less butter""

Be precise, actionable, and always show your calculations."""

    async def _interactive_mode(self, agent: ChatAgent, mcp_tools: list):
        """Run agent in interactive mode"""
        
        print("\n" + "="*60)
        print("PRICE MONITORING AGENT")
        print("="*60)
        
        examples = [
            "Butter price increased to $3.68/lb (was $3.20)",
            "Find best supplier for 500 lbs flour by Friday",
            "Parse this invoice email: [email content]"
        ]
        print("\n📝 Try these:")
        for i, ex in enumerate(examples, 1):
            print(f"   {i}. {ex}")
        print()
        
        while True:
            try:
                user_input = input("Query: ").strip()
                if not user_input or user_input.lower() in ['exit', 'quit']:
                    break
                
                print("\n🤖 Agent: ", end="", flush=True)
                result = await agent.run(user_input, tools=mcp_tools)
                print(result.text, "\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f" Error: {e}\n")

async def main():
    agent = PriceMonitoringAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())