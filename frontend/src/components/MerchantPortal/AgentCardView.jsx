import React, { useState } from 'react';
import { Bot, Globe, Shield, RefreshCw, Check, Copy, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';

export function AgentCardView({ merchant, onSyncCompleted }) {
  const [syncing, setSyncing] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);

  const handleManualSync = async () => {
    setSyncing(true);
    try {
      await api.syncStore();
      if (onSyncCompleted) onSyncCompleted();
    } catch (err) {
      alert(err.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const agentCardUrl = `${window.location.origin}/.well-known/agent.json?merchant_id=${merchant.merchant_id}`;

  const copyCardUrl = () => {
    navigator.clipboard.writeText(agentCardUrl);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  return (
    <div className="glass-panel" style={{ padding: '28px', marginBottom: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="badge badge-emerald">
              <CheckCircle2 size={12} /> Live on Node
            </span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Slug: <code style={{ color: '#38BDF8' }}>{merchant.merchant_id}</code>
            </span>
          </div>
          <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#fff' }}>
            {merchant.merchant_name}
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            Category: <strong style={{ color: '#fff' }}>{merchant.category}</strong> • Currency: <strong style={{ color: '#fff' }}>{merchant.currency}</strong>
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleManualSync}
            disabled={syncing}
            className="btn btn-secondary btn-sm"
          >
            <RefreshCw size={14} className={syncing ? 'spin' : ''} />
            {syncing ? 'Syncing...' : 'Sync Catalog'}
          </button>
          <a
            href={agentCardUrl}
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary btn-sm"
          >
            <Globe size={14} />
            View agent.json
          </a>
        </div>
      </div>

      {/* 3 Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Max Discount Cap
          </span>
          <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#38BDF8', marginTop: '4px' }}>
            {merchant.max_discount_percentage}%
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>Deterministic clamp ceiling</span>
        </div>

        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Single Tx Spend Cap
          </span>
          <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#818CF8', marginTop: '4px' }}>
            ₹{merchant.per_tx_spend_cap?.toLocaleString()}
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>Atomic Redis Lua gate</span>
        </div>

        <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Daily Spend Cap
          </span>
          <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#10B981', marginTop: '4px' }}>
            ₹{merchant.daily_merchant_spend_cap?.toLocaleString()}
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>24h rolling volume limit</span>
        </div>
      </div>

      {/* Discovery Card Endpoint Box */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(3, 7, 18, 0.7)',
        border: '1px solid var(--border)',
        borderRadius: '10px',
        padding: '10px 14px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
          <Bot size={16} color="#38BDF8" />
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>UAP Agent Discovery Card:</span>
          <code style={{ fontSize: '12px', color: '#38BDF8', textOverflow: 'ellipsis', overflow: 'hidden' }}>
            {agentCardUrl}
          </code>
        </div>
        <button
          onClick={copyCardUrl}
          className="btn btn-secondary btn-sm"
          style={{ flexShrink: 0 }}
        >
          {copiedUrl ? <Check size={14} /> : <Copy size={14} />}
          {copiedUrl ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  );
}
