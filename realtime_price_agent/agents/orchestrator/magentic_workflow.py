"""Magentic Workflow for Supply Chain Agents.

This module implements the Magentic orchestration pattern from Microsoft Agent Framework
for coordinating multiple specialized supply chain agents.

Reference: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/magentic

HOW MAGENTIC ORCHESTRATION WORKS:
=================================

1. USER sends a message (e.g., "Butter price increased 15%")

2. ORCHESTRATOR AGENT (StandardMagenticManager) analyzes the request and decides 
   which specialized agent should handle it

3. The orchestrator HANDS OFF the task to the appropriate agent:
   - Price queries → PriceMonitoringAgent
   - Demand queries → DemandForecastingAgent  
   - Order queries → AutomatedOrderingAgent

4. The specialized agent processes the request, optionally using MCP TOOLS 
   to fetch real data from external services

5. The orchestrator can COORDINATE multiple agents if needed:
   - First get price impact from PriceMonitoringAgent
   - Then get demand forecast from DemandForecastingAgent
   - Finally generate order from AutomatedOrderingAgent

6. FINAL RESPONSE is assembled and returned to the user
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent_framework import (
    ChatAgent,
    MCPStreamableHTTPTool,
    MagenticBuilder,
    StandardMagenticManager,
    # Event types available in agent-framework-core
    WorkflowOutputEvent,
    WorkflowStartedEvent,
    WorkflowFailedEvent,
    SuperStepCompletedEvent,
    SuperStepStartedEvent,
    AgentRunEvent,
    AgentRunUpdateEvent,
    WorkflowStatusEvent,
)
from agent_framework.openai import OpenAIChatClient
from openai import AsyncAzureOpenAI

from agents.config import settings
from agents.orchestrator.tools.tool_registry import tool_registry

# Import agent definitions from per-agent modules
from agents.price_monitoring import create_price_monitoring_agent
from agents.demand_forecasting import create_demand_forecasting_agent
from agents.automated_ordering import create_automated_ordering_agent
from agents.negotiation import create_negotiation_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# ORCHESTRATOR INSTRUCTIONS
# =============================================================================

ORCHESTRATOR_INSTRUCTIONS = """You are the Orchestrator Agent for a supply chain management system.
Your role is to analyze user queries and delegate to the appropriate specialized agent(s).

AVAILABLE SPECIALIZED AGENTS:

1. PriceMonitoringAgent
   Use for: Price changes, supplier optimization, margin analysis, "best place to buy"
   Examples:
   - "Supplier increased butter price by 15%"
   - "Find cheapest supplier for 500 lbs flour"
   - "Analyze margin impact of wheat price increase"

2. DemandForecastingAgent
   Use for: Sales predictions, demand forecasting, trend analysis
   Examples:
   - "Predict milk demand for next week"
   - "What's the seasonal trend for ice cream?"
   - "How much should we stock for the holiday season?"

3. AutomatedOrderingAgent
   Use for: Purchase order generation, order execution, supplier orders
   Examples:
   - "Create purchase order for 100 units of SKU-123"
   - "Place order with Supplier A for butter"
   - "Generate orders based on current inventory levels"

4. NegotiationAgent
   Use for: Multi-supplier price negotiations, getting quotes, counter-offers
   Examples:
   - "Negotiate best price for 500 units of butter"
   - "Get quotes from suppliers for flour"
   - "Compare supplier offers and negotiate better prices"

ROUTING LOGIC:
- If query mentions: prices, suppliers, margins, cost → Delegate to PriceMonitoringAgent
- If query mentions: forecast, predict, demand, trends → Delegate to DemandForecastingAgent
- If query mentions: order, purchase, buy (without negotiation) → Delegate to AutomatedOrderingAgent
- If query mentions: negotiate, best price, quotes, counter-offer → Delegate to NegotiationAgent
- If query spans multiple areas, coordinate between multiple agents in sequence

Always explain which agent(s) you're delegating to and why.
Format responses clearly and provide actionable insights."""


# =============================================================================
# ORCHESTRATOR CLASS
# =============================================================================

class SupplyChainOrchestrator:
    """Magentic-based supply chain orchestrator using Microsoft Agent Framework.

    Coordinates multiple specialized agents using the Magentic orchestration pattern:
    - OrchestratorAgent: Routes queries to appropriate agents
    - PriceMonitoringAgent: Price detection and supplier optimization
    - DemandForecastingAgent: Demand prediction and trend analysis
    - AutomatedOrderingAgent: Purchase order generation
    
    Agent Handoff Flow:
    1. User message → Orchestrator analyzes intent
    2. Orchestrator delegates to specialized agent(s)
    3. Specialized agent(s) process with MCP tools
    4. Results flow back through orchestrator
    5. Final response to user
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.chat_client: Optional[Any] = None
        self._manager_agent: Optional[ChatAgent] = None
        logger.info("🚀 Supply Chain Orchestrator initialized")

    async def initialize(self) -> None:
        """Initialize the Azure OpenAI chat client."""
        logger.info("Initializing Supply Chain workflow...")

        if not settings.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required")

        if not settings.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required")

        # Create Azure OpenAI client
        async_client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )

        # Wrap with MAF's OpenAIChatClient
        self.chat_client = OpenAIChatClient(
            model_id=settings.azure_openai_deployment_name,
            async_client=async_client,
        )

        # Create the manager agent for orchestration
        self._manager_agent = ChatAgent(
            name="ManagerAgent",
            description="Orchestrates supply chain agents",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            chat_client=self.chat_client,
        )

        logger.info(f"✓ Chat client initialized: {settings.azure_openai_deployment_name}")
        logger.info("✓ Supply Chain workflow ready")

    def _create_mcp_tool(self, server_id: str) -> Optional[MCPStreamableHTTPTool]:
        """Create MCP tool from registry metadata."""
        metadata = tool_registry.get_server_metadata(server_id)
        if not metadata:
            logger.debug(f"No metadata for MCP server: {server_id}")
            return None

        try:
            tool = MCPStreamableHTTPTool(
                name=metadata["name"],
                url=metadata["url"],
                headers=None,
                load_tools=True,
                load_prompts=False,
                request_timeout=30,
                approval_mode="never_require",
            )
            logger.info(f"✓ MCP tool created: {metadata['name']}")
            return tool
        except Exception as e:
            logger.warning(f"⚠ Could not create MCP tool for {server_id}: {e}")
            return None

    async def process_request_stream(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user request using the Magentic workflow with streaming.

        Args:
            user_message: The user's message/request
            conversation_history: Optional conversation history

        Yields:
            Event dictionaries for UI consumption showing agent interactions
        """
        if not self.chat_client:
            raise RuntimeError("Chat client not initialized. Call initialize() first.")

        logger.info(f"\n{'='*60}")
        logger.info(f"📥 USER REQUEST: {user_message[:100]}...")
        logger.info(f"{'='*60}\n")

        # NOTE: MCPStreamableHTTPTool requires SSE transport, but our MCP servers
        # use simple REST POST to /mcp. Disabling tools until servers are upgraded.
        # TODO: Upgrade MCP servers to use MCP Streamable HTTP with SSE
        # For now, agents will work without MCP tools (using LLM knowledge only)
        
        # Create MCP tool instances (DISABLED - protocol mismatch)
        # supplier_tool = self._create_mcp_tool("supplier-data")
        # inventory_tool = self._create_mcp_tool("inventory-mgmt")
        # finance_tool = self._create_mcp_tool("finance-data")
        # analytics_tool = self._create_mcp_tool("analytics-forecast")
        # integrations_tool = self._create_mcp_tool("integrations")

        logger.info("⚠️ MCP tools disabled - servers use REST, framework requires SSE")

        try:
            # Empty tool lists until MCP servers upgraded to SSE
            price_tools = []
            demand_tools = []
            ordering_tools = []
            negotiation_tools = []


            logger.info("\n🏗️ Building Magentic workflow with agents...")
            logger.info("  → OrchestratorAgent (routing)")
            logger.info(f"  → PriceMonitoringAgent (tools: {len(price_tools)})")
            logger.info(f"  → DemandForecastingAgent (tools: {len(demand_tools)})")
            logger.info(f"  → AutomatedOrderingAgent (tools: {len(ordering_tools)})")
            logger.info(f"  → NegotiationAgent (tools: {len(negotiation_tools)})")

            # Build workflow with correct API for this version
            # Create agent instances
            price_agent = create_price_monitoring_agent(
                chat_client=self.chat_client,
                tools=price_tools if price_tools else None,
            )
            demand_agent = create_demand_forecasting_agent(
                chat_client=self.chat_client,
                tools=demand_tools if demand_tools else None,
            )
            ordering_agent = create_automated_ordering_agent(
                chat_client=self.chat_client,
                tools=ordering_tools if ordering_tools else None,
            )
            negotiation_agent = create_negotiation_agent(
                chat_client=self.chat_client,
                tools=negotiation_tools if negotiation_tools else None,
            )
            
            # Build workflow - participants takes a list of agents
            workflow = (
                MagenticBuilder()
                .participants([
                    price_agent,
                    demand_agent,
                    ordering_agent,
                    negotiation_agent,
                ])
                .with_standard_manager(
                    agent=self._manager_agent,
                    max_round_count=8,
                    max_stall_count=2,
                    max_reset_count=1,
                )
                .build()
            )



            logger.info("✓ Workflow built successfully")
            logger.info("\n🔄 Starting workflow execution...\n")

            # Run workflow and stream events
            event_count = 0
            async for event in workflow.run_stream(user_message):
                event_count += 1
                event_data = self._convert_workflow_event(event, event_count)
                if event_data:
                    yield event_data

            logger.info(f"\n✓ Workflow completed. Total events: {event_count}")

        except Exception as e:
            logger.error(f"❌ Workflow error: {e}", exc_info=True)
            yield {
                "type": "error",
                "event": "Error",
                "message": f"Workflow error: {str(e)}",
                "statusCode": 500,
            }

    def _convert_workflow_event(self, event: Any, event_num: int) -> Optional[Dict[str, Any]]:
        """Convert Magentic workflow event to API format with detailed logging."""
        
        event_type = type(event).__name__
        
        # Log every event for debugging
        logger.info(f"  [{event_num}] Event: {event_type}")
        
        if isinstance(event, WorkflowStartedEvent):
            logger.info("      → Workflow has started")
            return {
                "type": "metadata",
                "agent": "Orchestrator",
                "event": "WorkflowStarted",
                "data": {
                    "agent": "Orchestrator",
                    "message": "Analyzing request and routing to agents...",
                },
            }
        
        elif isinstance(event, SuperStepStartedEvent):
            logger.info("      → New super-step started (agent handoff)")
            return {
                "type": "metadata",
                "agent": None,
                "event": "SuperStepStarted",
                "data": {
                    "message": "Agent coordination step started",
                },
            }
        
        elif isinstance(event, SuperStepCompletedEvent):
            logger.info("      → Super-step completed")
            return {
                "type": "metadata",
                "agent": None,
                "event": "SuperStepCompleted",
                "data": {
                    "message": "Agent coordination step completed",
                },
            }
        
        elif isinstance(event, AgentRunEvent):
            agent_name = getattr(event, 'agent_name', None) or getattr(event, 'agent_id', 'Agent')
            message = getattr(event, 'message', None) or getattr(event, 'text', '')
            if hasattr(message, 'text'):
                message = message.text
            elif hasattr(message, 'content'):
                message = message.content
            
            logger.info(f"      → Agent: {agent_name}")
            if message:
                # Truncate long messages in log
                msg_preview = str(message)[:100] + "..." if len(str(message)) > 100 else str(message)
                logger.info(f"        Message: {msg_preview}")
            
            return {
                "type": "metadata",
                "agent": str(agent_name),
                "event": "AgentRun",
                "data": {
                    "agent": str(agent_name),
                    "message": str(message) if message else "",
                },
            }

        elif isinstance(event, AgentRunUpdateEvent):
            agent_name = getattr(event, 'agent_name', None) or getattr(event, 'agent_id', 'Agent')
            delta = getattr(event, 'delta', '') or getattr(event, 'text', '')
            
            # Don't log every delta (too verbose), just return it
            return {
                "type": "delta",
                "agent": str(agent_name),
                "event": "AgentDelta",
                "data": {
                    "agent": str(agent_name),
                    "delta": str(delta) if delta else "",
                },
            }

        elif isinstance(event, WorkflowOutputEvent):
            output_data = str(event.data) if hasattr(event, 'data') and event.data else "Workflow completed"
            logger.info(f"      → Final output received")
            return {
                "type": "metadata",
                "agent": None,
                "event": "WorkflowComplete",
                "data": {
                    "output": output_data,
                    "completed": True,
                },
            }
        
        elif isinstance(event, WorkflowFailedEvent):
            error_msg = str(getattr(event, 'error', 'Unknown error'))
            logger.error(f"      → Workflow failed: {error_msg}")
            return {
                "type": "error",
                "agent": None,
                "event": "WorkflowFailed",
                "data": {
                    "error": error_msg,
                },
            }

        elif isinstance(event, WorkflowStatusEvent):
            status = getattr(event, 'status', 'unknown')
            logger.info(f"      → Status: {status}")
            return {
                "type": "metadata",
                "agent": None,
                "event": "WorkflowStatus",
                "data": {
                    "status": str(status),
                },
            }
        
        # Log unknown event types for debugging
        logger.debug(f"      → Unhandled event type: {event_type}")
        return None


# Global orchestrator instance
magentic_orchestrator = SupplyChainOrchestrator()
