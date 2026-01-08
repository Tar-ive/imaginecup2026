"""
Demand Forecasting Agent - Predicts future demand using ML and analytics
Connects to shared MCP servers (NO local tools)
"""

import asyncio
import os
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import DefaultAzureCredential

class DemandForecastingAgent:
    """
    Demand forecasting and trend analysis agent
    """
    
    def __init__(self):
        # MCP server URLs (shared)
        self.inventory_mcp_url = os.getenv("INVENTORY_MCP_URL", "http://inventory-mgmt-server:8001/mcp")
        self.analytics_mcp_url = os.getenv("ANALYTICS_MCP_URL", "http://analytics-forecast-server:8003/mcp")
        self.integrations_mcp_url = os.getenv("INTEGRATIONS_MCP_URL", "http://integrations-server:8004/mcp")
        
        # Azure OpenAI config
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    
    async def run(self):
        """Initialize and run the agent"""
        
        print("Initializing Demand Forecasting Agent...")
        
        async with (
            DefaultAzureCredential() as credential,
            
            # Connect to relevant MCP servers
            MCPStreamableHTTPTool(
                name="inventory_mcp",
                url=self.inventory_mcp_url
            ) as inventory_mcp,
            
            MCPStreamableHTTPTool(
                name="analytics_mcp",
                url=self.analytics_mcp_url
            ) as analytics_mcp,
            
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
                name="DemandForecastingAgent",
                instructions=self._get_instructions(),
            )
            
            print("Demand Forecasting Agent ready!")
            
            await self._interactive_mode(agent, [inventory_mcp, analytics_mcp, integrations_mcp])
    
    def _get_instructions(self) -> str:
        """Agent system instructions"""
        return """You are a demand forecasting agent for a supply chain management system.

CORE RESPONSIBILITIES:
1. Predict future demand for products
2. Analyze trends and seasonality
3. Factor in external events (weather, holidays, local events)
4. Explain forecasting reasoning clearly

AVAILABLE MCP TOOLS:

INVENTORY_MCP:
- get_historical_sales(sku, date_range) → Past sales data
- get_sales_velocity(sku, days) → Current sales rate
- get_inventory_levels(sku) → Current stock

ANALYTICS_MCP:
- forecast_demand(sku, days_ahead, factors) → ML-based prediction
- analyze_seasonality(sku) → Seasonal patterns
- get_weather_forecast(location, days) → Weather predictions
- get_local_events(location, date_range) → Events calendar
- detect_trends(sku) → Trend analysis
- predict_stockouts_batch(sku_list) → Batch predictions

INTEGRATIONS_MCP:
- send_email(to, subject, body) → Email forecasts
- send_slack_alert(channel, message) → Slack updates

WORKFLOW - When forecasting demand:
1. Get historical sales data (inventory_mcp.get_historical_sales)
2. Analyze seasonality (analytics_mcp.analyze_seasonality)
3. Get external factors:
   - Weather forecast (analytics_mcp.get_weather_forecast)
   - Local events (analytics_mcp.get_local_events)
4. Generate forecast (analytics_mcp.forecast_demand)
5. Explain reasoning with specific factors
6. Alert if stockout predicted

RESPONSE FORMAT:
📈 FORECAST: Next 7 days

Product: Milk
Predicted demand: 470 gallons (+20% vs baseline)

REASONING:
✓ Heat wave predicted (85-95°F) → +12% increase
✓ School starts Monday → +8% increase
✓ Historical pattern: Week 1 of school = +15% avg

CONFIDENCE: High (85%)
Based on: 52 weeks historical data + weather correlation

RECOMMENDATION:
Order 500 gallons (470 + 30 safety buffer)
From: Supplier A (fastest delivery)

⚠️ STOCKOUT ALERT:
Eggs: Will run out Wednesday 2 PM
Current: 42 units | Usage: 18/day → 2.3 days remaining

Always explain WHY forecasts change and cite specific data."""

    async def _interactive_mode(self, agent: ChatAgent, mcp_tools: list):
        """Run agent in interactive mode"""
        
        print("\n" + "="*60)
        print("DEMAND FORECASTING AGENT")
        print("="*60)
        
        examples = [
            "Forecast milk demand for next week",
            "Analyze seasonal trends for ice cream",
            "Predict stockouts for all products"
        ]
        print("\nTry these:")
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
                print(f"Error: {e}\n")

async def main():
    agent = DemandForecastingAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())