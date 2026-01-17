"""
Orchestrator Agent - Coordinates all supply chain agents
Routes queries to appropriate specialized agents
"""

import asyncio
import os
from typing import Dict, List
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import DefaultAzureCredential

class OrchestratorAgent:
    """
    Main orchestrator that routes queries to specialized agents
    Acts as the entry point for the supply chain system
    """
    
    def __init__(self):
        # Agent URLs (in production, these would be service URLs)
        self.price_agent_url = os.getenv("PRICE_AGENT_URL", "http://price-monitoring:8080")
        self.demand_agent_url = os.getenv("DEMAND_AGENT_URL", "http://demand-forecasting:8081")
        self.ordering_agent_url = os.getenv("ORDERING_AGENT_URL", "http://automated-ordering:8082")
        
        # Azure OpenAI config
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    
    async def run(self):
        """Initialize and run the orchestrator"""
        
        print("Initializing Orchestrator Agent...")
        
        async with (
            DefaultAzureCredential() as credential,
            AzureOpenAIChatClient(
                endpoint=self.azure_endpoint,
                credential=credential,
                deployment_name=self.deployment_name
            ) as chat_client
        ):
            agent = ChatAgent(
                chat_client=chat_client,
                name="OrchestratorAgent",
                instructions=self._get_instructions(),
            )
            
            print("Orchestrator initialized!")
            print("\nAvailable Agents:")
            print("   1. Price Monitoring - Price changes, supplier optimization")
            print("   2. Demand Forecasting - Sales predictions, trend analysis")
            print("   3. Automated Ordering - Purchase order generation")
            
            await self._interactive_mode(agent)
    
    def _get_instructions(self) -> str:
        """Orchestrator system instructions"""
        return """You are the Orchestrator Agent for a supply chain management system.
Your role is to analyze user queries and route them to the appropriate specialized agent(s).

AVAILABLE SPECIALIZED AGENTS:

1. PRICE MONITORING AGENT
   Use for: Price changes, supplier optimization, margin analysis, "best place to buy"
   Examples:
   - "Supplier increased butter price by 15%"
   - "Find cheapest supplier for 500 lbs flour"
   - "Analyze margin impact of wheat price increase"

2. DEMAND FORECASTING AGENT
   Use for: Sales predictions, demand forecasting, trend analysis
   Examples:
   - "Predict milk demand for next week"
   - "What's the seasonal trend for ice cream?"
   - "How much should we stock for the holiday season?"

3. AUTOMATED ORDERING AGENT
   Use for: Purchase order generation, order execution, supplier orders
   Examples:
   - "Create purchase order for 100 units of SKU-123"
   - "Place order with Supplier A for butter"
   - "Generate orders based on current inventory levels"

ROUTING LOGIC:
- If query mentions: prices, suppliers, margins, cost → Price Monitoring Agent
- If query mentions: forecast, predict, demand, trends → Demand Forecasting Agent
- If query mentions: order, purchase, buy → Automated Ordering Agent
- If query spans multiple areas, coordinate between agents

Always explain which agent(s) you're routing to and why.
Format responses clearly and provide actionable insights."""

    async def _interactive_mode(self, agent: ChatAgent):
        """Run orchestrator in interactive mode"""
        
        print("\n" + "="*60)
        print("SUPPLY CHAIN ORCHESTRATOR - Interactive Mode")
        print("="*60)
        print("Type your queries below. Type 'exit' to quit.\n")
        
        examples = [
            "Butter price increased 15%, what should we do?",
            "Predict demand for next week",
            "Create order for 500 lbs flour from cheapest supplier"
        ]
        print("Example queries:")
        for i, example in enumerate(examples, 1):
            print(f"   {i}. {example}")
        print()
        
        while True:
            try:
                user_input = input("🔵 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n Goodbye!")
                    break
                
                print("\n🤖 Orchestrator: ", end="", flush=True)
                
                result = await agent.run(user_input)
                
                print(result.text)
                print()
                
            except KeyboardInterrupt:
                print("\n\n Goodbye!")
                break
            except Exception as e:
                print(f"\n Error: {e}\n")

async def main():
    orchestrator = OrchestratorAgent()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())