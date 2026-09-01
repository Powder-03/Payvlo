import React, { useState } from 'react';
import { Sparkles, Copy, Check, MessageSquare, Utensils, Home, Bot } from 'lucide-react';

export function PromptHelper() {
  const [copiedIndex, setCopiedIndex] = useState(null);

  const copyPrompt = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const samplePrompts = [
    {
      category: 'Saved Address Shortcut',
      icon: <Home size={16} color="#38BDF8" />,
      badge: 'Home / Work Delivery',
      prompt: "Find a Margherita pizza from Domino's under ₹400, negotiate max discount, and order it to my 'Home' address with a ₹450 spend limit.",
      explanation: "The agent searches the catalog, gets a clamped quote, and calls execute_bounded_checkout with address_label='Home'."
    },
    {
      category: 'Dynamic Dine-In / In-Store',
      icon: <Utensils size={16} color="#F59E0B" />,
      badge: 'Dine-In Context',
      prompt: "Order 2 cheese pizzas from Domino's. I am dine-in at Kashmere Gate Metro Station Domino's, Table #4. My budget is ₹600.",
      explanation: "The agent parses your dynamic location + Table #4 and passes fulfillment_type='DINE_IN' into checkout without needing a pre-saved address."
    },
    {
      category: 'Autonomous Procurement',
      icon: <Bot size={16} color="#10B981" />,
      badge: 'Autonomous REST Bot',
      prompt: "Restock 2 units of 'Hyper-Whey Isolate Protein 2kg' from BeastLife Nutrition. Negotiate best quotation and settle within ₹5000 budget.",
      explanation: "Autonomous peer buyer bot flow using UAP A2A protocol (/.well-known/agent.json, /uap/v1/negotiate, /uap/v1/transact)."
    }
  ];

  return (
    <div className="glass-panel" style={{ padding: '28px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
        <div style={{
          width: '40px', height: '40px', borderRadius: '10px',
          background: 'rgba(129, 140, 248, 0.15)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#818CF8'
        }}>
          <Sparkles size={20} />
        </div>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff' }}>
            Interactive AI Prompt Assistant
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Try these real-world prompts in Antigravity chat or Claude Desktop:
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '14px' }}>
        {samplePrompts.map((p, idx) => (
          <div
            key={idx}
            style={{
              background: 'rgba(0, 0, 0, 0.3)',
              borderRadius: '12px',
              padding: '16px',
              border: '1px solid var(--border)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                {p.icon}
                {p.category}
              </span>
              <span className="badge badge-purple" style={{ fontSize: '11px', padding: '2px 8px' }}>
                {p.badge}
              </span>
            </div>

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'rgba(3, 7, 18, 0.7)',
              borderRadius: '8px',
              padding: '10px 14px',
              border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <span style={{ fontSize: '13px', color: '#F8FAFC', fontStyle: 'italic' }}>
                "{p.prompt}"
              </span>
              <button
                onClick={() => copyPrompt(p.prompt, idx)}
                className="btn btn-secondary btn-sm"
                style={{ marginLeft: '12px', flexShrink: 0, padding: '6px 10px' }}
                title="Copy Prompt"
              >
                {copiedIndex === idx ? <Check size={14} color="#10B981" /> : <Copy size={14} />}
                {copiedIndex === idx ? 'Copied' : 'Copy'}
              </button>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-subtle)', lineHeight: 1.4 }}>
              💡 {p.explanation}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
