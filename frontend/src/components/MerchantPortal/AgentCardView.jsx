import React, { useState } from 'react';
import { RefreshCw, Check, Copy, ExternalLink } from 'lucide-react';
import { api } from '../../services/api';

export function AgentCardView({ merchant, orders = [], onSyncCompleted }) {
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

  const totalRevenue = orders.reduce((sum, o) => sum + (o.final_amount || 0), 0);

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '12px',
      padding: '22px 24px',
      marginBottom: '20px'
    }}>
      {/* Top Bar: Title & Actions */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        flexWrap: 'wrap',
        gap: '16px',
        marginBottom: '20px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>
              {merchant.merchant_name}
            </h2>
            <span style={{
              fontSize: '11px',
              fontWeight: 500,
              padding: '2px 7px',
              borderRadius: '999px',
              background: 'rgba(52, 211, 153, 0.1)',
              color: '#34D399',
              border: '1px solid rgba(52, 211, 153, 0.2)'
            }}>
              Active Node
            </span>
          </div>

          <div style={{ fontSize: '13px', color: 'var(--text-subtle)', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <span>Slug: <code style={{ color: 'var(--text-muted)' }}>{merchant.merchant_id}</code></span>
            <span>•</span>
            <span>Category: <span style={{ color: 'var(--text-muted)' }}>{merchant.category}</span></span>
            <span>•</span>
            <span>Currency: <span style={{ color: 'var(--text-muted)' }}>{merchant.currency || 'INR'}</span></span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleManualSync}
            disabled={syncing}
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border)',
              borderRadius: '7px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--text-main)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <RefreshCw size={12} className={syncing ? 'spin-anim' : ''} />
            <span>{syncing ? 'Syncing...' : 'Sync Catalog'}</span>
          </button>

          <a
            href={agentCardUrl}
            target="_blank"
            rel="noreferrer"
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: '7px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--text-muted)',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>Agent Card</span>
            <ExternalLink size={12} />
          </a>
        </div>
      </div>

      {/* 4 Minimal Metric Tiles */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '12px',
        marginBottom: '18px'
      }}>
        <div style={{
          background: 'rgba(0, 0, 0, 0.2)',
          padding: '14px 16px',
          borderRadius: '9px',
          border: '1px solid var(--border)'
        }}>
          <span style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Settled Volume
          </span>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
            ₹{totalRevenue.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>
            {orders.length} order{orders.length === 1 ? '' : 's'} recorded
          </span>
        </div>

        <div style={{
          background: 'rgba(0, 0, 0, 0.2)',
          padding: '14px 16px',
          borderRadius: '9px',
          border: '1px solid var(--border)'
        }}>
          <span style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Max Discount Cap
          </span>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
            {merchant.max_discount_percentage}%
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>Clamped ceiling</span>
        </div>

        <div style={{
          background: 'rgba(0, 0, 0, 0.2)',
          padding: '14px 16px',
          borderRadius: '9px',
          border: '1px solid var(--border)'
        }}>
          <span style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Tx Spend Cap
          </span>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
            ₹{merchant.per_tx_spend_cap?.toLocaleString('en-IN')}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>Per transaction</span>
        </div>

        <div style={{
          background: 'rgba(0, 0, 0, 0.2)',
          padding: '14px 16px',
          borderRadius: '9px',
          border: '1px solid var(--border)'
        }}>
          <span style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            24h Volume Cap
          </span>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
            ₹{merchant.daily_merchant_spend_cap?.toLocaleString('en-IN')}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>Rolling limit</span>
        </div>
      </div>

      {/* Discovery Endpoint Strip */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(0, 0, 0, 0.15)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '8px 12px',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden', fontSize: '12px' }}>
          <span style={{ color: 'var(--text-subtle)', flexShrink: 0 }}>Agent Discovery Card:</span>
          <code style={{ color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {agentCardUrl}
          </code>
        </div>
        <button
          onClick={copyCardUrl}
          style={{
            background: 'transparent',
            border: 'none',
            color: copiedUrl ? '#34D399' : 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '12px',
            flexShrink: 0,
            padding: '2px 6px'
          }}
        >
          {copiedUrl ? <Check size={13} /> : <Copy size={13} />}
          <span>{copiedUrl ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
    </div>
  );
}
