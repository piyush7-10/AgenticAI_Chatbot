"""
Research Analyst Agent - WORKING VERSION
Works without tools parameter in CrewAI Agent
"""

from crewai import Agent
from langchain_openai import ChatOpenAI
import os
from typing import List, Dict, Any
from rag_system import JioRAGSystem
from mcp_client import MCPClient

class ResearchAnalystAgent:
    """Research Analyst - Data gathering and analysis expert"""
    
    def __init__(self, llm=None, rag_system=None, mcp_client=None):
        """Initialize the Research Analyst Agent"""
        
        # Use provided LLM or create new one
        self.llm = llm or ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Store subsystems as instance variables
        self.rag_system = rag_system
        self.mcp_client = mcp_client
        
        # Create tools list (for reference, not passed to Agent)
        self.tools = self._create_tools()
        
        # Create the agent WITHOUT tools parameter
        self.agent = self._create_agent()
        
        print("✅ Research Analyst Agent initialized")
    
    def _create_tools(self) -> List:
        """Create tool functions that can be called directly"""
        tools = []
        
        def search_knowledge_base(query: str) -> str:
            """Search the RAG knowledge base for Jio plans and services information"""
            if self.rag_system:
                try:
                    return self.rag_system.get_context(query)
                except Exception as e:
                    return f"Knowledge base error: {str(e)}"
            return "Knowledge base not available. Jio offers plans from ₹199 to ₹2999."
        
        def search_jio_plans(query: str) -> str:
            """Search for specific Jio plans based on requirements"""
            if self.mcp_client:
                try:
                    return self.mcp_client.search_plans(query, "all")
                except Exception as e:
                    return f"Plan search error: {str(e)}"
            return f"Searching for Jio plans matching: {query}. Popular plans include ₹299 (2GB/day) and ₹399 (3GB/day)."
        
        def get_jio_plan_details(plan_id: str) -> str:
            """Get detailed information about a specific Jio plan by price"""
            if self.mcp_client:
                try:
                    return self.mcp_client.get_plan_details(plan_id)
                except Exception as e:
                    return f"Error getting plan details: {str(e)}"
            
            # Fallback data
            plans = {
                "199": "₹199 Plan: 1.5GB/day, 28 days validity, unlimited calls, 100 SMS/day, 5G access",
                "299": "₹299 Plan: 2GB/day, 28 days validity, unlimited calls, 100 SMS/day, 5G access",
                "399": "₹399 Plan: 3GB/day, 56 days validity, unlimited calls, 100 SMS/day, 5G access, BEST VALUE",
                "599": "₹599 Plan: 3GB/day, 84 days validity, unlimited calls, 100 SMS/day, 5G access"
            }
            return plans.get(plan_id, f"Details for ₹{plan_id} plan not found")
        
        # Store tool functions for direct access
        self.search_knowledge_base = search_knowledge_base
        self.search_jio_plans = search_jio_plans
        self.get_jio_plan_details = get_jio_plan_details
        
        tools = [search_knowledge_base, search_jio_plans, get_jio_plan_details]
        return tools
    
    def _create_agent(self) -> Agent:
        """Create the Research Analyst agent WITHOUT tools parameter"""
        backstory = f"""You are a senior research analyst specializing in Jio telecommunications services in India.
        
        You have access to extensive knowledge about Jio plans and services. When asked about specific plans or services:
        
        KNOWLEDGE BASE:
        Popular Jio Plans:
        - ₹199: 1.5GB/day, 28 days validity, unlimited calls
        - ₹299: 2GB/day, 28 days validity, unlimited calls  
        - ₹399: 3GB/day, 56 days validity, unlimited calls (BEST VALUE - double validity!)
        - ₹599: 3GB/day, 84 days validity, unlimited calls
        
        JioFiber Plans:
        - ₹699: 30 Mbps unlimited
        - ₹999: 100 Mbps unlimited with OTT apps
        - ₹1499: 300 Mbps unlimited with Netflix, Prime
        
        Key Features (ALL plans include):
        - Unlimited voice calls to any network
        - 100 SMS per day
        - Free 5G access (no extra cost)
        - Access to Jio apps suite
        
        Special Information:
        - 5G is available in 500+ cities across India
        - Student plans: ₹199 for budget, ₹299 for regular use
        - Family plans: JioFiber ₹999 + mobile connections
        - Best value: ₹399 plan (lowest daily cost at ₹7.13/day)
        
        IMPORTANT:
        - Always provide specific, accurate information
        - Use ₹ (Indian Rupees) for all prices
        - Mention that 5G is FREE with all plans
        - Highlight unlimited calling on ALL plans
        - For comparisons, show daily cost calculations
        - Format responses with bullet points when listing multiple items
        
        You are analytical, thorough, and always provide data-driven insights."""
        
        return Agent(
            role='Jio Research Analyst',
            goal='Provide accurate, specific information about Jio plans and services',
            backstory=backstory,
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=3
        )
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze a query to extract key information"""
        query_lower = query.lower()
        
        # Direct tool usage based on query
        if "299" in query:
            details = self.get_jio_plan_details("299")
        elif "399" in query:
            details = self.get_jio_plan_details("399")
        elif "199" in query:
            details = self.get_jio_plan_details("199")
        else:
            details = None
        
        analysis = {
            "query": query,
            "user_type": self._identify_user_type(query),
            "requirements": self._extract_requirements(query),
            "budget": self._extract_budget(query),
            "priority": self._determine_priority(query),
            "plan_details": details
        }
        return analysis
    
    def _identify_user_type(self, query: str) -> str:
        """Identify the type of user from the query"""
        query_lower = query.lower()
        
        if "student" in query_lower:
            return "student"
        elif "family" in query_lower:
            return "family"
        elif "business" in query_lower or "work" in query_lower or "professional" in query_lower:
            return "professional"
        elif "senior" in query_lower or "elderly" in query_lower:
            return "senior"
        else:
            return "general"
    
    def _extract_requirements(self, query: str) -> List[str]:
        """Extract specific requirements from the query"""
        requirements = []
        query_lower = query.lower()
        
        # Data requirements
        if "unlimited" in query_lower:
            requirements.append("unlimited_data")
        if "5g" in query_lower:
            requirements.append("5g_access")
        if "fiber" in query_lower or "broadband" in query_lower:
            requirements.append("fiber_connection")
        
        # Specific data amounts
        if "2gb" in query_lower or "2 gb" in query_lower:
            requirements.append("2gb_daily")
        if "3gb" in query_lower or "3 gb" in query_lower:
            requirements.append("3gb_daily")
        
        # Plan mentions
        for price in ["199", "299", "399", "599"]:
            if price in query_lower:
                requirements.append(f"plan_{price}")
        
        # Comparison
        if "compare" in query_lower or "vs" in query_lower or "versus" in query_lower:
            requirements.append("comparison_needed")
        
        return requirements
    
    def _extract_budget(self, query: str) -> float:
        """Extract budget from the query if mentioned"""
        import re
        
        # Look for budget patterns
        budget_patterns = [
            r'budget.*?(\d+)',
            r'under.*?(\d+)',
            r'less than.*?(\d+)',
            r'max.*?(\d+)',
            r'₹\s*(\d+)',
        ]
        
        query_lower = query.lower()
        for pattern in budget_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return float(match.group(1))
        
        # Check for specific plan prices
        for price in ['199', '299', '399', '599', '999', '1499']:
            if price in query_lower:
                return float(price)
        
        return None
    
    def _determine_priority(self, query: str) -> str:
        """Determine the priority level of the query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["urgent", "asap", "immediately", "now", "quick"]):
            return "high"
        elif any(word in query_lower for word in ["compare", "versus", "vs", "detailed", "comprehensive"]):
            return "complex"
        else:
            return "normal"
    
    def get_agent(self) -> Agent:
        """Return the CrewAI agent"""
        return self.agent
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": "Research Analyst",
            "role": self.agent.role,
            "tools": [func.__name__ for func in self.tools],
            "tool_count": len(self.tools),
            "can_delegate": self.agent.allow_delegation,
            "specialties": [
                "Data gathering",
                "Market research",
                "Requirement analysis",
                "Knowledge base search",
                "Pattern identification",
                "Jio plan expertise"
            ]
        }