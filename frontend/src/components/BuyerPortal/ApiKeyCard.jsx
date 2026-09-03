import React, { useState, useEffect } from 'react';
import { Key, Copy, Check, Terminal, Shield, Eye, EyeOff, Download, Folder, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';

export function ApiKeyCard({ user }) {
  const [apiKeyData, setApiKeyData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedConfig, setCopiedConfig] = useState(false);
  const [copiedPath, setCopiedPath] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [activeClient, setActiveClient] = useState('antigravity'); // 'antigravity' | 'claude' | 'cursor'

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
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedState(true);
    setTimeout(() => setCopiedState(false), 2000);
  };

  const downloadConfigFile = (filename, content) => {
    if (!content) return;
    const blob = new Blob([content], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Helper to ensure snippet always contains the Authorization header with bearer token
  const getFullConfigSnippet = (clientType) => {
    if (!apiKeyData) return '';
    const token = apiKeyData.api_key || '';
    const sseUrl = apiKeyData.mcp_server_url || `${window.location.origin}/sse`;

    if (clientType === 'antigravity') {
      if (apiKeyData.antigravity_config_snippet && apiKeyData.antigravity_config_snippet.includes('Authorization')) {
        return apiKeyData.antigravity_config_snippet;
      }
      return JSON.stringify(
        {
          mcpServers: {
            'payvlo-commerce': {
              serverUrl: sseUrl,
              headers: {
                Authorization: `Bearer ${token}`
              }
            }
          }
        },
        null,
        2
      );
    }

    if (clientType === 'claude') {
      if (apiKeyData.claude_desktop_config_snippet && apiKeyData.claude_desktop_config_snippet.includes('Authorization')) {
        return apiKeyData.claude_desktop_config_snippet;
      }
      return JSON.stringify(
        {
          mcpServers: {
            'payvlo-commerce': {
              url: sseUrl,
              headers: {
                Authorization: `Bearer ${token}`
              }
            }
          }
        },
        null,
        2
      );
    }

    if (clientType === 'cursor') {
      if (apiKeyData.cursor_config_snippet && apiKeyData.cursor_config_snippet.includes('Authorization')) {
        return apiKeyData.cursor_config_snippet;
      }
      return JSON.stringify(
        {
          mcpServers: {
            'payvlo-commerce': {
              url: sseUrl,
              headers: {
                Authorization: `Bearer ${token}`
              }
            }
          }
        },
        null,
        2
      );
    }

    return '';
  };

  const clientDetails = {
    antigravity: {
      name: 'Antigravity IDE',
      filename: 'mcp_config.json',
      color: '#38BDF8',
      pathDesc: 'Global: ~/.gemini/config/mcp_config.json   |   Project: .agents/mcp_config.json',
      copyPath: '~/.gemini/config/mcp_config.json',
      instructions: 'Place this file in your global config or inside your workspace .agents/ directory. Antigravity connects directly over SSE with full authentication.'
    },
    claude: {
      name: 'Claude Desktop',
      filename: 'claude_desktop_config.json',
      color: '#818CF8',
      pathDesc: 'Windows: %APPDATA%\\Claude\\claude_desktop_config.json   |   macOS: ~/Library/Application Support/Claude/claude_desktop_config.json',
      copyPath: '%APPDATA%\\Claude\\claude_desktop_config.json',
      instructions: 'Save or merge this into your Claude Desktop config file and restart Claude Desktop to load all Payvlo commerce tools.'
    },
    cursor: {
      name: 'Cursor / VS Code',
      filename: 'mcp.json',
      color: '#34D399',
      pathDesc: 'Project Root: .cursor/mcp.json   |   Global: ~/.cursor/mcp.json',
      copyPath: '.cursor/mcp.json',
      instructions: 'Save this file in your project’s .cursor/ folder to empower your Cursor agent with autonomous store catalog search, quote negotiation, and checkout.'
    }
  };

  const currentClient = clientDetails[activeClient];
  const currentSnippet = getFullConfigSnippet(activeClient);

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '32px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Generating your authenticated MCP connection configuration...</p>
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: '28px', marginBottom: '28px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '44px', height: '44px', borderRadius: '12px',
            background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center',
            justifyContent: 'center', color: '#38BDF8', border: '1px solid rgba(56, 189, 248, 0.3)'
          }}>
            <Key size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              MCP Server Connection & API Key
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Complete pre-configured Model Context Protocol connection files with your permanent authorization token embedded.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-emerald" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Shield size={12} />
            Active (365 Days)
          </span>
          <span className="badge badge-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={12} />
            Token Pre-Injected
          </span>
        </div>
      </div>

      {/* Raw API Key Box */}
      <div style={{ marginBottom: '24px' }}>
        <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
          Your Permanent Bearer JWT Token
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
            className="btn btn-secondary btn-sm"
            style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            {copiedKey ? <Check size={14} color="#34D399" /> : <Copy size={14} />}
            {copiedKey ? 'Copied' : 'Copy Key'}
          </button>
        </div>
      </div>

      {/* Client Selection Tabs */}
      <div style={{
        background: 'rgba(0, 0, 0, 0.35)',
        borderRadius: '14px',
        border: '1px solid var(--border)',
        overflow: 'hidden'
      }}>
        {/* Tab Headers */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border)',
          background: 'rgba(15, 23, 42, 0.5)',
          overflowX: 'auto'
        }}>
          {Object.entries(clientDetails).map(([key, details]) => {
            const isActive = activeClient === key;
            return (
              <button
                key={key}
                onClick={() => {
                  setActiveClient(key);
                  setCopiedConfig(false);
                }}
                style={{
                  padding: '14px 20px',
                  background: isActive ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                  border: 'none',
                  borderBottom: isActive ? `2px solid ${details.color}` : '2px solid transparent',
                  color: isActive ? '#fff' : 'var(--text-muted)',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  transition: 'all 0.2s ease',
                  whiteSpace: 'nowrap'
                }}
              >
                <Terminal size={15} color={isActive ? details.color : 'currentColor'} />
                {details.name}
                <code style={{
                  fontSize: '11px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  color: isActive ? details.color : 'var(--text-muted)'
                }}>
                  {details.filename}
                </code>
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div style={{ padding: '20px' }}>
          {/* Action Bar: Download & Copy buttons */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '14px',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>Ready-to-Use Connection File:</span>
                <code style={{ color: currentClient.color, background: 'rgba(0,0,0,0.4)', padding: '2px 8px', borderRadius: '4px' }}>
                  {currentClient.filename}
                </code>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>
                {currentClient.instructions}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => copyToClipboard(currentSnippet, setCopiedConfig)}
                className="btn btn-secondary btn-sm"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px' }}
              >
                {copiedConfig ? <Check size={14} color="#34D399" /> : <Copy size={14} />}
                {copiedConfig ? 'Copied Config!' : 'Copy JSON'}
              </button>

              <button
                onClick={() => downloadConfigFile(currentClient.filename, currentSnippet)}
                className="btn btn-primary btn-sm"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                  boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
                }}
              >
                <Download size={14} />
                Download {currentClient.filename}
              </button>
            </div>
          </div>

          {/* Local Path Callout */}
          <div style={{
            background: 'rgba(3, 7, 18, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '8px',
            padding: '8px 12px',
            marginBottom: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '12px',
            color: 'var(--text-muted)',
            flexWrap: 'wrap',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <Folder size={14} color={currentClient.color} />
              <span>Recommended save path:</span>
              <code style={{ color: '#fff', fontSize: '11px', background: 'rgba(0,0,0,0.5)', padding: '2px 6px', borderRadius: '4px' }}>
                {currentClient.pathDesc}
              </code>
            </div>
            <button
              onClick={() => copyToClipboard(currentClient.copyPath, setCopiedPath)}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '11px', padding: '2px 8px' }}
              title="Copy path"
            >
              {copiedPath ? <Check size={11} color="#34D399" /> : <Copy size={11} />}
              {copiedPath ? 'Path Copied' : 'Copy Path'}
            </button>
          </div>

          {/* Full Code Preview Box */}
          <div style={{ position: 'relative' }}>
            <pre style={{
              background: 'rgba(3, 7, 18, 0.85)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              padding: '16px',
              color: '#38BDF8',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              lineHeight: '1.6',
              overflowX: 'auto',
              margin: 0,
              maxHeight: '220px'
            }}>
              <code>{currentSnippet}</code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
