import asyncio
import json
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
import re
load_dotenv()

class JioMCPServer:
    """MCP Server for Jio Assistant providing tools and context"""
    
    def __init__(self):
        self.name = "jio-mcp-server"
        self.version = "1.0.0"
        self.tools = {}
        self.setup_vector_db()
        self.setup_tools()
        print("✅ MCP Server initialized")
    
    def setup_vector_db(self):
        """Initialize ChromaDB for vector search"""
        self.chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
        
        # Use OpenAI embeddings
        self.embedding_func = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-ada-002"
        )
        
        try:
            self.collection = self.chroma_client.get_collection(
                name="jio_plans",
                embedding_function=self.embedding_func
            )
            print(f"✅ Loaded existing collection with {self.collection.count()} documents")
        except:
            self.collection = self.chroma_client.create_collection(
                name="jio_plans",
                embedding_function=self.embedding_func
            )
            self.load_jio_data()
            print("✅ Created new collection and loaded data")
    
    def load_jio_data(self):
        """Load Jio data into vector database"""
        with open('data/jio_data.json', 'r') as f:
            data = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, item in enumerate(data):
            # Split content into chunks
            content = item['content']
            chunk_size = 500
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            
            for j, chunk in enumerate(chunks):
                documents.append(chunk)
                metadatas.append({
                    "source": item['url'],
                    "title": item.get('title', 'Jio Info'),
                    "chunk_index": j
                })
                ids.append(f"doc_{i}_chunk_{j}")
        
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✅ Added {len(documents)} chunks to vector database")
    
    def setup_tools(self):
        """Define MCP tools available to agents"""
        
        self.tools = {
            "search_plans": {
                "name": "search_plans",
                "description": "Search for Jio plans based on requirements",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "plan_type": {"type": "string", "enum": ["mobile", "fiber", "postpaid", "business", "all"]}
                },
                "handler": self.search_plans
            },
            "get_plan_details": {
                "name": "get_plan_details",
                "description": "Get detailed information about a specific plan",
                "parameters": {
                    "plan_name": {"type": "string", "description": "Name or price of the plan"}
                },
                "handler": self.get_plan_details
            },
            "recommend_plan": {
                "name": "recommend_plan",
                "description": "Get personalized plan recommendations",
                "parameters": {
                    "user_type": {"type": "string", "enum": ["student", "professional", "family", "business"]},
                    "data_usage": {"type": "string", "enum": ["low", "medium", "high"]},
                    "budget": {"type": "number", "description": "Maximum budget per month"}
                },
                "handler": self.recommend_plan
            },
            "compare_plans": {
                "name": "compare_plans",
                "description": "Compare multiple Jio plans",
                "parameters": {
                    "plan1": {"type": "string"},
                    "plan2": {"type": "string"}
                },
                "handler": self.compare_plans
            },
            "check_5g_availability": {
                "name": "check_5g_availability",
                "description": "Check 5G availability and compatible plans",
                "parameters": {
                    "location": {"type": "string", "description": "City or area name"}
                },
                "handler": self.check_5g_availability
            }
        }
    
    async def search_plans(self, query: str, plan_type: str = "all") -> Dict[str, Any]:
        """Search for plans using vector database"""
        try:
            # Add plan type to query if specified
            search_query = f"{query} {plan_type}" if plan_type != "all" else query
            
            # Search in vector database
            results = self.collection.query(
                query_texts=[search_query],
                n_results=5,
                where={"source": {"$contains": plan_type}} if plan_type != "all" else None
            )
            
            # Format results
            plans = []
            if results['documents']:
                for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                    plans.append({
                        "content": doc[:200],  # Truncate for readability
                        "source": metadata.get('source', 'Unknown'),
                        "relevance": "High"
                    })
            
            return {
                "status": "success",
                "plans": plans,
                "count": len(plans)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def get_plan_details(self, plan_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific plan"""
        # Predefined plan details (in production, this would query the database)
        plan_database = {
            "199": {
                "name": "₹199 Plan",
                "data": "1.5GB/day",
                "validity": "28 days",
                "voice": "Unlimited",
                "sms": "100/day",
                "benefits": ["Jio Apps", "5G Access", "Weekend Data Rollover"]
            },
            "299": {
                "name": "₹299 Plan",
                "data": "2GB/day",
                "validity": "28 days",
                "voice": "Unlimited",
                "sms": "100/day",
                "benefits": ["Jio Apps", "5G Access", "Weekend Data Rollover", "JioCloud Storage"]
            },
            "399": {
                "name": "₹399 Plan",
                "data": "3GB/day",
                "validity": "56 days",
                "voice": "Unlimited",
                "sms": "100/day",
                "benefits": ["Jio Apps", "5G Access", "Weekend Data Rollover", "JioCloud Storage", "JioSecurity"]
            },
            "999": {
                "name": "JioFiber ₹999",
                "speed": "100 Mbps",
                "data": "Unlimited",
                "voice": "Unlimited calls",
                "ott": ["Netflix", "Amazon Prime", "JioCinema Premium"],
                "benefits": ["Free Router", "Free Installation", "No Security Deposit"]
            }
        }
        
        # Extract number from plan name
        import re
        numbers = re.findall(r'\d+', plan_name)
        plan_key = numbers[0] if numbers else plan_name
        
        if plan_key in plan_database:
            return {
                "status": "success",
                "plan": plan_database[plan_key]
            }
        else:
            # Search in vector database
            results = await self.search_plans(plan_name, "all")
            if results["plans"]:
                return {
                    "status": "success",
                    "plan": {
                        "name": plan_name,
                        "details": results["plans"][0]["content"]
                    }
                }
            return {"status": "not_found", "message": f"Plan {plan_name} not found"}
    
    async def recommend_plan(self, user_type: str, data_usage: str, budget: float = None) -> Dict[str, Any]:
        """Get personalized recommendations based on user profile"""
        recommendations = {
            ("student", "low"): ["₹199 - Perfect for basic needs", "₹155 - 2GB/day for 24 days"],
            ("student", "medium"): ["₹299 - 2GB/day ideal for streaming", "₹399 - Longer validity saves money"],
            ("student", "high"): ["₹399 - 3GB/day for heavy usage", "₹599 - 84 days validity"],
            ("professional", "low"): ["₹299 - Reliable for work", "₹399 - Better value"],
            ("professional", "medium"): ["₹399 - 3GB/day for video calls", "JioFiber ₹999 for home office"],
            ("professional", "high"): ["₹599 - Heavy usage plan", "JioFiber ₹1499 - 300 Mbps"],
            ("family", "low"): ["₹399 - Shareable data", "Family Postpaid ₹799"],
            ("family", "medium"): ["Family Postpaid ₹799", "JioFiber ₹999 + Mobile"],
            ("family", "high"): ["JioFiber ₹1499", "Family Postpaid ₹1299"]
        }
        
        key = (user_type, data_usage)
        plans = recommendations.get(key, ["₹299 - Balanced plan", "₹399 - Popular choice"])
        
        # Filter by budget if provided
        if budget:
            plans = [p for p in plans if int(re.findall(r'\d+', p)[0]) <= budget] if plans else ["₹199 - Within budget"]
        
        return {
            "status": "success",
            "recommendations": plans,
            "user_profile": {
                "type": user_type,
                "usage": data_usage,
                "budget": budget
            }
        }
    
    async def compare_plans(self, plan1: str, plan2: str) -> Dict[str, Any]:
        """Compare two plans side by side"""
        # Get details for both plans
        details1 = await self.get_plan_details(plan1)
        details2 = await self.get_plan_details(plan2)
        
        comparison = {
            "status": "success",
            "plan1": details1.get("plan", {"name": plan1, "details": "Not found"}),
            "plan2": details2.get("plan", {"name": plan2, "details": "Not found"}),
            "recommendation": "Based on the comparison, choose according to your data needs and budget."
        }
        
        return comparison
    
    async def check_5g_availability(self, location: str) -> Dict[str, Any]:
        """Check 5G availability in a location"""
        # Major cities with 5G (simplified list)
        cities_with_5g = [
            "delhi", "mumbai", "bangalore", "chennai", "kolkata", "hyderabad",
            "pune", "ahmedabad", "jaipur", "lucknow", "kanpur", "nagpur",
            "visakhapatnam", "bhopal", "patna", "ludhiana", "agra", "nashik",
            "faridabad", "meerut", "rajkot", "varanasi", "srinagar", "aurangabad"
        ]
        
        location_lower = location.lower()
        is_available = any(city in location_lower for city in cities_with_5g)
        
        return {
            "status": "success",
            "location": location,
            "5g_available": is_available,
            "message": f"5G is {'available' if is_available else 'coming soon'} in {location}",
            "compatible_plans": ["All plans ₹239 and above include unlimited 5G"] if is_available else ["5G will be available once launched in your area"]
        }
    
    def get_tool_list(self) -> List[Dict[str, Any]]:
        """Return list of available tools in MCP format"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for tool in self.tools.values()
        ]
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution requests"""
        if tool_name not in self.tools:
            return {"error": f"Tool {tool_name} not found"}
        
        handler = self.tools[tool_name]["handler"]
        try:
            result = await handler(**arguments)
            return result
        except Exception as e:
            return {"error": str(e)}

# MCP Server Runner
async def run_mcp_server():
    """Run the MCP server"""
    server = JioMCPServer()
    print(f"🚀 MCP Server '{server.name}' v{server.version} is running")
    print(f"📦 Available tools: {', '.join(server.tools.keys())}")
    
    # Keep server running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_mcp_server())