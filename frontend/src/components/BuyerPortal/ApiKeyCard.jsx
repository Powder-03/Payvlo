import React, { useState, useEffect } from 'react';
import { Key, Copy, Check, Terminal, Shield, RefreshCw, Eye, EyeOff } from 'lucide-react';
import { api } from '../../services/api';

export function ApiKeyCard({ user }) {
  const [apiKeyData, setApiKeyData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedAntigravity, setCopiedAntigravity] = useState(false);
  const [copiedClaude, setCopiedClaude] = useState(false);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    fetchApiKey();
  }, []);

  const fetchApiKey = async () => {
    setLoading(true);
    try {
      const data = await api.getApiKey();
      setApiKeyData(data);
    } catch (err) {
      console.error('Failed to load API key:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, setCopiedState) => {
    navigator.clipboard.writeText(text);
    setCopiedState(true);
    setTimeout(() => setCopiedState(false), 2000);
  };

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '32px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Generating your MCP authorization key...</p>
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: '28px', marginBottom: '28px' }}>
      {/* Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '10px',
            background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center',
            justifyContent: 'center', color: '#38BDF8'
          }}>
            <Key size={20} />
          </div>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff' }}>
              Your MCP Server API Key
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Use this key to authorize Claude Desktop, Antigravity, or your Python buyer agents.
            </p>
          </div>
        </div>

        <span className="badge badge-emerald">
          <Shield size={12} />
          Active (365 Days)
        </span>
      </div>

      {/* API Key Box */}
      <div style={{ marginBottom: '20px' }}>
        <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
          Permanent Bearer JWT Token
        </label>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(3, 7, 18, 0.7)',
          border: '1px solid var(--border)',
          borderRadius: '10px',
          padding: '8px 12px'
        }}>
          <input
            type={showKey ? 'text' : 'password'}
            readOnly
            value={apiKeyData?.api_key || ''}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              color: '#38BDF8',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              outline: 'none'
            }}
          />
          <button
            onClick={() => setShowKey(!showKey)}
            className="btn btn-secondary btn-sm"
            style={{ padding: '6px 10px' }}
            title={showKey ? 'Hide Token' : 'Show Token'}
          >
            {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
          <button
            onClick={() => copyToClipboard(apiKeyData?.api_key, setCopiedKey)}
            className="btn btn-primary btn-sm"
            style={{ padding: '6px 12px' }}
          >
            {copiedKey ? <Check size={14} /> : <Copy size={14} />}
            {copiedKey ? 'Copied' : 'Copy Key'}
          </button>
        </div>
      </div>

      {/* 2 Setup Tabs for Antigravity & Claude */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Antigravity Config */}
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', borderRadius: '12px', padding: '16px', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Terminal size={14} />
              Antigravity IDE Config (<code style={{ color: '#fff' }}>mcp_config.json</code>)
            </span>
            <button
              onClick={() => copyToClipboard(apiKeyData?.antigravity_config_snippet, setCopiedAntigravity)}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '11px', padding: '4px 8px' }}
            >
              {copiedAntigravity ? <Check size={12} /> : <Copy size={12} />}
              {copiedAntigravity ? 'Copied' : 'Copy JSON'}
            </button>
          </div>
          <div className="code-box" style={{ fontSize: '11px', maxHeight: '110px' }}>
            {apiKeyData?.antigravity_config_snippet}
          </div>
        </div>

        {/* Claude Desktop Config */}
        <div style={{ background: 'rgba(0, 0, 0, 0.3)', borderRadius: '12px', padding: '16px', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#818CF8', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Terminal size={14} />
              Claude Desktop Config (<code style={{ color: '#fff' }}>claude_desktop_config.json</code>)
            </span>
            <button
              onClick={() => copyToClipboard(apiKeyData?.claude_desktop_config_snippet, setCopiedClaude)}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '11px', padding: '4px 8px' }}
            >
              {copiedClaude ? <Check size={12} /> : <Copy size={12} />}
              {copiedClaude ? 'Copied' : 'Copy JSON'}
            </button>
          </div>
          <div className="code-box" style={{ fontSize: '11px', maxHeight: '110px' }}>
            {apiKeyData?.claude_desktop_config_snippet}
          </div>
        </div>
      </div>
    </div>
  );
}
