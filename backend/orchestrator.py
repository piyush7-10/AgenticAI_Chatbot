"""
Main Orchestrator for Multi-Agent System - WITH FOLLOW-UP QUESTIONS FEATURE
This version includes RAG & MCP integration plus intelligent follow-up questions
"""

from crewai import Crew, Task, Process
from langchain_openai import ChatOpenAI
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import time
import re
import random

# Import all agents
from agent_research import ResearchAnalystAgent
from agent_architect import SolutionArchitectAgent
from agent_customer import CustomerSuccessAgent

# Import subsystems
from rag_system import JioRAGSystem
from mcp_client import MCPClient


class FollowUpManager:
    """Manages follow-up questions and context for incomplete queries"""
    
    def __init__(self):
        # Store conversation context for follow-ups
        self.pending_context = {}
        
        # Define patterns that need more info
        self.ambiguous_patterns = {
            'vague_plan': {
                'patterns': [
                    r'^plan$', r'^best plan$', r'^good plan$', r'^plans$',
                    r'^recharge$', r'^mobile plan$', r'^jio plan$'
                ],
                'follow_ups': [
                    "I'd be happy to help you find the perfect plan! Could you tell me:\n• What's your budget range? (e.g., under ₹300, ₹300-500)\n• How much data do you typically use? (light: <1GB, medium: 1-2GB, heavy: 3GB+)\n• Are you a student, professional, or looking for family plans?",
                    "To recommend the best plan, could you share your requirements?\n• Budget: ₹___ \n• Primary use: Work/Study/Entertainment?\n• Current data usage per day?"
                ],
                'context_type': 'plan_recommendation'
            },
            'incomplete_comparison': {
                'patterns': [
                    r'^compare$', r'^comparison$', r'^which is better$',
                    r'^compare plans$', r'^vs$'
                ],
                'follow_ups': [
                    "I can help you compare plans! Which specific plans would you like to compare?\n• For example: 'Compare 299 vs 399'\n• Or tell me your budget and I'll compare suitable options",
                    "Which plans should I compare for you?\n• Popular comparisons: ₹299 vs ₹399, ₹199 vs ₹299\n• Or specify any two plan prices"
                ],
                'context_type': 'comparison'
            },
            'missing_location': {
                'patterns': [
                    r'^5g$', r'^5g availability$', r'^is 5g available$',
                    r'^check 5g$', r'^5g coverage$'
                ],
                'follow_ups': [
                    "I'll check 5G availability for you! Which city are you asking about?\n• Major cities with 5G: Mumbai, Delhi, Bangalore, Chennai, Kolkata\n• Just tell me your city name",
                    "To check 5G coverage, please specify your location:\n• City: ___\n• Or share your area/region"
                ],
                'context_type': '5g_check'
            },
            'unclear_budget': {
                'patterns': [
                    r'cheap', r'cheapest', r'affordable', r'budget plan',
                    r'economical', r'low cost'
                ],
                'follow_ups': [
                    "I'll find you the most affordable option! What's your maximum budget?\n• Under ₹200?\n• ₹200-300?\n• ₹300-500?",
                    "To find the best budget plan, could you specify:\n• Maximum amount: ₹___\n• Minimum data needed: ___GB/day"
                ],
                'context_type': 'budget_plan'
            },
            'missing_user_type': {
                'patterns': [
                    r'^recommend', r'^suggest', r'^what should i',
                    r'^which plan for me', r'^best for me'
                ],
                'follow_ups': [
                    "I'll recommend the perfect plan for you! Please tell me:\n• Are you a: Student/Professional/Family user?\n• Daily data usage: Light (<1GB), Medium (1-2GB), Heavy (3GB+)?\n• Budget preference?",
                    "To personalize my recommendation:\n• Your usage type: Work/Study/Entertainment/General?\n• How many connections do you need?\n• Any specific features needed (5G, OTT apps)?"
                ],
                'context_type': 'recommendation'
            },
            'vague_problem': {
                'patterns': [
                    r'^help$', r'^i need help$', r'^assist',
                    r'^support$', r'^issue$', r'^problem$'
                ],
                'follow_ups': [
                    "I'm here to help! What would you like assistance with?\n• Finding a new plan?\n• Comparing existing plans?\n• Understanding plan benefits?\n• 5G availability?\n• JioFiber broadband?",
                    "How can I assist you today?\n• 📱 Mobile plans and recharges\n• 🏠 JioFiber broadband\n• 📊 Plan comparisons\n• 💡 Recommendations\nPlease tell me more!"
                ],
                'context_type': 'general_help'
            }
        }
        
    def needs_follow_up(self, query: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if query needs follow-up questions
        Returns: (needs_followup, follow_up_question, context_type)
        """
        query_lower = query.lower().strip()
        
        # Check each pattern category
        for category, config in self.ambiguous_patterns.items():
            for pattern in config['patterns']:
                if re.match(pattern, query_lower):
                    # Select a follow-up question (can randomize if needed)
                    follow_up = random.choice(config['follow_ups'])
                    return True, follow_up, config['context_type']
        
        # Check for very short queries that might need clarification
        if len(query.split()) <= 2 and not any(char.isdigit() for char in query):
            # Short query without specific numbers
            if 'plan' in query_lower or 'recharge' in query_lower:
                return True, self.ambiguous_patterns['vague_plan']['follow_ups'][0], 'plan_recommendation'
        
        return False, None, None
    
    def store_context(self, session_id: str, original_query: str, context_type: str):
        """Store context for follow-up processing"""
        self.pending_context[session_id] = {
            'original_query': original_query,
            'context_type': context_type,
            'timestamp': time.time()
        }
    
    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored context for a session"""
        return self.pending_context.get(session_id)
    
    def clear_context(self, session_id: str):
        """Clear context after successful resolution"""
        if session_id in self.pending_context:
            del self.pending_context[session_id]
    
    def merge_with_context(self, session_id: str, new_query: str) -> str:
        """
        Merge follow-up answer with original context
        """
        context = self.get_context(session_id)
        if not context:
            return new_query
        
        context_type = context['context_type']
        original = context['original_query']
        
        # Build enhanced query based on context type
        if context_type == 'plan_recommendation':
            # Extract budget and usage from response
            budget_match = re.search(r'₹?(\d{3,4})', new_query)
            usage_patterns = {
                'light': '1GB', 'medium': '2GB', 'heavy': '3GB',
                '<1': '1GB', '1-2': '2GB', '3+': '3GB', '2gb': '2GB', '3gb': '3GB'
            }
            
            budget = budget_match.group(1) if budget_match else "500"
            usage = "2GB"
            for pattern, value in usage_patterns.items():
                if pattern in new_query.lower():
                    usage = value
                    break
            
            # Check for user type
            user_type = "general"
            if 'student' in new_query.lower():
                user_type = "student"
            elif 'professional' in new_query.lower() or 'work' in new_query.lower():
                user_type = "professional"
            elif 'family' in new_query.lower():
                user_type = "family"
            
            enhanced_query = f"Recommend best {user_type} plan under ₹{budget} with {usage} daily data"
            
        elif context_type == 'comparison':
            # Extract plan prices from response
            prices = re.findall(r'₹?(\d{3,4})', new_query)
            if len(prices) >= 2:
                enhanced_query = f"Compare ₹{prices[0]} vs ₹{prices[1]} plans"
            else:
                enhanced_query = f"Compare plans: {new_query}"
        
        elif context_type == '5g_check':
            # Extract city name
            enhanced_query = f"Check 5G availability in {new_query}"
        
        elif context_type == 'budget_plan':
            # Extract budget
            budget_match = re.search(r'₹?(\d{3,4})', new_query)
            if budget_match:
                enhanced_query = f"Best plans under ₹{budget_match.group(1)}"
            else:
                enhanced_query = f"Cheapest plans {new_query}"
        
        else:
            # Generic merge
            enhanced_query = f"{original} - {new_query}"
        
        return enhanced_query


class JioOrchestrator:
    """Main orchestrator that manages all agents and their interactions"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the orchestrator with all agents"""
        
        print("\n🎭 Initializing Jio Multi-Agent Orchestrator...")
        
        # Configuration
        self.config = config or {}
        self.llm = ChatOpenAI(
            model=self.config.get("model", "gpt-3.5-turbo"),
            temperature=self.config.get("temperature", 0.7),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize follow-up manager
        self.followup_manager = FollowUpManager()
        
        # Initialize subsystems
        self._init_subsystems()
        
        # Initialize all agents
        self._init_agents()
        
        # Cache for common queries
        self.response_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Track orchestration metrics
        self.metrics = {
            "total_queries": 0,
            "successful_orchestrations": 0,
            "failed_orchestrations": 0,
            "direct_responses": 0,
            "follow_up_questions": 0,
            "rag_usage": 0,
            "mcp_usage": 0,
            "cache_hits": 0,
            "strategy_usage": {
                "direct": 0,
                "rag_mcp": 0,
                "sequential": 0,
                "hierarchical": 0,
                "parallel": 0,
                "consensus": 0
            }
        }
        
        print("✅ Orchestrator initialization complete!")
        self._print_system_status()
    
    def _init_subsystems(self):
        """Initialize RAG and MCP subsystems"""
        try:
            self.rag_system = JioRAGSystem()
            print("  ✅ RAG system initialized")
        except Exception as e:
            print(f"  ⚠️ RAG system failed: {e}")
            self.rag_system = None
        
        try:
            self.mcp_client = MCPClient()
            print("  ✅ MCP client initialized")
        except Exception as e:
            print(f"  ⚠️ MCP client failed: {e}")
            self.mcp_client = None
    
    def _init_agents(self):
        """Initialize all agents"""
        print("\n📦 Initializing Agents...")
        
        # Initialize Research Analyst
        self.research_agent = ResearchAnalystAgent(
            llm=self.llm,
            rag_system=self.rag_system,
            mcp_client=self.mcp_client
        )
        
        # Initialize Solution Architect
        self.architect_agent = SolutionArchitectAgent(
            llm=self.llm,
            mcp_client=self.mcp_client
        )
        
        # Initialize Customer Success Manager
        self.customer_agent = CustomerSuccessAgent(
            llm=self.llm
        )
        
        print("\n✅ All agents initialized successfully!")
    
    def _print_system_status(self):
        """Print the current system status"""
        print("\n" + "=" * 60)
        print("🎯 SYSTEM STATUS")
        print("=" * 60)
        
        print("\n📊 Agents:")
        for agent_wrapper in [self.research_agent, self.architect_agent, self.customer_agent]:
            caps = agent_wrapper.get_capabilities()
            print(f"  • {caps['name']}: Ready")
        
        print("\n🔧 Subsystems:")
        print(f"  • RAG System: {'✅ Active' if self.rag_system else '❌ Inactive'}")
        print(f"  • MCP Client: {'✅ Active' if self.mcp_client else '❌ Inactive'}")
        print(f"  • Follow-up Manager: ✅ Active")
        
        print("\n🎭 Available Strategies:")
        print("  • Direct: Instant response for simple queries")
        print("  • Follow-up: Ask clarifying questions for vague queries")
        print("  • RAG-MCP: Uses knowledge base and tools")
        print("  • Sequential: Step-by-step processing")
        print("  • Hierarchical: Manager-led delegation")
        print("  • Parallel: Concurrent processing")
        print("  • Consensus: Collaborative decision-making")
        
        print("=" * 60 + "\n")
    
    def orchestrate_with_followup(self, 
                                 query: str, 
                                 session_id: str = "default",
                                 strategy: str = "auto", 
                                 verbose: bool = True) -> Dict[str, Any]:
        """
        Enhanced orchestration with follow-up question capability
        """
        
        # Check if this is a follow-up response to a previous question
        context = self.followup_manager.get_context(session_id)
        if context:
            # This is a follow-up response, merge with context
            if verbose:
                print(f"  🔄 Processing follow-up response for: {context['original_query']}")
            
            # Merge the response with original context
            enhanced_query = self.followup_manager.merge_with_context(session_id, query)
            
            if verbose:
                print(f"  📝 Enhanced query: {enhanced_query}")
            
            # Clear the context since we're processing it
            self.followup_manager.clear_context(session_id)
            
            # Process the enhanced query normally
            return self.orchestrate(enhanced_query, strategy, verbose)
        
        # Check if the new query needs follow-up
        needs_followup, followup_question, context_type = self.followup_manager.needs_follow_up(query)
        
        if needs_followup:
            if verbose:
                print(f"  ❓ Query needs clarification: {query}")
                print(f"  💭 Context type: {context_type}")
            
            # Store context for when user responds
            self.followup_manager.store_context(session_id, query, context_type)
            
            # Track metrics
            self.metrics["follow_up_questions"] += 1
            
            # Return follow-up question instead of processing
            return {
                "success": True,
                "response": followup_question,
                "metadata": {
                    "type": "follow_up",
                    "waiting_for": context_type,
                    "original_query": query,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        # Process normally if no follow-up needed
        return self.orchestrate(query, strategy, verbose)
    
    def _get_rag_context(self, query: str, verbose: bool = True) -> str:
        """Get context from RAG system - ALWAYS for relevant queries"""
        if not self.rag_system:
            return ""
        
        try:
            context = self.rag_system.get_context(query)
            self.metrics["rag_usage"] += 1
            if verbose:
                print(f"  📚 RAG System: Retrieved {len(context)} chars of context")
            return context
        except Exception as e:
            if verbose:
                print(f"  ⚠️ RAG error: {e}")
            return ""
    
    def _get_mcp_data(self, query: str, verbose: bool = True) -> Dict[str, Any]:
        """Get data from MCP client - ENHANCED VERSION"""
        if not self.mcp_client:
            return {}
        
        mcp_data = {}
        query_lower = query.lower()
        
        try:
            # 1. ALWAYS search for plans if any plan-related keyword is mentioned
            plan_keywords = ['plan', 'mobile', 'recharge', 'prepaid', 'postpaid', 
                           'fiber', 'broadband', 'jio', 'data', 'validity']
            if any(keyword in query_lower for keyword in plan_keywords):
                search_result = self.mcp_client.search_plans(query, "all")
                if search_result and "No plans found" not in search_result:
                    mcp_data["plan_search"] = search_result
                    self.metrics["mcp_usage"] += 1
                    if verbose:
                        print(f"  🔧 MCP: Searched for relevant plans")
            
            # 2. Check for specific plan prices (be more aggressive)
            prices = re.findall(r'\d{3,4}', query)
            for price in prices:
                if 100 <= int(price) <= 5000:  # Reasonable price range
                    details = self.mcp_client.get_plan_details(price)
                    if details and "Could not find" not in details:
                        mcp_data[f"plan_{price}"] = details
                        self.metrics["mcp_usage"] += 1
                        if verbose:
                            print(f"  🔧 MCP: Retrieved ₹{price} plan details")
            
            # 3. Check for comparisons
            comparison_keywords = ['compare', 'vs', 'versus', 'better', 'difference', 'which']
            if any(word in query_lower for word in comparison_keywords):
                # Try to extract two prices for comparison
                if len(prices) >= 2:
                    comparison = self.mcp_client.compare_plans(prices[0], prices[1])
                    if comparison and "Could not compare" not in comparison:
                        mcp_data["comparison"] = comparison
                        self.metrics["mcp_usage"] += 1
                        if verbose:
                            print(f"  🔧 MCP: Compared ₹{prices[0]} vs ₹{prices[1]}")
                elif len(prices) == 1:
                    # Compare with popular alternative
                    popular_alternatives = {'199': '299', '299': '399', '399': '599'}
                    if prices[0] in popular_alternatives:
                        comparison = self.mcp_client.compare_plans(
                            prices[0], 
                            popular_alternatives[prices[0]]
                        )
                        if comparison and "Could not compare" not in comparison:
                            mcp_data["comparison"] = comparison
                            self.metrics["mcp_usage"] += 1
                            if verbose:
                                print(f"  🔧 MCP: Auto-compared with alternative")
            
            # 4. Check for 5G queries
            if '5g' in query_lower or 'five g' in query_lower:
                # Extract city if mentioned
                cities = ["mumbai", "delhi", "bangalore", "chennai", "kolkata", 
                         "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow",
                         "kanpur", "nagpur", "visakhapatnam", "bhopal", "patna"]
                
                city = "Mumbai"  # Default city
                for c in cities:
                    if c in query_lower:
                        city = c.title()
                        break
                
                availability = self.mcp_client.check_5g_availability(city)
                if availability:
                    mcp_data["5g_availability"] = availability
                    self.metrics["mcp_usage"] += 1
                    if verbose:
                        print(f"  🔧 MCP: Checked 5G availability in {city}")
            
            # 5. Get recommendations based on user type or requirements
            user_indicators = {
                'student': ['student', 'college', 'university', 'study', 'campus'],
                'family': ['family', 'home', 'parents', 'kids', 'household'],
                'professional': ['professional', 'work', 'office', 'business', 'job', 'meeting'],
                'business': ['business', 'company', 'enterprise', 'corporate', 'startup']
            }
            
            detected_user_type = None
            for user_type, keywords in user_indicators.items():
                if any(keyword in query_lower for keyword in keywords):
                    detected_user_type = user_type
                    break
            
            # Also check for general recommendation requests
            recommendation_keywords = ['recommend', 'suggest', 'best', 'good', 'suitable', 'ideal']
            if detected_user_type or any(word in query_lower for word in recommendation_keywords):
                # Determine usage level
                if 'heavy' in query_lower or 'lot' in query_lower or 'high' in query_lower:
                    usage = "high"
                elif 'light' in query_lower or 'basic' in query_lower or 'low' in query_lower:
                    usage = "low"
                else:
                    usage = "medium"
                
                # Extract budget
                budget = None
                budget_patterns = [
                    r'under\s*₹?\s*(\d{3,4})',
                    r'budget\s*₹?\s*(\d{3,4})',
                    r'less\s*than\s*₹?\s*(\d{3,4})',
                    r'max\s*₹?\s*(\d{3,4})',
                    r'below\s*₹?\s*(\d{3,4})'
                ]
                
                for pattern in budget_patterns:
                    match = re.search(pattern, query_lower)
                    if match:
                        budget = float(match.group(1))
                        break
                
                # Get recommendation
                user_type = detected_user_type or "general"
                recommendation = self.mcp_client.recommend_plan(user_type, usage, budget)
                if recommendation and "Could not generate" not in recommendation:
                    mcp_data["recommendation"] = recommendation
                    self.metrics["mcp_usage"] += 1
                    if verbose:
                        print(f"  🔧 MCP: Generated {user_type} recommendations (usage: {usage}, budget: {budget})")
            
            # 6. Check for specific features or requirements
            if 'unlimited' in query_lower or 'ott' in query_lower or 'netflix' in query_lower:
                search_result = self.mcp_client.search_plans(query, "all")
                if search_result and "No plans found" not in search_result:
                    mcp_data["feature_search"] = search_result
                    self.metrics["mcp_usage"] += 1
                    if verbose:
                        print(f"  🔧 MCP: Searched for specific features")
            
        except Exception as e:
            if verbose:
                print(f"  ⚠️ MCP error: {e}")
        
        return mcp_data
    
    def _get_query_complexity(self, query: str) -> str:
        """Determine query complexity - FIXED to ensure RAG/MCP usage"""
        query_lower = query.lower().strip()
        word_count = len(query.split())
        
        # ONLY mark as simple for pure greetings (nothing else!)
        greetings = ['hi', 'hello', 'hey', 'namaste', 'good morning', 'good evening']
        if query_lower in greetings and word_count <= 2:
            return "simple"
        
        # If query is just "thanks" or similar
        thanks = ['thanks', 'thank you', 'bye', 'goodbye', 'ok', 'okay']
        if query_lower in thanks:
            return "simple"
        
        # EVERYTHING ELSE should use RAG/MCP
        # Any query with these keywords should NEVER be simple
        force_tool_keywords = [
            # Prices
            '199', '299', '399', '599', '999', '1499',
            # Plan keywords
            'plan', 'price', 'cost', 'rupee', '₹', 'recharge',
            'prepaid', 'postpaid', 'mobile', 'fiber', 'broadband',
            # Service keywords
            '5g', 'data', 'validity', 'gb', 'mbps', 'speed',
            'unlimited', 'calls', 'sms', 'ott', 'apps',
            # Action keywords
            'details', 'show', 'tell', 'what', 'which', 'how',
            'give', 'provide', 'explain', 'list',
            # Comparison keywords
            'compare', 'versus', 'vs', 'better', 'best', 'good',
            'difference', 'choose', 'recommend', 'suggest',
            # User types
            'student', 'family', 'professional', 'business',
            'work', 'home', 'office',
            # Question indicators
            'jio', 'available', 'offer', 'benefit', 'feature'
        ]
        
        # If ANY of these keywords exist, it's at least medium complexity
        if any(keyword in query_lower for keyword in force_tool_keywords):
            # Check if it's complex
            if any(word in query_lower for word in [
                'compare', 'versus', 'vs', 'calculate', 'design', 
                'bundle', 'complete solution', 'multiple', 'all'
            ]):
                return "complex"
            return "medium"
        
        # Even general questions should use tools
        if '?' in query or any(word in query_lower.split() for word in ['what', 'which', 'how', 'when', 'where', 'why']):
            return "medium"
        
        # Default to medium to ensure tool usage
        return "medium"
    
    def orchestrate(self, query: str, strategy: str = "auto", verbose: bool = True, 
                   force_tools: bool = False, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Main orchestration method with ENHANCED RAG and MCP integration
        
        Args:
            query: User query
            strategy: Orchestration strategy
            verbose: Print detailed logs
            force_tools: Force RAG/MCP usage even for simple queries
            skip_cache: Skip cache lookup
        """
        start_time = time.time()
        self.metrics["total_queries"] += 1
        
        if verbose:
            print(f"\n🎯 New Orchestration Request")
            print(f"  Query: {query}")
            print(f"  Strategy: {strategy}")
            print(f"  Force Tools: {force_tools}")
            print("-" * 50)
        
        # Check cache (unless skipped)
        cache_key = f"{query}:{strategy}"
        if not skip_cache and cache_key in self.response_cache:
            cached_response, cached_time = self.response_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                self.metrics["cache_hits"] += 1
                if verbose:
                    print("  ⚡ Cache hit - returning cached response")
                cached_response["metadata"]["cached"] = True
                cached_response["metadata"]["duration"] = time.time() - start_time
                return cached_response
        
        # Determine complexity
        complexity = self._get_query_complexity(query)
        if verbose:
            print(f"  📊 Query Complexity: {complexity}")
        
        # Handle direct responses ONLY for truly simple queries
        if complexity == "simple" and not force_tools:
            direct_result = self._handle_direct_response(query)
            if direct_result and direct_result.get("response"):
                self.metrics["direct_responses"] += 1
                self.metrics["strategy_usage"]["direct"] += 1
                
                duration = time.time() - start_time
                
                result = {
                    "success": True,
                    "response": direct_result["response"],
                    "metadata": {
                        "strategy": "direct",
                        "duration": duration,
                        "timestamp": datetime.now().isoformat(),
                        "agents_used": 0,
                        "complexity": complexity,
                        "rag_used": False,
                        "mcp_used": False
                    }
                }
                
                # Cache the response
                if not skip_cache:
                    self.response_cache[cache_key] = (result, time.time())
                
                if verbose:
                    print(f"  ⚡ Direct response in {duration:.2f}s")
                
                return result
        
        # For ALL non-simple queries, ALWAYS use RAG and MCP
        if verbose:
            print("\n🔄 ORCHESTRATION WITH RAG & MCP")
            print("  ℹ️ Gathering context from knowledge systems...")
        
        # ALWAYS gather context from RAG for non-simple queries
        rag_context = ""
        if complexity != "simple" or force_tools:
            rag_context = self._get_rag_context(query, verbose)
        
        # ALWAYS gather data from MCP for non-simple queries
        mcp_data = {}
        if complexity != "simple" or force_tools:
            mcp_data = self._get_mcp_data(query, verbose)
        
        # Log what we got
        if verbose:
            if rag_context:
                print(f"  ✅ RAG provided context ({len(rag_context)} chars)")
            else:
                print(f"  ⚠️ No RAG context retrieved")
            
            if mcp_data:
                print(f"  ✅ MCP provided {len(mcp_data)} data points: {list(mcp_data.keys())}")
            else:
                print(f"  ⚠️ No MCP data retrieved")
        
        # Auto-select strategy if needed
        if strategy == "auto":
            strategy = self._select_strategy(query, complexity)
            if verbose:
                print(f"  🎯 Auto-selected strategy: {strategy}")
        
        # Track strategy usage
        if rag_context or mcp_data:
            self.metrics["strategy_usage"]["rag_mcp"] += 1
        elif strategy in self.metrics["strategy_usage"]:
            self.metrics["strategy_usage"][strategy] += 1
        
        # Execute orchestration with RAG and MCP context
        try:
            if verbose:
                print(f"\n🚀 Executing {strategy.upper()} orchestration...")
            
            if strategy == "sequential":
                result = self._orchestrate_sequential_with_context(query, rag_context, mcp_data, verbose)
            elif strategy == "hierarchical":
                result = self._orchestrate_hierarchical_with_context(query, rag_context, mcp_data, verbose)
            elif strategy == "parallel":
                result = self._orchestrate_parallel_with_context(query, rag_context, mcp_data, verbose)
            elif strategy == "consensus":
                result = self._orchestrate_consensus_with_context(query, rag_context, mcp_data, verbose)
            else:
                # Default to sequential
                result = self._orchestrate_sequential_with_context(query, rag_context, mcp_data, verbose)
            
            self.metrics["successful_orchestrations"] += 1
            
            # Add metadata
            duration = time.time() - start_time
            
            response = {
                "success": True,
                "response": result,
                "metadata": {
                    "strategy": strategy,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat(),
                    "agents_used": 1,
                    "complexity": complexity,
                    "rag_used": bool(rag_context),
                    "mcp_used": bool(mcp_data),
                    "mcp_tools_called": list(mcp_data.keys()) if mcp_data else [],
                    "context_size": len(rag_context) + sum(len(str(v)) for v in mcp_data.values())
                }
            }
            
            # Cache the response
            if not skip_cache:
                self.response_cache[cache_key] = (response, time.time())
            
            if verbose:
                print(f"\n  ✅ Response generated in {duration:.2f}s")
                print(f"  📊 RAG Used: {bool(rag_context)}, MCP Used: {bool(mcp_data)}")
                if mcp_data:
                    print(f"  🔧 MCP Tools Called: {list(mcp_data.keys())}")
            
            return response
            
        except Exception as e:
            self.metrics["failed_orchestrations"] += 1
            print(f"❌ Orchestration failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "response": self._get_intelligent_fallback(query),
                "error": str(e),
                "metadata": {
                    "strategy": strategy,
                    "timestamp": datetime.now().isoformat(),
                    "complexity": complexity
                }
            }
    
    def _orchestrate_sequential_with_context(self, query: str, rag_context: str, mcp_data: Dict, verbose: bool) -> str:
        """Sequential orchestration with RAG and MCP context"""
        if verbose:
            print("\n📄 SEQUENTIAL ORCHESTRATION WITH CONTEXT")
        
        # Prepare context string
        context_parts = []
        
        if rag_context:
            context_parts.append(f"📚 Knowledge Base Information:\n{rag_context}")
        
        if mcp_data:
            for key, value in mcp_data.items():
                if key == "comparison":
                    context_parts.append(f"📊 Plan Comparison:\n{value}")
                elif key.startswith("plan_"):
                    context_parts.append(f"📱 Plan Details:\n{value}")
                elif key == "5g_availability":
                    context_parts.append(f"🌐 5G Information:\n{value}")
                elif key == "recommendation":
                    context_parts.append(f"💡 Recommendations:\n{value}")
                elif key == "plan_search":
                    context_parts.append(f"🔍 Search Results:\n{value}")
                elif key == "feature_search":
                    context_parts.append(f"✨ Feature Search:\n{value}")
        
        full_context = "\n\n".join(context_parts) if context_parts else "No additional context available."
        
        # Create comprehensive task with context
        comprehensive_task = Task(
            description=f"""
            User Query: '{query}'
            
            AVAILABLE INFORMATION FROM SYSTEMS:
            {full_context}
            
            Instructions:
            1. USE THE PROVIDED CONTEXT to answer accurately
            2. If plan details are provided above, use those EXACT details
            3. If comparison is provided, present it clearly
            4. Format response with bullets and emojis for readability
            5. Include prices in ₹ (Indian Rupees)
            6. Be friendly, helpful, and specific
            7. If recommendations are provided, present them clearly
            8. DO NOT make up information - use only what's provided above
            9. Keep responses concise but complete - use bullet points where appropriate
            
            Provide a complete, accurate, and helpful response based on the context above.
            """,
            agent=self.research_agent.get_agent(),
            expected_output="Complete response using provided context with bullet points for clarity"
        )
        
        # Create simplified crew
        crew = Crew(
            agents=[self.research_agent.get_agent()],
            tasks=[comprehensive_task],
            process=Process.sequential,
            verbose=verbose,
            max_rpm=30
        )
        
        result = crew.kickoff()
        return str(result)
    
    def _orchestrate_parallel_with_context(self, query: str, rag_context: str, mcp_data: Dict, verbose: bool) -> str:
        """Fast parallel orchestration with context"""
        if verbose:
            print("\n⚡ PARALLEL ORCHESTRATION WITH CONTEXT")
        
        # Prepare urgent context
        context = ""
        if mcp_data:
            # Get most relevant MCP data for speed
            for key, value in mcp_data.items():
                context += f"\n{value[:500]}"  # Limit context for speed
                if len(context) > 1000:  # Cap total context
                    break
        elif rag_context:
            context = rag_context[:1000]  # Limit for speed
        
        urgent_task = Task(
            description=f"""
            URGENT Query: '{query}'
            
            Quick Context:
            {context}
            
            Provide immediate, actionable response using the context!
            Be specific with plan details and prices.
            """,
            agent=self.architect_agent.get_agent(),
            expected_output="Quick actionable response"
        )
        
        crew = Crew(
            agents=[self.architect_agent.get_agent()],
            tasks=[urgent_task],
            process=Process.sequential,
            verbose=verbose,
            max_rpm=30
        )
        
        result = crew.kickoff()
        return str(result)
    
    def _orchestrate_consensus_with_context(self, query: str, rag_context: str, mcp_data: Dict, verbose: bool) -> str:
        """Consensus orchestration for comparisons with context"""
        if verbose:
            print("\n🤝 CONSENSUS ORCHESTRATION WITH CONTEXT")
        
        # Focus on comparison data
        comparison_context = ""
        if mcp_data.get("comparison"):
            comparison_context = mcp_data["comparison"]
        
        # Add individual plan details if available
        for key, value in mcp_data.items():
            if key.startswith("plan_"):
                comparison_context += f"\n\n{value}"
        
        # Add RAG context if no MCP comparison
        if not comparison_context and rag_context:
            comparison_context = rag_context
        
        comparison_task = Task(
            description=f"""
            Compare and analyze: '{query}'
            
            Comparison Data:
            {comparison_context}
            
            Requirements:
            - Show side-by-side comparison with specific details
            - Calculate value metrics (daily cost, total data, cost per GB)
            - Provide clear recommendation with reasoning
            - Use ₹ for all prices
            - Format with bullets and emojis
            - Highlight the winner clearly
            - Explain WHY one is better than the other
            
            Create a detailed comparison that helps the user make an informed decision.
            """,
            agent=self.architect_agent.get_agent(),
            expected_output="Detailed comparison with recommendation"
        )
        
        crew = Crew(
            agents=[self.architect_agent.get_agent()],
            tasks=[comparison_task],
            process=Process.sequential,
            verbose=verbose,
            max_rpm=30
        )
        
        result = crew.kickoff()
        return str(result)
    
    def _orchestrate_hierarchical_with_context(self, query: str, rag_context: str, mcp_data: Dict, verbose: bool) -> str:
        """Hierarchical orchestration for complex queries with context"""
        if verbose:
            print("\n👑 HIERARCHICAL ORCHESTRATION WITH CONTEXT")
        
        # Combine all context
        full_context = ""
        if rag_context:
            full_context += f"📚 Knowledge Base:\n{rag_context}\n\n"
        
        if mcp_data:
            for key, value in mcp_data.items():
                if key == "plan_search":
                    full_context += f"🔍 Available Plans:\n{value}\n\n"
                elif key == "recommendation":
                    full_context += f"💡 Recommendations:\n{value}\n\n"
                elif key.startswith("plan_"):
                    full_context += f"📱 {key.replace('_', ' ').title()}:\n{value}\n\n"
                else:
                    full_context += f"{key.replace('_', ' ').title()}:\n{value}\n\n"
        
        manager_task = Task(
            description=f"""
            Design complete solution for: '{query}'
            
            Available Information:
            {full_context}
            
            As Solution Architect:
            1. Analyze ALL requirements from the query
            2. Design comprehensive solution using the provided information
            3. Include mobile plans, fiber, and add-ons as appropriate
            4. Calculate total costs and value propositions
            5. Provide clear, structured recommendations
            6. Consider bundles and family plans if relevant
            7. Use ₹ for all prices
            
            Create a complete, detailed solution package that addresses all needs.
            """,
            agent=self.architect_agent.get_agent(),
            expected_output="Complete solution bundle with all details"
        )
        
        crew = Crew(
            agents=[self.architect_agent.get_agent()],
            tasks=[manager_task],
            process=Process.sequential,
            verbose=verbose,
            max_rpm=30
        )
        
        result = crew.kickoff()
        return str(result)
    
    def _select_strategy(self, query: str, complexity: str = None) -> str:
        """Intelligently select the best orchestration strategy"""
        query_lower = query.lower()
        
        if not complexity:
            complexity = self._get_query_complexity(query)
        
        # Direct response for simple
        if complexity == "simple":
            return "direct"
        
        # Urgent queries - use parallel
        if any(word in query_lower for word in ['urgent', 'asap', 'immediately', 'now', 'quick']):
            return "parallel"
        
        # Comparison queries - use consensus
        if any(word in query_lower for word in ['compare', 'versus', 'vs', 'which is better', 'difference']):
            return "consensus"
        
        # Complex bundling - use hierarchical
        if any(word in query_lower for word in ['complete solution', 'bundle', 'family plan', 'design', 'multiple', 'everything']):
            return "hierarchical"
        
        # Default to sequential for standard queries
        return "sequential"
    
    def _handle_direct_response(self, query: str) -> Dict[str, Any]:
        """Handle simple queries with direct responses"""
        query_lower = query.lower().strip()
        
        # Greetings
        greetings = ['hi', 'hello', 'hey', 'namaste', 'good morning', 'good evening']
        if any(greeting in query_lower for greeting in greetings):
            return {
                "response": """Hello! 👋 Welcome to Jio AI Assistant!

I can help you with:
• 📱 Mobile Plans (₹199, ₹299, ₹399, ₹599)
• 🏠 JioFiber Broadband (₹699, ₹999, ₹1499)
• 🚀 5G Services (Free with all plans!)
• 💰 Personalized recommendations

What would you like to know today?"""
            }
        
        # Thanks
        if any(word in query_lower for word in ['thanks', 'thank you', 'dhanyawad']):
            return {
                "response": "You're welcome! 😊 Feel free to ask if you need any more information about Jio plans or services!"
            }
        
        # Goodbye
        if any(word in query_lower for word in ['bye', 'goodbye', 'see you']):
            return {
                "response": "Goodbye! 👋 Thank you for choosing Jio. Have a great day!"
            }
        
        return {"response": None}
    
    def _get_intelligent_fallback(self, query: str) -> str:
        """Enhanced fallback response when orchestration fails"""
        return """I apologize for the inconvenience. Let me provide you with our popular plans:

📱 **Mobile Plans:**
• ₹199 - 1.5GB/day for 28 days
• ₹299 - 2GB/day for 28 days
• ₹399 - 3GB/day for 56 days (Best Value!)
• ₹599 - 3GB/day for 84 days

🏠 **JioFiber:**
• ₹699 - 30 Mbps
• ₹999 - 100 Mbps with OTT apps
• ₹1499 - 300 Mbps with Netflix & Prime

All plans include unlimited calls and free 5G!

Please try rephrasing your question or ask about specific plans!"""
    
    def clear_cache(self):
        """Clear the response cache"""
        self.response_cache = {}
        print("✅ Cache cleared")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestration metrics"""
        total = self.metrics["total_queries"]
        if total > 0:
            self.metrics["success_rate"] = (self.metrics["successful_orchestrations"] / total) * 100
            self.metrics["rag_usage_rate"] = (self.metrics["rag_usage"] / total) * 100
            self.metrics["mcp_usage_rate"] = (self.metrics["mcp_usage"] / total) * 100
            self.metrics["cache_hit_rate"] = (self.metrics["cache_hits"] / total) * 100
            self.metrics["direct_response_rate"] = (self.metrics["direct_responses"] / total) * 100
            self.metrics["follow_up_rate"] = (self.metrics["follow_up_questions"] / total) * 100
        return self.metrics
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "research": self.research_agent.get_capabilities(),
            "architect": self.architect_agent.get_capabilities(),
            "customer": self.customer_agent.get_capabilities()
        }