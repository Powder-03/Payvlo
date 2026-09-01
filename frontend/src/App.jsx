import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { LandingHero } from './components/LandingHero';
import { AuthModal } from './components/AuthModal';
import { ApiKeyCard } from './components/BuyerPortal/ApiKeyCard';
import { AddressBook } from './components/BuyerPortal/AddressBook';
import { PromptHelper } from './components/BuyerPortal/PromptHelper';
import { StoreWizard } from './components/MerchantPortal/StoreWizard';
import { AgentCardView } from './components/MerchantPortal/AgentCardView';
import { CatalogTable } from './components/MerchantPortal/CatalogTable';
import { api } from './services/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [persona, setPersona] = useState('buyer'); // 'buyer' | 'merchant'
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [storeData, setStoreData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('payvlo_token');
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const res = await api.getMe();
      setUser(res.user);
      if (res.has_store) {
        setPersona('merchant');
        loadStore();
      }
    } catch (err) {
      console.log('Session expired, logging out');
      localStorage.removeItem('payvlo_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const loadStore = async () => {
    try {
      const data = await api.getMyStore();
      if (data.has_store) {
        setStoreData(data);
      }
    } catch (err) {
      console.error('Failed to load store:', err);
    }
  };

  const handleAuthSuccess = (authenticatedUser, targetPersona) => {
    setUser(authenticatedUser);
    setPersona(targetPersona);
    if (targetPersona === 'merchant') {
      loadStore();
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('payvlo_token');
    setUser(null);
    setStoreData(null);
  };

  const openAuth = (mode = 'login') => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Navigation */}
      <Navbar
        user={user}
        persona={persona}
        onPersonaChange={(p) => setPersona(p)}
        onOpenAuth={openAuth}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main style={{ flex: 1, maxWidth: '1200px', width: '100%', margin: '0 auto', padding: '32px 24px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '64px', color: 'var(--text-muted)' }}>
            Connecting to Payvlo Commerce Node...
          </div>
        ) : !user ? (
          /* Guest View: Landing Hero for Buyer or Merchant */
          <LandingHero
            persona={persona}
            onPersonaChange={(p) => setPersona(p)}
            onOpenAuth={openAuth}
          />
        ) : persona === 'buyer' ? (
          /* Authenticated Buyer Portal */
          <div>
            <div style={{ marginBottom: '24px' }}>
              <span className="badge badge-primary" style={{ marginBottom: '8px' }}>
                Buyer & AI Agent Portal
              </span>
              <h1 style={{ fontSize: '28px', fontWeight: 800, color: '#fff' }}>
                Welcome back, {user.full_name || user.email}!
              </h1>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Manage your permanent MCP authorization key, saved address shortcuts, and prompt templates.
              </p>
            </div>

            {/* 1. MCP API Key Card */}
            <ApiKeyCard user={user} />

            {/* 2. Address Book */}
            <AddressBook user={user} />

            {/* 3. Interactive Prompt Assistant */}
            <PromptHelper />
          </div>
        ) : (
          /* Authenticated Merchant Portal */
          <div>
            <div style={{ marginBottom: '24px' }}>
              <span className="badge badge-emerald" style={{ marginBottom: '8px' }}>
                Merchant SaaS Portal
              </span>
              <h1 style={{ fontSize: '28px', fontWeight: 800, color: '#fff' }}>
                Merchant Control Center
              </h1>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Configure multi-tenant discount guardrails, sync Shopify / REST inventory, and inspect your AI agent card.
              </p>
            </div>

            {!storeData?.has_store ? (
              /* Step 2: Store Onboarding Wizard */
              <StoreWizard onStoreConnected={() => loadStore()} />
            ) : (
              /* Live Merchant Dashboard */
              <>
                <AgentCardView
                  merchant={storeData.merchant}
                  onSyncCompleted={() => loadStore()}
                />
                <CatalogTable products={storeData.products || []} />
              </>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '24px 32px',
        textAlign: 'center',
        fontSize: '13px',
        color: 'var(--text-subtle)',
        background: 'rgba(9, 13, 22, 0.95)'
      }}>
        ⚡ Payvlo — Universal Agentic Commerce Node (MCP SSE + UAP A2A) • Production Ready for Render & Vercel
      </footer>

      {/* Auth Modal */}
      {authModalOpen && (
        <AuthModal
          initialMode={authModalMode}
          persona={persona}
          onClose={() => setAuthModalOpen(false)}
          onSuccess={handleAuthSuccess}
        />
      )}
    </div>
  );
}
