"""
Solution Architect Agent - WORKING VERSION
Works without tools parameter in CrewAI Agent
"""

from crewai import Agent
from langchain_openai import ChatOpenAI
import os
from typing import List, Dict, Any
from mcp_client import MCPClient

class SolutionArchitectAgent:
    """Solution Architect - Designs optimal solutions based on requirements"""
    
    def __init__(self, llm=None, mcp_client=None):
        """Initialize the Solution Architect Agent"""
        
        # Use provided LLM or create new one
        self.llm = llm or ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.5,  # Lower temperature for more consistent technical decisions
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Store MCP client
        self.mcp_client = mcp_client
        
        # Create tools (for reference, not passed to Agent)
        self.tools = self._create_tools()
        
        # Create the agent WITHOUT tools parameter
        self.agent = self._create_agent()
        
        print("✅ Solution Architect Agent initialized")
    
    def _create_tools(self) -> List:
        """Create tool functions that can be called directly"""
        tools = []
        
        def compare_jio_plans(plan1: str, plan2: str) -> str:
            """Compare two Jio plans"""
            if self.mcp_client:
                try:
                    return self.mcp_client.compare_plans(plan1, plan2)
                except:
                    pass
            
            # Fallback comparison data
            comparisons = {
                ("299", "399"): """📊 Jio Plan Comparison: ₹299 vs ₹399

₹299 Plan:
• Data: 2GB/day
• Validity: 28 days
• Daily Cost: ₹10.68
• Total Data: 56GB

₹399 Plan:
• Data: 3GB/day
• Validity: 56 days (2X!)
• Daily Cost: ₹7.13
• Total Data: 168GB

🏆 Winner: ₹399 Plan
✅ 50% more daily data
✅ Double validity period
✅ 33% lower daily cost
✅ 3X total data

Recommendation: ₹399 offers significantly better value!""",
                
                ("199", "299"): """📊 Jio Plan Comparison: ₹199 vs ₹299

₹199 Plan:
• Data: 1.5GB/day
• Validity: 28 days
• Daily Cost: ₹7.11

₹299 Plan:
• Data: 2GB/day
• Validity: 28 days
• Daily Cost: ₹10.68

Analysis:
• ₹199: Best for budget-conscious users
• ₹299: Better for regular streaming and browsing"""
            }
            
            key = (plan1, plan2) if (plan1, plan2) in comparisons else (plan2, plan1)
            if key in comparisons:
                return comparisons[key]
            
            return f"Comparing ₹{plan1} vs ₹{plan2}: Both are good Jio plans. Higher price generally offers more features."
        
        def calculate_plan_roi(plan_price: int, usage_hours: float = 5) -> str:
            """Calculate ROI and value of a Jio plan"""
            # Plan validity data
            validity_days = {
                199: 28, 299: 28, 399: 56, 599: 84,
                155: 24, 239: 28, 533: 56
            }
            
            days = validity_days.get(plan_price, 28)
            cost_per_day = plan_price / days
            cost_per_hour = cost_per_day / usage_hours if usage_hours > 0 else cost_per_day
            
            # Value assessment
            if cost_per_hour < 2:
                value = "EXCELLENT - Superb value!"
            elif cost_per_hour < 5:
                value = "VERY GOOD - Great choice!"
            elif cost_per_hour < 10:
                value = "GOOD - Decent value"
            else:
                value = "MODERATE - Consider usage"
            
            # Get data allowance
            data_per_day = {199: 1.5, 299: 2, 399: 3, 599: 3}.get(plan_price, 2)
            
            return f"""📊 ROI Analysis for ₹{plan_price} Plan:

Financial Breakdown:
• Daily Cost: ₹{cost_per_day:.2f}
• Per Hour Cost: ₹{cost_per_hour:.2f}
• Validity: {days} days

Data Value:
• Daily Data: {data_per_day}GB
• Total Data: {data_per_day * days}GB
• Cost per GB: ₹{(plan_price / (data_per_day * days)):.2f}

💰 Value Assessment: {value}"""
        
        # Store tool functions for direct access
        self.compare_jio_plans = compare_jio_plans
        self.calculate_plan_roi = calculate_plan_roi
        
        tools = [compare_jio_plans, calculate_plan_roi]
        return tools
    
    def _create_agent(self) -> Agent:
        """Create the Solution Architect agent WITHOUT tools parameter"""
        backstory = """You are a senior solution architect specializing in Jio telecommunications solutions.
        
        MANDATORY: Write ONLY in bullet points. NO PARAGRAPHS EVER.
        
        COMPARISON FORMAT:
        ₹299 vs ₹399:
        • ₹299: 2GB/day, 28 days, ₹10.68/day
        • ₹399: 3GB/day, 56 days, ₹7.13/day
        • Winner: ₹399 (lower daily cost, double validity)
        
        RECOMMENDATION FORMAT:
        For [User Type]:
        • Budget: ₹XXX - [reason in 5 words]
        • Recommended: ₹XXX - [reason in 5 words]
        • Premium: ₹XXX - [reason in 5 words]
        
        QUICK FACTS (memorized):
        • ₹399 = BEST VALUE (₹7.13/day)
        • ₹599 = Heavy users (84 days)
        • ₹299 = Popular choice
        • ₹199 = Budget option
        
        VALUE FORMULA:
        • Daily cost = Price ÷ Validity
        • Lower daily cost = Better value
        • Longer validity = More savings
        
        RESPONSE RULES:
        • Maximum 10-12 total points
        • Each point under 15 words
        • Numbers, not words (2 not two)
        • Skip marketing language
        • Be direct and specific
        
        Your analysis must be sharp, clear, and minimal."""
        
        return Agent(
            role='Jio Solution Architect - Crisp Analysis',
            goal='Design solutions in clear, minimal bullet points',
            backstory=backstory,
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=3
        )
    
    def evaluate_options(self, options: List[Dict[str, Any]], criteria: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate multiple options against weighted criteria"""
        
        # Default criteria weights if not provided
        default_criteria = {
            "cost": 0.3,
            "data": 0.25,
            "validity": 0.20,
            "features": 0.15,
            "value": 0.10
        }
        
        criteria = criteria or default_criteria
        
        evaluations = []
        for option in options:
            score = 0
            evaluation = {
                "option": option,
                "scores": {},
                "total_score": 0
            }
            
            # Calculate weighted scores
            for criterion, weight in criteria.items():
                criterion_score = self._score_criterion(option, criterion)
                evaluation["scores"][criterion] = criterion_score
                score += criterion_score * weight
            
            evaluation["total_score"] = score
            evaluations.append(evaluation)
        
        # Sort by total score
        evaluations.sort(key=lambda x: x["total_score"], reverse=True)
        
        return {
            "best_option": evaluations[0] if evaluations else None,
            "all_evaluations": evaluations,
            "criteria_used": criteria
        }
    
    def _score_criterion(self, option: Dict[str, Any], criterion: str) -> float:
        """Score a single criterion for an option (0-100)"""
        
        if criterion == "cost":
            # Lower cost = higher score
            price = option.get("price", 999999)
            if price < 200:
                return 100
            elif price < 400:
                return 80
            elif price < 600:
                return 60
            elif price < 1000:
                return 40
            else:
                return 20
        
        elif criterion == "data":
            # More data = higher score
            data = option.get("data_per_day", 0)
            if data >= 4:
                return 100
            elif data >= 3:
                return 80
            elif data >= 2:
                return 60
            elif data >= 1.5:
                return 40
            else:
                return 20
        
        elif criterion == "validity":
            # Longer validity = higher score
            days = option.get("validity_days", 0)
            if days >= 84:
                return 100
            elif days >= 56:
                return 90
            elif days >= 28:
                return 60
            else:
                return 40
        
        elif criterion == "value":
            # Lower daily cost = higher score
            daily_cost = option.get("daily_cost", 100)
            if daily_cost < 8:
                return 100
            elif daily_cost < 11:
                return 80
            elif daily_cost < 15:
                return 60
            else:
                return 40
        
        else:
            # Default scoring for unknown criteria
            return 50
    
    def get_agent(self) -> Agent:
        """Return the CrewAI agent"""
        return self.agent
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": "Solution Architect",
            "role": self.agent.role,
            "tools": [func.__name__ for func in self.tools],
            "tool_count": len(self.tools),
            "can_delegate": self.agent.allow_delegation,
            "specialties": [
                "Solution design",
                "Plan comparison",
                "ROI calculation",
                "5G assessment",
                "Bundle creation",
                "Value analysis"
            ]
        }