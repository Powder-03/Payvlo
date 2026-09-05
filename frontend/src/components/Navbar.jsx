import React from 'react';
import { Zap, Bot, Store, LogOut, User as UserIcon, BookOpen } from 'lucide-react';

export function Navbar({ user, persona, onPersonaChange, onOpenAuth, onLogout, merchantName, hasStore }) {
  const isMerchantAccount = Boolean(user && (hasStore || user.merchant_id || persona === 'merchant'));

  return (
    <nav style={{
      height: '60px',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      background: 'rgba(10, 12, 16, 0.95)',
      backdropFilter: 'blur(12px)',
      position: 'sticky',
      top: 0,
      zIndex: 50
    }}>
      {/* Brand & Context */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            background: 'var(--text-main)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Zap size={16} color="#0a0c10" strokeWidth={2.5} />
          </div>
          <span style={{ fontWeight: 700, fontSize: '17px', letterSpacing: '-0.3px', color: 'var(--text-main)' }}>
            Payvlo
          </span>
        </div>

        {/* If logged in as merchant, LOCK navigation and show store breadcrumb */}
        {isMerchantAccount ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--text-subtle)', fontSize: '13px' }}>/</span>
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-muted)' }}>
              Store:
            </span>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
              {merchantName || 'Merchant Console'}
            </span>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
              color: '#34D399',
              background: 'rgba(52, 211, 153, 0.1)',
              padding: '2px 7px',
              borderRadius: '999px',
              fontWeight: 500,
              marginLeft: '4px'
            }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#34D399' }} />
              Live
            </span>
          </div>
        ) : !user ? (
          /* Guest Persona Switcher - Subtle & Minimal */
          <div style={{
            display: 'flex',
            background: 'rgba(255, 255, 255, 0.04)',
            borderRadius: '8px',
            padding: '2px',
            border: '1px solid var(--border)'
          }}>
            <button
              onClick={() => onPersonaChange('buyer')}
              style={{
                padding: '4px 10px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: persona === 'buyer' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                color: persona === 'buyer' ? '#fff' : 'var(--text-muted)'
              }}
            >
              <Bot size={13} />
              Buyer Agent
            </button>
            <button
              onClick={() => onPersonaChange('merchant')}
              style={{
                padding: '4px 10px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: persona === 'merchant' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                color: persona === 'merchant' ? '#fff' : 'var(--text-muted)'
              }}
            >
              <Store size={13} />
              Merchant Portal
            </button>
          </div>
        ) : (
          /* Logged in buyer breadcrumb */
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--text-subtle)', fontSize: '13px' }}>/</span>
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-muted)' }}>
              Buyer & Agent Dashboard
            </span>
          </div>
        )}
      </div>

      {/* Right Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '5px 9px',
            borderRadius: '6px',
            border: '1px solid var(--border)',
            background: 'rgba(255, 255, 255, 0.02)'
          }}
        >
          <BookOpen size={13} />
          Docs
        </a>

        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              borderRadius: '7px',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--border)'
            }}>
              <UserIcon size={13} color="var(--text-muted)" />
              <span style={{ fontSize: '12px', color: 'var(--text-main)', fontWeight: 500 }}>
                {user.full_name || user.email}
              </span>
            </div>
            <button
              onClick={onLogout}
              title="Logout"
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: '7px',
                padding: '6px 9px',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <LogOut size={13} />
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => onOpenAuth('login')}
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: '7px',
                padding: '5px 12px',
                color: 'var(--text-main)',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              Sign In
            </button>
            <button
              onClick={() => onOpenAuth('signup')}
              style={{
                background: 'var(--text-main)',
                border: 'none',
                borderRadius: '7px',
                padding: '5px 12px',
                color: '#0a0c10',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Get Started
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
