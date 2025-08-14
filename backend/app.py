"""
Flask Application with Follow-up Questions Feature
Enhanced version with session management and intelligent clarification
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import time
import uuid
from orchestrator import JioOrchestrator
import os
# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*", supports_credentials=True, methods=["GET", "POST", "OPTIONS"])
# Set OpenAI API Key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Initialize the orchestrator
orchestrator = None
try:
    orchestrator = JioOrchestrator(config={
        "model": "gpt-3.5-turbo",
        "temperature": 0.7
    })
    print("\n✅ Jio Orchestrator ready with Follow-up Support!")
except Exception as e:
    print(f"\n❌ Orchestrator initialization failed: {e}")

# Track session conversations (in production, use Redis or database)
conversation_history = {}
session_contexts = {}  # Track follow-up contexts

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'orchestrator': orchestrator is not None,
        'timestamp': datetime.now().isoformat(),
        'metrics': orchestrator.get_metrics() if orchestrator else None,
        'features': {
            'follow_up_questions': True,
            'rag_system': orchestrator.rag_system is not None if orchestrator else False,
            'mcp_client': orchestrator.mcp_client is not None if orchestrator else False
        }
    })

@app.route('/init', methods=['GET', 'OPTIONS'])
def initialize():
    """Initialize and get system status"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    if orchestrator:
        metrics = orchestrator.get_metrics()
        return jsonify({
            'status': 'initialized',
            'agents': orchestrator.get_agent_status(),
            'metrics': metrics,
            'capabilities': {
                'total_tools': sum(agent['tool_count'] for agent in orchestrator.get_agent_status().values()),
                'strategies': ['direct', 'follow_up', 'tool_only', 'sequential', 'hierarchical', 'parallel', 'consensus', 'auto'],
                'subsystems': {
                    'rag': orchestrator.rag_system is not None,
                    'mcp': orchestrator.mcp_client is not None,
                    'follow_up': True
                }
            },
            'follow_up_stats': {
                'total_follow_ups': metrics.get('follow_up_questions', 0),
                'follow_up_rate': f"{metrics.get('follow_up_rate', 0):.1f}%"
            }
        })
    
    return jsonify({'status': 'not_initialized', 'error': 'Orchestrator failed to load'}), 500

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    """Main chat endpoint with follow-up question support"""
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        # Extract request data
        data = request.json
        user_message = data.get('message', '')
        
        # Session management - critical for follow-ups
        session_id = data.get('session_id')
        if not session_id:
            # Generate new session ID if not provided
            session_id = str(uuid.uuid4())
            print(f"  📝 Generated new session ID: {session_id}")
        
        strategy = data.get('strategy', 'auto')
        verbose = data.get('verbose', False)
        force_tools = data.get('force_tools', False)
        skip_cache = data.get('skip_cache', False)
        
        # Log incoming request
        print(f"\n{'='*60}")
        print(f"📨 New Message: {user_message}")
        print(f"   Session: {session_id}")
        print(f"   Strategy: {strategy}")
        
        # Check if this might be a follow-up response
        if session_id in session_contexts:
            print(f"   🔄 Possible follow-up response for session {session_id}")
        
        # Track conversation history
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        
        conversation_history[session_id].append({
            'role': 'user',
            'message': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Check if orchestrator is available
        if not orchestrator:
            fallback_response = get_enhanced_fallback_response(user_message)
            print(f"   ⚠️ Using fallback (orchestrator not available)")
            return jsonify({
                'response': fallback_response,
                'error': 'Orchestrator not initialized',
                'fallback': True,
                'session_id': session_id
            }), 200
        
        # Process with orchestrator (with follow-up support)
        result = orchestrator.orchestrate_with_followup(
            query=user_message,
            session_id=session_id,  # Pass session ID for context tracking
            strategy=strategy,
            verbose=verbose
        )
        
        # Check if this is a follow-up question
        is_follow_up = result.get('metadata', {}).get('type') == 'follow_up'
        
        if is_follow_up:
            # Store that this session is waiting for follow-up
            session_contexts[session_id] = {
                'waiting_for': result['metadata'].get('waiting_for'),
                'original_query': result['metadata'].get('original_query'),
                'timestamp': time.time()
            }
            print(f"   ❓ Asking follow-up question")
            print(f"   💭 Waiting for: {result['metadata'].get('waiting_for')}")
        else:
            # Clear follow-up context if it existed
            if session_id in session_contexts:
                del session_contexts[session_id]
                print(f"   ✅ Follow-up context resolved")
        
        # Log performance metrics
        if result.get('metadata') and not is_follow_up:
            meta = result['metadata']
            print(f"\n📊 Performance Metrics:")
            print(f"   ✅ Strategy Used: {meta.get('strategy', 'unknown')}")
            print(f"   ⏱️  Response Time: {meta.get('duration', 0):.2f}s")
            print(f"   📈 Complexity: {meta.get('complexity', 'unknown')}")
            print(f"   🤖 Agents Used: {meta.get('agents_used', 0)}")
            print(f"   📚 RAG Used: {meta.get('rag_used', False)}")
            print(f"   🔧 MCP Used: {meta.get('mcp_used', False)}")
            
            # Log efficiency
            duration = meta.get('duration', 0)
            if duration < 1:
                print(f"   ⚡ FAST RESPONSE!")
            elif duration < 3:
                print(f"   ✅ Good response time")
            elif duration < 5:
                print(f"   ⚠️  Acceptable response time")
            else:
                print(f"   🐌 SLOW RESPONSE - Needs optimization")
        
        # Track conversation
        conversation_history[session_id].append({
            'role': 'assistant',
            'message': result['response'],
            'metadata': result.get('metadata'),
            'is_follow_up': is_follow_up,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"{'='*60}\n")
        
        # Prepare response
        response_data = {
            'response': result['response'],
            'metadata': result['metadata'],
            'success': True,
            'session_id': session_id,  # Always return session ID
            'is_follow_up': is_follow_up  # Indicate if this is a follow-up question
        }
        
        # Add follow-up context if applicable
        if is_follow_up:
            response_data['follow_up_context'] = {
                'waiting_for': result['metadata'].get('waiting_for'),
                'original_query': result['metadata'].get('original_query')
            }
        
        return jsonify(response_data)
            
    except Exception as e:
        print(f"\n❌ Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        # Generate session ID if not present
        if 'session_id' not in locals():
            session_id = str(uuid.uuid4())
        
        fallback_response = get_enhanced_fallback_response(data.get('message', ''))
        return jsonify({
            'response': fallback_response,
            'error': str(e),
            'success': False,
            'fallback': True,
            'session_id': session_id
        }), 200

@app.route('/session/new', methods=['GET'])
def new_session():
    """Create a new session ID"""
    session_id = str(uuid.uuid4())
    return jsonify({
        'session_id': session_id,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/session/<session_id>/context', methods=['GET'])
def get_session_context(session_id):
    """Get the current follow-up context for a session"""
    if session_id in session_contexts:
        context = session_contexts[session_id]
        return jsonify({
            'session_id': session_id,
            'has_pending_followup': True,
            'waiting_for': context.get('waiting_for'),
            'original_query': context.get('original_query'),
            'age_seconds': time.time() - context.get('timestamp', 0)
        })
    
    return jsonify({
        'session_id': session_id,
        'has_pending_followup': False
    })

@app.route('/session/<session_id>/clear', methods=['POST'])
def clear_session_context(session_id):
    """Clear follow-up context for a session"""
    if session_id in session_contexts:
        del session_contexts[session_id]
        return jsonify({
            'status': 'cleared',
            'session_id': session_id
        })
    
    return jsonify({
        'status': 'no_context',
        'session_id': session_id
    })

@app.route('/agents', methods=['GET'])
def get_agents():
    """Get detailed information about all agents"""
    if not orchestrator:
        return jsonify({'error': 'Orchestrator not initialized'}), 500
    
    agent_status = orchestrator.get_agent_status()
    
    # Add more details
    for agent_name, info in agent_status.items():
        info['status'] = 'active'
        info['description'] = {
            'research': 'Gathers information from knowledge base and MCP tools',
            'architect': 'Designs solutions and makes technical recommendations',
            'customer': 'Creates friendly, personalized responses for users'
        }.get(agent_name, 'Multi-purpose agent')
    
    return jsonify(agent_status)

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get detailed orchestration metrics including follow-up stats"""
    if not orchestrator:
        return jsonify({'error': 'Orchestrator not initialized'}), 500
    
    metrics = orchestrator.get_metrics()
    
    # Add conversation stats
    metrics['conversations'] = {
        'total_sessions': len(conversation_history),
        'total_messages': sum(len(conv) for conv in conversation_history.values()),
        'active_sessions': len([s for s in conversation_history.values() if len(s) > 0]),
        'sessions_with_pending_followup': len(session_contexts)
    }
    
    # Add follow-up stats
    metrics['follow_up_stats'] = {
        'total_follow_ups': metrics.get('follow_up_questions', 0),
        'follow_up_rate': f"{metrics.get('follow_up_rate', 0):.1f}%",
        'pending_contexts': len(session_contexts),
        'active_followup_sessions': list(session_contexts.keys())
    }
    
    # Add performance stats
    if metrics.get('total_queries', 0) > 0:
        metrics['performance'] = {
            'avg_direct_response': f"{metrics.get('direct_response_rate', 0):.1f}%",
            'avg_cache_hit': f"{metrics.get('cache_hit_rate', 0):.1f}%",
            'success_rate': f"{metrics.get('success_rate', 0):.1f}%",
            'follow_up_rate': f"{metrics.get('follow_up_rate', 0):.1f}%"
        }
    
    return jsonify(metrics)

@app.route('/strategies', methods=['GET'])
def get_strategies():
    """Get detailed information about available orchestration strategies"""
    return jsonify({
        'strategies': [
            {
                'name': 'direct',
                'description': 'Instant response without agent orchestration',
                'best_for': 'Simple queries, greetings, basic information',
                'speed': 'Instant (<0.5s)',
                'agents_used': 0
            },
            {
                'name': 'follow_up',
                'description': 'Ask clarifying questions for vague queries',
                'best_for': 'Incomplete queries needing more context',
                'speed': 'Instant (<0.5s)',
                'agents_used': 0
            },
            {
                'name': 'tool_only',
                'description': 'Direct tool usage without full agent orchestration',
                'best_for': 'Specific plan queries, simple lookups',
                'speed': 'Very Fast (<1s)',
                'agents_used': 0
            },
            {
                'name': 'sequential',
                'description': 'Step-by-step processing with research focus',
                'best_for': 'Standard queries requiring analysis',
                'speed': 'Medium (2-3s)',
                'agents_used': 1
            },
            {
                'name': 'hierarchical',
                'description': 'Manager-led delegation for complex solutions',
                'best_for': 'Complex bundles, family plans, complete solutions',
                'speed': 'Slower (3-5s)',
                'agents_used': 2
            },
            {
                'name': 'parallel',
                'description': 'Fast processing for urgent queries',
                'best_for': 'Urgent queries needing quick response',
                'speed': 'Fast (1-2s)',
                'agents_used': 1
            },
            {
                'name': 'consensus',
                'description': 'Comparison-focused analysis',
                'best_for': 'Plan comparisons, evaluations',
                'speed': 'Medium (2-4s)',
                'agents_used': 1
            },
            {
                'name': 'auto',
                'description': 'System selects optimal strategy',
                'best_for': 'Let AI decide based on query',
                'speed': 'Variable',
                'agents_used': 'Variable'
            }
        ],
        'selection_logic': {
            'vague_queries': 'follow_up',
            'simple_queries': 'direct',
            'specific_plans': 'tool_only',
            'urgent_queries': 'parallel',
            'comparison_queries': 'consensus',
            'complex_bundles': 'hierarchical',
            'standard_queries': 'sequential'
        }
    })

@app.route('/test', methods=['POST'])
def test_orchestration():
    """Test endpoint for trying different strategies"""
    data = request.json
    query = data.get('query', 'What are the best Jio mobile plans?')
    test_all = data.get('test_all', False)
    session_id = data.get('session_id', 'test_' + str(uuid.uuid4()))
    
    if not orchestrator:
        return jsonify({'error': 'Orchestrator not initialized'}), 500
    
    if test_all:
        # Test all strategies
        results = {}
        strategies = ['direct', 'sequential', 'parallel', 'consensus']
        
        for strategy in strategies:
            try:
                print(f"\nTesting strategy: {strategy}")
                start = time.time()
                
                # Use regular orchestrate for testing (not follow-up version)
                result = orchestrator.orchestrate(query, strategy, verbose=False)
                duration = time.time() - start
                
                results[strategy] = {
                    'success': result['success'],
                    'response_preview': result['response'][:200] + '...' if len(result['response']) > 200 else result['response'],
                    'duration': duration,
                    'agents_used': result['metadata'].get('agents_used', 0),
                    'rag_used': result['metadata'].get('rag_used', False),
                    'mcp_used': result['metadata'].get('mcp_used', False)
                }
            except Exception as e:
                results[strategy] = {'error': str(e)}
        
        # Test follow-up detection
        followup_result = orchestrator.orchestrate_with_followup(query, session_id + '_followup')
        results['follow_up_detection'] = {
            'needs_followup': followup_result.get('metadata', {}).get('type') == 'follow_up',
            'context_type': followup_result.get('metadata', {}).get('waiting_for')
        }
        
        # Determine best strategy
        best_strategy = min(
            [s for s in results if s != 'follow_up_detection' and results[s].get('success')],
            key=lambda s: results[s]['duration'],
            default='auto'
        )
        
        return jsonify({
            'query': query,
            'results': results,
            'recommendation': best_strategy
        })
    else:
        # Test single query with follow-up support
        result = orchestrator.orchestrate_with_followup(query, session_id, 'auto', verbose=True)
        return jsonify({
            'query': query,
            'session_id': session_id,
            'result': result
        })

@app.route('/test/followup', methods=['POST'])
def test_followup_flow():
    """Test complete follow-up flow"""
    data = request.json
    initial_query = data.get('initial_query', 'best plan')
    followup_response = data.get('followup_response', 'under 300, student')
    
    if not orchestrator:
        return jsonify({'error': 'Orchestrator not initialized'}), 500
    
    # Generate test session ID
    test_session = 'test_' + str(uuid.uuid4())
    
    # Step 1: Initial vague query
    result1 = orchestrator.orchestrate_with_followup(initial_query, test_session)
    
    # Step 2: Follow-up response
    result2 = None
    if result1.get('metadata', {}).get('type') == 'follow_up':
        result2 = orchestrator.orchestrate_with_followup(followup_response, test_session)
    
    return jsonify({
        'test_session': test_session,
        'step1': {
            'query': initial_query,
            'is_followup': result1.get('metadata', {}).get('type') == 'follow_up',
            'response': result1['response'][:300] + '...' if len(result1['response']) > 300 else result1['response']
        },
        'step2': {
            'query': followup_response,
            'response': result2['response'][:300] + '...' if result2 and len(result2['response']) > 300 else result2['response'] if result2 else None
        } if result2 else None
    })

@app.route('/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """Get conversation history for a session"""
    if session_id not in conversation_history:
        return jsonify({'error': 'Session not found'}), 404
    
    # Check if session has pending follow-up
    has_pending_followup = session_id in session_contexts
    
    return jsonify({
        'session_id': session_id,
        'messages': conversation_history[session_id],
        'message_count': len(conversation_history[session_id]),
        'has_pending_followup': has_pending_followup,
        'pending_context': session_contexts.get(session_id) if has_pending_followup else None
    })

@app.route('/clear-history/<session_id>', methods=['DELETE'])
def clear_history(session_id):
    """Clear conversation history and follow-up context for a session"""
    cleared = False
    
    if session_id in conversation_history:
        conversation_history[session_id] = []
        cleared = True
    
    if session_id in session_contexts:
        del session_contexts[session_id]
        cleared = True
    
    if cleared:
        return jsonify({'status': 'cleared', 'session_id': session_id})
    
    return jsonify({'error': 'Session not found'}), 404

@app.route('/debug/last-query', methods=['GET'])
def debug_last_query():
    """Debug endpoint to see details of the last query processed"""
    if not orchestrator:
        return jsonify({'error': 'Orchestrator not initialized'}), 500
    
    metrics = orchestrator.get_metrics()
    
    # Get most recent conversation
    recent_session = None
    recent_messages = []
    
    for session_id, messages in conversation_history.items():
        if messages:
            recent_session = session_id
            recent_messages = messages[-2:] if len(messages) >= 2 else messages
    
    # Check if recent session has pending follow-up
    has_followup = recent_session in session_contexts if recent_session else False
    
    return jsonify({
        'last_session': recent_session,
        'last_exchange': recent_messages,
        'has_pending_followup': has_followup,
        'followup_context': session_contexts.get(recent_session) if has_followup else None,
        'total_queries': metrics.get('total_queries', 0),
        'follow_up_questions': metrics.get('follow_up_questions', 0),
        'strategy_distribution': metrics.get('strategy_usage', {}),
        'performance': {
            'success_rate': f"{metrics.get('success_rate', 0):.1f}%",
            'cache_hit_rate': f"{metrics.get('cache_hit_rate', 0):.1f}%",
            'direct_response_rate': f"{metrics.get('direct_response_rate', 0):.1f}%",
            'follow_up_rate': f"{metrics.get('follow_up_rate', 0):.1f}%"
        }
    })

@app.route('/cleanup', methods=['POST'])
def cleanup_old_sessions():
    """Clean up old sessions and follow-up contexts"""
    max_age_seconds = request.json.get('max_age_seconds', 3600)  # Default 1 hour
    current_time = time.time()
    
    # Clean up old follow-up contexts
    old_contexts = []
    for session_id, context in list(session_contexts.items()):
        age = current_time - context.get('timestamp', 0)
        if age > max_age_seconds:
            old_contexts.append(session_id)
            del session_contexts[session_id]
    
    return jsonify({
        'cleaned_contexts': len(old_contexts),
        'cleaned_sessions': old_contexts,
        'remaining_contexts': len(session_contexts)
    })

# ============================================================================
# ENHANCED FALLBACK RESPONSES
# ============================================================================

def get_enhanced_fallback_response(message: str) -> str:
    """Enhanced fallback responses with better intent recognition"""
    if not message:
        return "Please type a message to get started!"
    
    message_lower = message.lower().strip()
    
    # Greetings
    greetings = ['hi', 'hello', 'hey', 'namaste', 'good morning', 'good evening']
    if any(greeting in message_lower for greeting in greetings):
        return """Hello! 👋 Welcome to Jio AI Assistant!
        
I can help you find the perfect Jio plan. Try asking:
• "Show me plans under 300"
• "Details of 299 plan"
• "Compare 299 vs 399"
• "Best plan for students"
• "Check 5G availability"

What would you like to know?"""
    
    # Specific plan queries
    if '299' in message_lower:
        return """📱 ₹299 Plan Details:

• Data: 2GB per day
• Validity: 28 days
• Daily Cost: ₹10.68
• Total Data: 56GB

Includes:
✅ Unlimited voice calls
✅ 100 SMS/day
✅ Free 5G access
✅ Jio Apps subscription

Perfect for regular users! Want to compare or activate?"""
    
    elif '399' in message_lower:
        return """📱 ₹399 Plan Details:

• Data: 3GB per day
• Validity: 56 days (Double!)
• Daily Cost: ₹7.13
• Total Data: 168GB

Includes:
✅ Unlimited voice calls
✅ 100 SMS/day
✅ Free 5G access
✅ Jio Apps subscription

🏆 BEST VALUE - Lower daily cost with more data!
Ready to activate?"""
    
    # Student queries
    elif "student" in message_lower:
        return """📚 Perfect Plans for Students:

**Budget-Friendly:**
• ₹155 - 2GB/day for 24 days
• ₹199 - 1.5GB/day for 28 days

**Popular Choice:**
• ₹299 - 2GB/day for 28 days

**Best Value:**
• ₹399 - 3GB/day for 56 days

All include unlimited calls and free 5G!
Which fits your budget?"""
    
    # Comparison queries
    elif any(word in message_lower for word in ['compare', 'vs', 'versus', 'better']):
        return """📊 Popular Jio Plan Comparisons:

**₹299 vs ₹399:**
• ₹299: 2GB/day for 28 days = ₹10.68/day
• ₹399: 3GB/day for 56 days = ₹7.13/day
🏆 Winner: ₹399 for better value!

**₹199 vs ₹299:**
• ₹199: 1.5GB/day = ₹7.11/day
• ₹299: 2GB/day = ₹10.68/day
🏆 Choice: ₹199 for budget, ₹299 for more data

Which comparison interests you?"""
    
    # JioFiber queries
    elif any(word in message_lower for word in ['fiber', 'broadband', 'wifi']):
        return """🏠 JioFiber Plans:

**Basic:** ₹699/month
• 30 Mbps speed
• Unlimited data
• Free voice calling

**Popular:** ₹999/month
• 100 Mbps speed
• Unlimited data
• 14 OTT apps included

**Premium:** ₹1499/month
• 300 Mbps speed
• Unlimited data
• Netflix, Prime, and more

All plans include free installation!
Which speed suits your needs?"""
    
    # Default response
    return """Welcome to Jio! Here are our popular services:

📱 **Mobile Plans:**
• ₹199 - 1.5GB/day, 28 days
• ₹299 - 2GB/day, 28 days
• ₹399 - 3GB/day, 56 days (Best Value!)

🏠 **JioFiber Broadband:**
• ₹699 - 30 Mbps
• ₹999 - 100 Mbps
• ₹1499 - 300 Mbps

All plans include unlimited calls and free 5G!

Try asking:
- "Details of 299 plan"
- "Compare 299 vs 399"
- "Best plan for students"
- "JioFiber plans"

How can I help you today?"""

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 JIO CHATBOT SERVER - WITH FOLLOW-UP QUESTIONS")
    print("=" * 60)
    print(f"📍 Server: http://127.0.0.1:5001")
    print(f"🔧 OpenAI Key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"🎭 Orchestrator: {'✅ Ready' if orchestrator else '❌ Failed'}")
    
    if orchestrator:
        print("\n📊 Agent Configuration:")
        status = orchestrator.get_agent_status()
        for agent_name, info in status.items():
            print(f"  • {info['name']}: {info['tool_count']} tools")
        
        print("\n🎯 Enhanced Features:")
        print("  ✅ Follow-up Questions - Asks for clarification on vague queries")
        print("  ✅ Session Management - Tracks conversation context")
        print("  ✅ RAG Integration - Knowledge base search")
        print("  ✅ MCP Tools - Dynamic plan data")
        print("  ✅ Response Caching - Faster repeated queries")
        
        print("\n📝 Follow-up Scenarios:")
        print("  • 'best plan' → Asks for budget/usage/user type")
        print("  • 'compare' → Asks which plans to compare")
        print("  • '5g' → Asks for city location")
        print("  • 'cheapest' → Asks for budget range")
        print("  • 'help' → Asks what specific help needed")
    
    print("\n📡 API Endpoints:")
    print("  POST /chat                 - Main chat with follow-up support")
    print("  GET  /session/new          - Create new session ID")
    print("  GET  /session/<id>/context - Check follow-up context")
    print("  POST /session/<id>/clear   - Clear follow-up context")
    print("  GET  /agents               - List all agents")
    print("  GET  /strategies           - Available strategies")
    print("  GET  /metrics              - System metrics")
    print("  POST /test                 - Test strategies")
    print("  POST /test/followup        - Test follow-up flow")
    print("  GET  /history/<session>    - Get chat history")
    print("  GET  /debug/last-query     - Debug last query")
    print("  POST /cleanup              - Clean old sessions")
    
    print("\n✨ New Features:")
    print("  • Intelligent follow-up questions for vague queries")
    print("  • Session-based conversation tracking")
    print("  • Context preservation across messages")
    print("  • Automatic session ID generation")
    print("  • Follow-up metrics and monitoring")
    
    print("=" * 60 + "\n")
    
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, port=port, host='0.0.0.0')