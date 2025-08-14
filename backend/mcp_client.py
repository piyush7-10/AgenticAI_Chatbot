import asyncio
from typing import Dict, Any, List
from mcp_server import JioMCPServer
import re

class MCPClient:
    """Client to interact with MCP Server from CrewAI agents"""
    
    def __init__(self):
        self.server = JioMCPServer()
        print("✅ MCP Client connected to server")
    
    def search_plans(self, query: str, plan_type: str = "all") -> str:
        """Synchronous wrapper for search_plans"""
        result = asyncio.run(self.server.search_plans(query, plan_type))
        
        if result["status"] == "success" and result["plans"]:
            plans_text = "\n".join([
                f"- {plan['content'][:100]}... (Source: {plan['source']})"
                for plan in result["plans"]
            ])
            return f"Found {result['count']} relevant plans:\n{plans_text}"
        return "No plans found matching your criteria."
    
    def get_plan_details(self, plan_name: str) -> str:
        """Synchronous wrapper for get_plan_details"""
        result = asyncio.run(self.server.get_plan_details(plan_name))
        
        if result["status"] == "success":
            plan = result["plan"]
            
            # Check if it's a mobile plan (has 'data' and 'validity')
            if "data" in plan and "validity" in plan:
                return f"""
Plan: {plan['name']}
Data: {plan['data']}
Validity: {plan['validity']}
Voice: {plan['voice']}
SMS: {plan.get('sms', 'N/A')}
Benefits: {', '.join(plan.get('benefits', []))}
"""
            # Check if it's a fiber plan (has 'speed')
            elif "speed" in plan:
                return f"""
Plan: {plan['name']}
Speed: {plan['speed']}
Data: {plan.get('data', 'Unlimited')}
Voice: {plan.get('voice', 'Unlimited calls')}
OTT Apps: {', '.join(plan.get('ott', []))}
Benefits: {', '.join(plan.get('benefits', []))}
"""
            # Generic plan format
            else:
                details_text = f"Plan: {plan.get('name', plan_name)}\n"
                
                # Add any available fields
                for key, value in plan.items():
                    if key != 'name':
                        if isinstance(value, list):
                            details_text += f"{key.title()}: {', '.join(value)}\n"
                        else:
                            details_text += f"{key.title()}: {value}\n"
                
                return details_text if len(details_text) > len(f"Plan: {plan_name}\n") else f"Plan: {plan_name}\nDetails: {plan.get('details', 'No detailed information available')}"
        
        return f"Could not find details for {plan_name}"
    
    def recommend_plan(self, user_type: str, data_usage: str, budget: float = None) -> str:
        """Synchronous wrapper for recommend_plan"""
        result = asyncio.run(self.server.recommend_plan(user_type, data_usage, budget))
        
        if result["status"] == "success":
            recs = "\n".join([f"• {rec}" for rec in result["recommendations"]])
            profile = result["user_profile"]
            return f"""
Based on your profile:
- User Type: {profile['type'].title()}
- Data Usage: {profile['usage'].title()}
- Budget: ₹{profile['budget'] if profile['budget'] else 'Flexible'}

Recommended Plans:
{recs}
"""
        return "Could not generate recommendations."
    
    def compare_plans(self, plan1: str, plan2: str) -> str:
        """Synchronous wrapper for compare_plans"""
        result = asyncio.run(self.server.compare_plans(plan1, plan2))
        
        if result["status"] == "success":
            p1 = result["plan1"]
            p2 = result["plan2"]
            return f"""
Comparison:

{p1.get('name', plan1)}:
{self._format_plan_details(p1)}

{p2.get('name', plan2)}:
{self._format_plan_details(p2)}

{result['recommendation']}
"""
        return "Could not compare plans."
    
    def check_5g_availability(self, location: str) -> str:
        """Synchronous wrapper for check_5g_availability"""
        result = asyncio.run(self.server.check_5g_availability(location))
        
        if result["status"] == "success":
            return f"""
5G Status in {result['location']}:
{result['message']}

Compatible Plans:
{chr(10).join(['• ' + plan for plan in result['compatible_plans']])}
"""
        return "Could not check 5G availability."
    
    def _format_plan_details(self, plan: Dict[str, Any]) -> str:
        """Format plan details for display - handles both mobile and fiber plans"""
        if not plan or plan == {"name": plan.get("name", ""), "details": "Not found"}:
            return "Details not available"
        
        details = []
        
        # Define the order of fields to display
        field_order = ['data', 'speed', 'validity', 'voice', 'sms', 'ott', 'benefits', 'details']
        
        # Display fields in order if they exist
        for field in field_order:
            if field in plan:
                value = plan[field]
                if isinstance(value, list) and value:
                    details.append(f"- {field.title()}: {', '.join(value)}")
                elif value and not isinstance(value, list):
                    details.append(f"- {field.title()}: {value}")
        
        # Add any other fields not in the standard order
        for key, value in plan.items():
            if key not in field_order and key != "name":
                if isinstance(value, list) and value:
                    details.append(f"- {key.title()}: {', '.join(value)}")
                elif value and not isinstance(value, list):
                    details.append(f"- {key.title()}: {value}")
        
        return "\n".join(details) if details else "No details available"