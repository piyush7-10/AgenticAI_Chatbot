import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSpring, animated } from '@react-spring/web';
import { ReactTyped } from 'react-typed';
import Confetti from 'react-confetti';
import toast, { Toaster } from 'react-hot-toast';
import CountUp from 'react-countup';
import { useInView } from 'react-intersection-observer';
import { v4 as uuidv4 } from 'uuid';
import './App.css';
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

// Icons (using emoji for simplicity, or install lucide-react)
const Icons = {
  chat: '💬',
  close: '✕',
  send: '➤',
  sparkle: '✨',
  robot: '🤖',
  user: '👤',
  attachment: '📎',
  emoji: '😊'
};

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState([
    { 
      id: uuidv4(),
      type: 'bot', 
      text: 'Hey there! 👋 I\'m your Jio AI Assistant. How can I revolutionize your digital experience today?',
      timestamp: new Date(),
      animated: false
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [showConfetti, setShowConfetti] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [currentSuggestion, setCurrentSuggestion] = useState(0);
  
  const chatBodyRef = useRef(null);
  const inputRef = useRef(null);

  // Animated stats
  const [stats, setStats] = useState({
    users: 0,
    cities: 0,
    speed: 0
  });

  // Quick suggestions
  const suggestions = [
    "Show me 5G plans",
    "Compare ₹299 vs ₹399",
    "Best plan for students",
    "JioFiber speeds",
    "International roaming"
  ];

  // Initialize session
  useEffect(() => {
    fetch(`${API_URL}/session/new`)
      .then(res => res.json())
      .then(data => {
        setSessionId(data.session_id);
        toast.success('Connected to Jio AI', {
          icon: '🚀',
          duration: 2000
        });
      })
      .catch(err => {
        toast.error('Connection failed. Please check if backend is running.');
      });

    // Animate stats on load
    setTimeout(() => {
      setStats({
        users: 200000000,
        cities: 500,
        speed: 1000
      });
    }, 500);

    // Celebration on first visit
    const isFirstVisit = !localStorage.getItem('visited');
    if (isFirstVisit) {
      localStorage.setItem('visited', 'true');
      setTimeout(() => {
        setShowConfetti(true);
        setTimeout(() => setShowConfetti(false), 5000);
      }, 1000);
    }
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle send message
  const sendMessage = async () => {
    if (!inputMessage.trim()) {
      toast.error('Please type a message', { icon: '✍️' });
      return;
    }

    const userMsg = {
      id: uuidv4(),
      type: 'user',
      text: inputMessage,
      timestamp: new Date(),
      animated: true
    };

    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setIsTyping(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: inputMessage,
          session_id: sessionId 
        }),
      });

      const data = await response.json();
      
      // Check if it's a follow-up question
      if (data.is_follow_up) {
        toast('📝 Need more info...', { icon: '🤔' });
      }

      setTimeout(() => {
        const botMsg = {
          id: uuidv4(),
          type: 'bot',
          text: data.response,
          timestamp: new Date(),
          animated: true,
          metadata: data.metadata
        };
        setMessages(prev => [...prev, botMsg]);
        setIsTyping(false);

        // Special effects for certain responses
        if (data.response.includes('₹399')) {
          toast.success('Best value plan detected! 🎉');
        }
      }, 1000 + Math.random() * 1000);

    } catch (error) {
      setIsTyping(false);
      toast.error('Oops! Something went wrong');
      setMessages(prev => [...prev, {
        id: uuidv4(),
        type: 'bot',
        text: 'I\'m having connection issues. Please try again.',
        timestamp: new Date(),
        error: true
      }]);
    }
  };

  // Quick action handler
  const handleQuickAction = (action) => {
    setInputMessage(action);
    setTimeout(() => sendMessage(), 100);
  };

  return (
    <div className={`app ${isDarkMode ? 'dark' : 'light'}`}>
      {showConfetti && <Confetti />}
      <Toaster position="top-center" />

      {/* Animated Background */}
      <div className="animated-bg">
        <div className="gradient-orb orb-1" />
        <div className="gradient-orb orb-2" />
        <div className="gradient-orb orb-3" />
        <div className="particle-field" />
      </div>

      {/* Main Content */}
      <div className="main-container">
        {/* Hero Section */}
        <motion.div 
          className="hero-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div className="hero-badge">
            <span className="badge-icon">{Icons.sparkle}</span>
            <span>AI-Powered Telecom</span>
          </div>
          
          <h1 className="hero-title">
            <span className="gradient-text">Jio</span>
            <span className="ai-text">AI</span>
          </h1>
          
          <ReactTyped
            className="hero-subtitle"
            strings={[
              'Experience True 5G Speed',
              'Unlimited Possibilities',
              'India\'s Digital Revolution',
              'Connect. Create. Celebrate.'
            ]}
            typeSpeed={50}
            backSpeed={30}
            loop
          />

          {/* About Us Section - NEW */}
          <motion.div 
            className="about-section"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8 }}
          >
            <div className="about-content">
              <h2 className="about-title">Transforming Digital India</h2>
              <p className="about-description">
                Welcome to the future of connectivity. Jio has revolutionized how India connects, 
                communicates, and experiences the digital world. With our cutting-edge AI assistant, 
                we're making it easier than ever to find the perfect plan, explore our services, 
                and join millions in India's digital transformation journey.
              </p>
              
              <div className="about-highlights">
                <motion.div 
                  className="highlight-item"
                  whileHover={{ scale: 1.05, rotate: 1 }}
                >
                  <span className="highlight-icon">🚀</span>
                  <h3>Lightning Fast</h3>
                  <p>True 5G speeds up to 1 Gbps, powering your digital life</p>
                </motion.div>
                
                <motion.div 
                  className="highlight-item"
                  whileHover={{ scale: 1.05, rotate: -1 }}
                >
                  <span className="highlight-icon">🌟</span>
                  <h3>AI-Powered</h3>
                  <p>Smart recommendations tailored just for you</p>
                </motion.div>
                
                <motion.div 
                  className="highlight-item"
                  whileHover={{ scale: 1.05, rotate: 1 }}
                >
                  <span className="highlight-icon">💎</span>
                  <h3>Best Value</h3>
                  <p>Unbeatable plans starting at just ₹199</p>
                </motion.div>
              </div>
            </div>

            {/* Animated Stats - Integrated with About */}
            <div className="stats-container">
              <motion.div 
                className="stats-header"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <h3>Our Impact in Numbers</h3>
                <p>Join the digital revolution that's transforming India</p>
              </motion.div>
              
              <div className="stats-grid">
                <motion.div 
                  className="stat-card"
                  whileHover={{ scale: 1.05, boxShadow: '0 20px 40px rgba(0,0,0,0.3)' }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="stat-icon">👥</div>
                  <div className="stat-number">
                    <CountUp end={stats.users} duration={2} separator="," />+
                  </div>
                  <span className="stat-label">Happy Users</span>
                  <div className="stat-description">Largest network in India</div>
                </motion.div>
                
                <motion.div 
                  className="stat-card"
                  whileHover={{ scale: 1.05, boxShadow: '0 20px 40px rgba(0,0,0,0.3)' }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="stat-icon">🏙️</div>
                  <div className="stat-number">
                    <CountUp end={stats.cities} duration={2} />+
                  </div>
                  <span className="stat-label">Cities with 5G</span>
                  <div className="stat-description">Pan-India coverage</div>
                </motion.div>
                
                <motion.div 
                  className="stat-card"
                  whileHover={{ scale: 1.05, boxShadow: '0 20px 40px rgba(0,0,0,0.3)' }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="stat-icon">⚡</div>
                  <div className="stat-number">
                    <CountUp end={stats.speed} duration={2} />
                  </div>
                  <span className="stat-label">Mbps Speed</span>
                  <div className="stat-description">Lightning-fast connectivity</div>
                </motion.div>
              </div>
            </div>

            {/* Mission Statement */}
            <motion.div 
              className="mission-statement"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
            >
              <blockquote>
                "Empowering every Indian with affordable, world-class digital services. 
                Together, we're building a connected India where dreams meet opportunities."
              </blockquote>
              <cite>— Team Jio</cite>
            </motion.div>
          </motion.div>
        </motion.div>

        {/* Feature Cards */}
        <div className="features-grid">
          {[
            { 
              icon: '📱', 
              title: 'Mobile Plans', 
              desc: 'Starting ₹199', 
              gradient: 'gradient-1' 
            },
            { 
              icon: '🌐', 
              title: 'JioFiber', 
              desc: 'Up to 1 Gbps', 
              gradient: 'gradient-2' 
            },
            { 
              icon: '🚀', 
              title: 'True 5G', 
              desc: 'Unlimited Free', 
              gradient: 'gradient-3' 
            },
            { 
              icon: '🎬', 
              title: 'OTT Apps', 
              desc: '15+ Platforms', 
              gradient: 'gradient-4' 
            }
          ].map((feature, index) => (
            <motion.div
              key={index}
              className={`feature-card ${feature.gradient}`}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ 
                scale: 1.05,
                boxShadow: '0 20px 40px rgba(0,0,0,0.3)'
              }}
            >
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.desc}</p>
              <div className="feature-glow" />
            </motion.div>
          ))}
        </div>
      </div>

      {/* Floating Chat Button */}
      <motion.button
        className="chat-fab"
        onClick={() => setIsChatOpen(!isChatOpen)}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        animate={{ rotate: isChatOpen ? 90 : 0 }}
      >
        {isChatOpen ? Icons.close : Icons.chat}
        <span className="chat-fab-pulse" />
      </motion.button>

      {/* Chat Interface */}
      <AnimatePresence>
        {isChatOpen && (
          <motion.div
            className="chat-window"
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            transition={{ type: "spring", damping: 20 }}
          >
            {/* Chat Header */}
            <div className="chat-header">
              <div className="chat-header-info">
                <div className="chat-avatar">
                  <span>{Icons.robot}</span>
                  <span className="online-indicator" />
                </div>
                <div>
                  <h3>Jio AI Assistant</h3>
                  <span className="chat-status">
                    {isTyping ? 'Typing...' : 'Online'}
                  </span>
                </div>
              </div>
              <div className="chat-header-actions">
                <button 
                  className="theme-toggle"
                  onClick={() => setIsDarkMode(!isDarkMode)}
                >
                  {isDarkMode ? '🌙' : '☀️'}
                </button>
                <button onClick={() => setIsChatOpen(false)}>
                  {Icons.close}
                </button>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
              {suggestions.map((suggestion, idx) => (
                <motion.button
                  key={idx}
                  className="quick-action-pill"
                  onClick={() => handleQuickAction(suggestion)}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {suggestion}
                </motion.button>
              ))}
            </div>

            {/* Chat Body */}
            <div className="chat-body" ref={chatBodyRef}>
              <AnimatePresence>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    className={`message-wrapper ${msg.type}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                  >
                    <div className="message-avatar">
                      {msg.type === 'bot' ? Icons.robot : Icons.user}
                    </div>
                    <div className={`message-bubble ${msg.error ? 'error' : ''}`}>
                      <div className="message-text" style={{whiteSpace: 'pre-line'}}>{msg.text}</div>
                      <div className="message-time">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Typing Indicator */}
              {isTyping && (
                <motion.div 
                  className="typing-indicator"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <span></span>
                  <span></span>
                  <span></span>
                </motion.div>
              )}
            </div>

            {/* Chat Input */}
            <div className="chat-input-container">
              <input
                ref={inputRef}
                type="text"
                className="chat-input"
                placeholder="Ask about plans, 5G, or anything..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              />
              <button 
                className="send-btn"
                onClick={sendMessage}
                disabled={!inputMessage.trim()}
              >
                {Icons.send}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;