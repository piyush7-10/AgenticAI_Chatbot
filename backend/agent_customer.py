"""
Customer Success Manager Agent - WORKING VERSION
Works without tools parameter in CrewAI Agent
"""

from crewai import Agent
from langchain_openai import ChatOpenAI
import os
from typing import List, Dict, Any
from datetime import datetime
import random

class CustomerSuccessAgent:
    """Customer Success Manager - Focuses on customer experience and communication"""
    
    def __init__(self, llm=None):
        """Initialize the Customer Success Manager Agent"""
        
        # Use provided LLM or create new one
        self.llm = llm or ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.8,  # Higher temperature for more creative, friendly responses
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create tools (for reference, not passed to Agent)
        self.tools = self._create_tools()
        
        # Create the agent WITHOUT tools parameter
        self.agent = self._create_agent()
        
        print("✅ Customer Success Manager Agent initialized")
    
    def _create_tools(self) -> List:
        """Create tool functions that can be called directly"""
        tools = []
        
        def format_jio_response(content: str, style: str = "friendly") -> str:
            """Format response with proper styling"""
            styles = {
                "friendly": {
                    "greeting": "Hello! 😊",
                    "closing": "Is there anything else I can help you with today?",
                },
                "professional": {
                    "greeting": "Good day!",
                    "closing": "Please let me know if you need any clarification.",
                },
                "enthusiastic": {
                    "greeting": "Hey there! 🎉",
                    "closing": "Can't wait to help you get started! 🚀",
                },
                "student": {
                    "greeting": "Hey! 📚",
                    "closing": "Hope this helps with your studies! Any other questions?",
                }
            }
            
            style_config = styles.get(style, styles["friendly"])
            
            formatted = f"{style_config['greeting']}\n\n"
            formatted += content
            formatted += f"\n\n{style_config['closing']}"
            
            return formatted
        
        def create_followup_questions(context: str) -> str:
            """Create appropriate follow-up questions"""
            context_lower = context.lower()
            
            followups = {
                "plan_selection": [
                    "Would you like to know more about the benefits included?",
                    "Should I explain the activation process?",
                    "Do you want to compare with other similar plans?"
                ],
                "comparison": [
                    "Would you like a more detailed comparison?",
                    "Should I explain the specific benefits of each plan?"
                ],
                "general": [
                    "Is there anything specific you'd like to know more about?",
                    "Can I help you with plan activation?"
                ]
            }
            
            # Determine category
            if any(word in context_lower for word in ["plan", "price", "₹", "299", "399"]):
                category = "plan_selection"
            elif any(word in context_lower for word in ["compare", "versus", "vs"]):
                category = "comparison"
            else:
                category = "general"
            
            return random.choice(followups[category])
        
        # Store tool functions for direct access
        self.format_jio_response = format_jio_response
        self.create_followup_questions = create_followup_questions
        
        tools = [format_jio_response, create_followup_questions]
        return tools
    
    def _create_agent(self) -> Agent:
        """Create the Customer Success Manager agent WITHOUT tools parameter"""
        backstory = """You are an award-winning Customer Success Manager at Jio.
        
        GOLDEN RULE: Be friendly but BRIEF. Use bullets, not paragraphs.
        
        GREETING FORMAT:
        "Welcome! Let's find your perfect Jio plan! 😊"
        
        PLAN PRESENTATION:
        📱 ₹XXX Plan:
        • Data: X GB/day
        • Validity: X days  
        • Daily cost: ₹XX
        • Best for: [3-4 words]
        
        COMPARISON FORMAT:
        Quick Comparison:
        • ₹299: 2GB/day, ₹10.68/day
        • ₹399: 3GB/day, ₹7.13/day
        • 🏆 Pick ₹399 for better value
        
        STUDENT FORMAT:
        Student Plans 📚:
        • Tight budget: ₹199
        • Regular use: ₹299
        • Best value: ₹399
        
        KEY POINTS (always mention):
        • All plans: Unlimited calls + FREE 5G
        • ₹399 = Best value
        • No hidden charges
        
        BANNED PHRASES:
        • "comprehensive package"
        • "extensive benefits"
        • "wide range of"
        • Any corporate jargon
        
        CLOSING:
        "Ready to activate? Any questions?"
        
        Keep responses under 8-10 bullet points total.
        One emoji per section maximum.
        Be warm but GET TO THE POINT."""
        
        return Agent(
            role='Jio Customer Success - Brief & Friendly',
            goal='Help customers quickly with minimal words',
            backstory=backstory,
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=2
        )
    
    def craft_response(self, 
                      technical_info: str, 
                      user_type: str = "general",
                      sentiment: str = "neutral") -> str:
        """Craft a customer-friendly response from technical information"""
        
        # Structure the response
        response_structure = {
            "greeting": self._get_greeting(user_type, sentiment),
            "acknowledgment": self._acknowledge_query(sentiment),
            "main_content": self._simplify_technical_content(technical_info),
            "benefits": self._highlight_benefits(technical_info),
            "next_steps": self._suggest_next_steps(user_type),
            "closing": self._get_closing(user_type)
        }
        
        # Build the response
        response = f"{response_structure['greeting']}\n\n"
        response += f"{response_structure['acknowledgment']}\n\n"
        response += f"{response_structure['main_content']}\n\n"
        
        if response_structure['benefits']:
            response += f"✨ Key Benefits:\n{response_structure['benefits']}\n\n"
        
        response += f"{response_structure['next_steps']}\n\n"
        response += response_structure['closing']
        
        return response
    
    def _get_greeting(self, user_type: str, sentiment: str) -> str:
        """Get appropriate greeting based on context"""
        greetings = {
            ("student", "positive"): "Hey there! 📚 Great to hear from you!",
            ("student", "negative"): "Hi! 📚 I'm here to help sort this out.",
            ("student", "neutral"): "Hello! 📚 Thanks for choosing Jio!",
            ("professional", "positive"): "Good day! 💼 Delighted to assist you.",
            ("professional", "negative"): "Hello! 💼 I understand your concern.",
            ("professional", "neutral"): "Welcome! 💼 How can I help you today?",
            ("family", "positive"): "Hello! 👨‍👩‍👧‍👦 Wonderful to help your family!",
            ("family", "negative"): "Hi there! 👨‍👩‍👧‍👦 Let's resolve this together.",
            ("family", "neutral"): "Welcome! 👨‍👩‍👧‍👦 Happy to help!",
        }
        
        return greetings.get((user_type, sentiment), "Hello! 😊 Welcome to Jio!")
    
    def _acknowledge_query(self, sentiment: str) -> str:
        """Acknowledge the customer's query appropriately"""
        acknowledgments = {
            "positive": "I'm excited to help you find the perfect Jio solution!",
            "negative": "I completely understand your concern, and I'm here to help.",
            "urgent": "I see this is urgent - let me help you immediately.",
            "neutral": "I'd be happy to help you with that."
        }
        
        return acknowledgments.get(sentiment, acknowledgments["neutral"])
    
    def _simplify_technical_content(self, technical_info: str) -> str:
        """Simplify technical information for customers"""
        
        # Ensure Indian context
        simplified = technical_info.replace("$", "₹")
        simplified = simplified.replace("dollars", "rupees")
        
        # Simplify terms
        replacements = {
            "bandwidth": "internet speed",
            "Mbps": "Mbps (speed)",
            "GB": "GB (data)",
            "validity": "active days",
            "OTT": "streaming apps"
        }
        
        for tech_term, simple_term in replacements.items():
            simplified = simplified.replace(tech_term, simple_term)
        
        return simplified
    
    def _highlight_benefits(self, content: str) -> str:
        """Extract and highlight key Jio benefits"""
        content_lower = content.lower()
        benefits = []
        
        if "unlimited" in content_lower or len(benefits) == 0:
            benefits.append("• Unlimited calling to all networks")
        if "5g" in content_lower or len(benefits) < 2:
            benefits.append("• Free 5G access included")
        if "299" in content:
            benefits.append("• Perfect 2GB daily data for all needs")
        if "399" in content:
            benefits.append("• Best value with 56-day validity")
        if len(benefits) < 3:
            benefits.append("• 100 SMS/day included")
        
        return "\n".join(benefits) if benefits else ""
    
    def _suggest_next_steps(self, user_type: str) -> str:
        """Suggest appropriate next steps"""
        next_steps = {
            "student": "📚 Ready to activate? It's quick and easy!",
            "professional": "💼 Should I help you with quick activation?",
            "family": "👨‍👩‍👧‍👦 Would you like to add family members for extra savings?",
            "general": "📱 Ready to get started? I can guide you through activation!"
        }
        
        return next_steps.get(user_type, next_steps["general"])
    
    def _get_closing(self, user_type: str) -> str:
        """Get appropriate closing"""
        closings = {
            "student": "Let me know if you need anything else! Happy studying! 🌟",
            "professional": "Please don't hesitate to reach out for any clarification.",
            "family": "Happy to help your family stay connected! 😊",
            "general": "Is there anything else I can help you with today? 😊"
        }
        
        return closings.get(user_type, closings["general"])
    
    def get_agent(self) -> Agent:
        """Return the CrewAI agent"""
        return self.agent
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": "Customer Success Manager",
            "role": self.agent.role,
            "tools": [func.__name__ for func in self.tools],
            "tool_count": len(self.tools),
            "can_delegate": self.agent.allow_delegation,
            "specialties": [
                "Customer communication",
                "Empathetic responses",
                "Message personalization",
                "Sentiment analysis",
                "Activation guidance",
                "Customer satisfaction"
            ]
        }