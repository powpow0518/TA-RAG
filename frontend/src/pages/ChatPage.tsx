import React, { useEffect, useRef, useState } from 'react';
import { Send } from 'lucide-react';

import { useCourse } from '../App';

interface Message {
  text: string;
  sender: 'user' | 'bot';
}

const ChatPage: React.FC = () => {
  const { currentCourse } = useCourse();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => Math.random().toString(36).substring(7));
  const [followUp, setFollowUp] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    setMessages([]);
    setFollowUp(null);
    setSessionId(Math.random().toString(36).substring(7));
  }, [currentCourse]);

  const handleSend = async (overrideInput?: string) => {
    const textToSend = overrideInput || input;
    if (!textToSend.trim() || isLoading || !currentCourse) return;

    const userMessage: Message = { text: textToSend, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setFollowUp(null);
    setIsLoading(true);

    try {
      const response = await fetch('/api/v1/rag/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          query: textToSend,
          course_id: currentCourse.course_id,
          session_id: sessionId,
        }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let botContent = '';

      setMessages((prev) => [...prev, { text: '', sender: 'bot' }]);

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;
        const chunk = decoder.decode(value);

        if (chunk.includes('{"type": "follow_up"')) {
          try {
            const parts = chunk.split('\n');
            for (const part of parts) {
              if (part.startsWith('{"type": "follow_up"')) {
                const followUpData = JSON.parse(part);
                setFollowUp(followUpData.content);
              } else {
                botContent += part;
              }
            }
          } catch (e) {
            console.error('Failed to parse follow-up JSON', e);
            botContent += chunk;
          }
        } else {
          botContent += chunk;
        }

        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].text = botContent;
          return newMessages;
        });
      }
    } catch (error) {
      console.error('Error fetching RAG response:', error);
      setMessages((prev) => [...prev, { text: 'Something went wrong while asking the assistant.', sender: 'bot' }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!currentCourse) return <div style={{ padding: '20px' }}>Please select a course first.</div>;

  return (
    <div className="chat-container">
      <div className="chat-header">
        Active course: <strong style={{ color: 'var(--primary-color)' }}>{currentCourse.course_name}</strong> ({currentCourse.course_id})
      </div>
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div
            key={index}
            style={{ marginBottom: '1rem', textAlign: message.sender === 'user' ? 'right' : 'left' }}
          >
            <div className={`chat-bubble ${message.sender === 'user' ? 'user' : 'bot'}`}>
              {message.text}
            </div>
          </div>
        ))}
        {isLoading && <p className="muted" style={{ fontSize: '0.9rem' }}>Thinking...</p>}

        {followUp && !isLoading && (
          <div style={{ marginTop: '1rem', textAlign: 'left' }}>
            <p className="muted" style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>Suggested follow-up</p>
            <button
              onClick={() => handleSend(followUp)}
              style={{
                backgroundColor: 'rgba(255,255,255,0.04)',
                border: '1px solid var(--primary-color)',
                color: 'var(--primary-color)',
                padding: '0.5rem 1rem',
                textAlign: 'left',
                maxWidth: '90%',
                display: 'block',
              }}
            >
              {followUp}
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={`Ask something about ${currentCourse.course_name}...`}
        />
        <button onClick={() => handleSend()} disabled={isLoading}>
          <Send size={20} />
        </button>
      </div>
    </div>
  );
};

export default ChatPage;
