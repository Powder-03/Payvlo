import React, { useState } from 'react';
import { X, Bot, Store, ArrowRight, Lock, Mail, User, Building } from 'lucide-react';
import { api } from '../services/api';

export function AuthModal({ initialMode = 'login', persona = 'buyer', onClose, onSuccess }) {
  const [mode, setMode] = useState(initialMode); // 'login' | 'signup'
  const [activePersona, setActivePersona] = useState(persona);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'signup') {
        const res = await api.signup({
          email,
          password,
          full_name: fullName,
          company_name: activePersona === 'merchant' ? companyName : (companyName || 'Individual Buyer'),
          persona: activePersona,
        });
        localStorage.setItem('payvlo_token', res.token);
        onSuccess(res.user, activePersona);
      } else {
        const res = await api.login(email, password);
        localStorage.setItem('payvlo_token', res.token);
        onSuccess(res.user, activePersona);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '22px', fontWeight: 800, color: '#fff' }}>
              {mode === 'login' ? 'Sign In to Payvlo' : 'Create Account'}
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {activePersona === 'buyer' ? 'Access your AI Agent key & Address Vault' : 'Manage your Merchant store & guardrails'}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Persona Selector inside Modal */}
        <div style={{
          display: 'flex',
          background: 'rgba(0, 0, 0, 0.4)',
          borderRadius: '10px',
          padding: '4px',
          marginBottom: '20px',
          border: '1px solid var(--border)'
        }}>
          <button
            type="button"
            onClick={() => setActivePersona('buyer')}
            style={{
              flex: 1,
              padding: '8px',
              borderRadius: '8px',
              border: activePersona === 'buyer' ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid transparent',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              background: activePersona === 'buyer' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
              color: activePersona === 'buyer' ? '#38BDF8' : 'var(--text-muted)'
            }}
          >
            <Bot size={15} />
            Buyer / AI User
          </button>
          <button
            type="button"
            onClick={() => setActivePersona('merchant')}
            style={{
              flex: 1,
              padding: '8px',
              borderRadius: '8px',
              border: activePersona === 'merchant' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              background: activePersona === 'merchant' ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
              color: activePersona === 'merchant' ? '#10B981' : 'var(--text-muted)'
            }}
          >
            <Store size={15} />
            Merchant / Store
          </button>

        </div>

        {error && (
          <div style={{
            padding: '10px 14px',
            background: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            borderRadius: '8px',
            color: '#F43F5E',
            fontSize: '13px',
            marginBottom: '16px'
          }}>
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Alex Mercer"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>

              {activePersona === 'merchant' && (
                <div className="form-group">
                  <label>Brand / Store Name</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Urban Style Apparel"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    required
                  />
                </div>
              )}
            </>
          )}

          <div className="form-group">
            <label>Email Address</label>
            <input
              type="email"
              className="form-control"
              placeholder="you@domain.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password (min 6 characters)</label>
            <input
              type="password"
              className="form-control"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={6}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`btn ${activePersona === 'buyer' ? 'btn-primary' : 'btn-purple'}`}
            style={{ width: '100%', padding: '12px', marginTop: '8px', justifyContent: 'center' }}
          >
            {loading ? 'Processing...' : (mode === 'login' ? 'Sign In' : 'Create Account')}
            <ArrowRight size={16} />
          </button>
        </form>

        {/* Mode Toggle Footer */}
        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '13px', color: 'var(--text-muted)' }}>
          {mode === 'login' ? (
            <>
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => setMode('signup')}
                style={{ background: 'none', border: 'none', color: '#38BDF8', fontWeight: 600, cursor: 'pointer' }}
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => setMode('login')}
                style={{ background: 'none', border: 'none', color: '#38BDF8', fontWeight: 600, cursor: 'pointer' }}
              >
                Sign in
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
