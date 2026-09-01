import React from 'react';
import { Bot, Store, ShieldCheck, Zap, ArrowRight, CheckCircle2, Sparkles, Key, MapPin, Terminal } from 'lucide-react';

export function LandingHero({ persona, onPersonaChange, onOpenAuth }) {
  const isBuyer = persona === 'buyer';

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '48px 16px', textAlign: 'center' }}>
      {/* Top Badge */}
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 16px',
        borderRadius: '30px',
        background: isBuyer ? 'rgba(56, 189, 248, 0.12)' : 'rgba(16, 185, 129, 0.12)',
        border: `1px solid ${isBuyer ? 'rgba(56, 189, 248, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
        color: isBuyer ? '#38BDF8' : '#10B981',
        fontSize: '13px',
        fontWeight: 600,
        marginBottom: '24px'
      }}>
        <Sparkles size={14} />
        {isBuyer ? 'AI Agent Commerce Node & Address Vault' : 'Multi-Tenant Agentic Commerce Gateway'}
      </div>

      {/* Main Headline */}
      <h1 style={{
        fontSize: 'clamp(36px, 5vw, 56px)',
        fontWeight: 900,
        lineHeight: 1.15,
        marginBottom: '20px',
        background: 'linear-gradient(135deg, #FFFFFF 20%, #94A3B8 100%)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent'
      }}>
        {isBuyer ? (
          <>Empower Your AI Agents to <span style={{ color: '#38BDF8', WebkitTextFillColor: '#38BDF8' }}>Buy Anywhere</span></>
        ) : (
          <>Make Your Store Discoverable by <span style={{ color: '#10B981', WebkitTextFillColor: '#10B981' }}>Millions of AI Agents</span></>
        )}
      </h1>

      {/* Subheading */}
      <p style={{
        fontSize: '18px',
        lineHeight: 1.6,
        color: 'var(--text-muted)',
        maxWidth: '780px',
        margin: '0 auto 36px auto'
      }}>
        {isBuyer ? (
          'Connect Claude Desktop, Antigravity, or Cursor IDE to live stores. Save your home & work addresses, or order dine-in on-the-fly with mathematical spend caps.'
        ) : (
          'Connect your Shopify, WooCommerce, or Custom REST catalog in 30 seconds. Enable autonomous buyer agents to search, negotiate bounded discounts, and settle orders safely.'
        )}
      </p>

      {/* CTA Buttons */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap', marginBottom: '48px' }}>
        <button
          onClick={() => onOpenAuth('signup')}
          className={`btn ${isBuyer ? 'btn-primary' : 'btn-purple'}`}
          style={{ padding: '14px 28px', fontSize: '15px' }}
        >
          {isBuyer ? 'Get Free MCP API Key' : 'Onboard Your Store'}
          <ArrowRight size={16} />
        </button>
        <button
          onClick={() => onOpenAuth('login')}
          className="btn btn-secondary"
          style={{ padding: '14px 24px', fontSize: '15px' }}
        >
          Sign In to Portal
        </button>
      </div>

      {/* 3 Feature Highlights Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '20px',
        textAlign: 'left',
        marginTop: '20px'
      }}>
        {isBuyer ? (
          <>
            <div className="glass-panel-interactive" style={{ padding: '24px' }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '10px',
                background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', color: '#38BDF8', marginBottom: '16px'
              }}>
                <Key size={20} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                1-Click MCP API Key
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Generate a permanent JWT token with ready-to-paste snippets for Antigravity (<code style={{ color: '#38BDF8' }}>mcp_config.json</code>), Claude Desktop, and Python.
              </p>
            </div>

            <div className="glass-panel-interactive" style={{ padding: '24px' }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '10px',
                background: 'rgba(129, 140, 248, 0.15)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', color: '#818CF8', marginBottom: '16px'
              }}>
                <MapPin size={20} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                Smart Address Book & Dine-In
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Save "Home" and "Work" shortcuts or tell your agent you're dine-in at a metro station. The node auto-resolves addresses dynamically.
              </p>
            </div>

            <div className="glass-panel-interactive" style={{ padding: '24px' }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '10px',
                background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', color: '#10B981', marginBottom: '16px'
              }}>
                <ShieldCheck size={20} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                Zero-Trust Spend Bounds
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Atomic Redis Lua spend gates protect your budget. Agents cannot overspend or double-charge, backed by 24h idempotency.
              </p>
            </div>
          </>
        ) : (
          <>
            <div className="glass-panel-interactive" style={{ padding: '24px' }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '10px',
                background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', color: '#10B981', marginBottom: '16px'
              }}>
                <Store size={20} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                30-Second Shopify & REST Sync
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Connect your Shopify store or custom API. Products, variants, and stock counts sync automatically in real-time.
              </p>
            </div>

            <div className="glass-panel-interactive" style={{ padding: '24px' }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '10px',
                background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', color: '#38BDF8', marginBottom: '16px'
              }}>
                <ShieldCheck size={20} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                Deterministic Discount Ceilings
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Set max discount caps (e.g. 15%). Prompt injections and AI hallucinations are clamped down mathematically before checkout.
              </p>
            </div>

            <div className="glass-panel-interactive" style={{ padding: '24px' }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '10px',
                background: 'rgba(129, 140, 248, 0.15)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', color: '#818CF8', marginBottom: '16px'
              }}>
                <Terminal size={20} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                UAP / A2A Agent Card
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Automatically generates <code style={{ color: '#818CF8' }}>/.well-known/agent.json</code> discovery cards for peer-to-peer autonomous buyer bots.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
