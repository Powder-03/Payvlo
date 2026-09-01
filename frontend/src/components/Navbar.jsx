import React from 'react';
import { Zap, Bot, Store, LogOut, User as UserIcon, BookOpen } from 'lucide-react';

export function Navbar({ user, persona, onPersonaChange, onOpenAuth, onLogout }) {
  return (
    <nav style={{
      height: '72px',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 32px',
      background: 'rgba(9, 13, 22, 0.85)',
      backdropFilter: 'blur(16px)',
      position: 'sticky',
      top: 0,
      zIndex: 50
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #38BDF8, #6366F1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(56, 189, 248, 0.3)'
          }}>
            <Zap size={20} color="#090D16" strokeWidth={2.5} />
          </div>
          <span style={{ fontFamily: 'Outfit', fontWeight: 800, fontSize: '22px', letterSpacing: '-0.5px' }}>
            Payvlo
          </span>
          <span className="badge badge-primary" style={{ fontSize: '11px' }}>
            MCP + UAP Node
          </span>
        </div>

        {/* Segmented Persona Switcher */}
        <div style={{
          display: 'flex',
          background: 'rgba(0, 0, 0, 0.4)',
          borderRadius: '12px',
          padding: '3px',
          border: '1px solid var(--border)'
        }}>
          <button
            onClick={() => onPersonaChange('buyer')}
            style={{
              padding: '6px 14px',
              borderRadius: '9px',
              border: persona === 'buyer' ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid transparent',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s',
              background: persona === 'buyer' ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(129, 140, 248, 0.2))' : 'transparent',
              color: persona === 'buyer' ? '#38BDF8' : 'var(--text-muted)'
            }}
          >
            <Bot size={15} />
            Buyer & AI Agent
          </button>
          <button
            onClick={() => onPersonaChange('merchant')}
            style={{
              padding: '6px 14px',
              borderRadius: '9px',
              border: persona === 'merchant' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s',
              background: persona === 'merchant' ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(56, 189, 248, 0.2))' : 'transparent',
              color: persona === 'merchant' ? '#10B981' : 'var(--text-muted)'
            }}
          >
            <Store size={15} />
            Merchant Portal
          </button>

        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          className="btn btn-secondary btn-sm"
          style={{ textDecoration: 'none' }}
        >
          <BookOpen size={14} />
          API Docs
        </a>

        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              borderRadius: '10px',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border)'
            }}>
              <UserIcon size={14} color="#38BDF8" />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>{user.full_name || user.email}</span>
            </div>
            <button onClick={onLogout} className="btn btn-secondary btn-sm" title="Logout">
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={() => onOpenAuth('login')} className="btn btn-secondary btn-sm">
              Sign In
            </button>
            <button onClick={() => onOpenAuth('signup')} className="btn btn-primary btn-sm">
              Get Started
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
