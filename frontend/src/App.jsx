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
import { OrdersTable } from './components/MerchantPortal/OrdersTable';
import { api } from './services/api';
import { ShoppingBag, Package } from 'lucide-react';

export default function App() {
  const [user, setUser] = useState(null);
  const [persona, setPersona] = useState('buyer'); // 'buyer' | 'merchant'
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [storeData, setStoreData] = useState(null);
  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [merchantTab, setMerchantTab] = useState('orders'); // 'orders' | 'catalog'
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
        if (Array.isArray(data.orders)) {
          setOrders(data.orders);
        }
      }
      await refreshOrders();
    } catch (err) {
      console.error('Failed to load store:', err);
    }
  };

  const refreshOrders = async () => {
    setOrdersLoading(true);
    try {
      const orderList = await api.getMyStoreOrders();
      if (Array.isArray(orderList)) {
        setOrders(orderList);
      }
    } catch (err) {
      console.error('Failed to refresh orders:', err);
    } finally {
      setOrdersLoading(false);
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
    setOrders([]);
    setPersona('buyer');
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
        merchantName={storeData?.merchant?.merchant_name}
        hasStore={Boolean(storeData?.has_store)}
      />

      {/* Main Content Area */}
      <main style={{ flex: 1, maxWidth: '1120px', width: '100%', margin: '0 auto', padding: '24px 20px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--text-subtle)', fontSize: '14px' }}>
            Connecting to Payvlo Node...
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
            <div style={{ marginBottom: '20px' }}>
              <h1 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>
                Buyer & Agent Credentials
              </h1>
              <p style={{ fontSize: '13px', color: 'var(--text-subtle)', marginTop: '2px' }}>
                Manage your MCP authorization key, saved shipping addresses, and agent prompts.
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
            {!storeData?.has_store ? (
              /* Store Onboarding Wizard */
              <StoreWizard onStoreConnected={() => loadStore()} />
            ) : (
              /* Live Merchant Dashboard */
              <>
                <AgentCardView
                  merchant={storeData.merchant}
                  orders={orders}
                  onSyncCompleted={() => loadStore()}
                />

                {/* Clean Tab Switcher: Orders vs Catalog */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  borderBottom: '1px solid var(--border)',
                  paddingBottom: '10px',
                  marginTop: '16px'
                }}>
                  <button
                    onClick={() => setMerchantTab('orders')}
                    style={{
                      background: merchantTab === 'orders' ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                      border: merchantTab === 'orders' ? '1px solid var(--border)' : '1px solid transparent',
                      borderRadius: '7px',
                      padding: '6px 12px',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: merchantTab === 'orders' ? 'var(--text-main)' : 'var(--text-muted)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <ShoppingBag size={14} />
                    <span>Orders</span>
                    <span style={{
                      fontSize: '11px',
                      padding: '1px 6px',
                      borderRadius: '999px',
                      background: 'rgba(255, 255, 255, 0.08)',
                      color: 'var(--text-muted)'
                    }}>
                      {orders.length}
                    </span>
                  </button>

                  <button
                    onClick={() => setMerchantTab('catalog')}
                    style={{
                      background: merchantTab === 'catalog' ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                      border: merchantTab === 'catalog' ? '1px solid var(--border)' : '1px solid transparent',
                      borderRadius: '7px',
                      padding: '6px 12px',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: merchantTab === 'catalog' ? 'var(--text-main)' : 'var(--text-muted)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <Package size={14} />
                    <span>Catalog</span>
                    <span style={{
                      fontSize: '11px',
                      padding: '1px 6px',
                      borderRadius: '999px',
                      background: 'rgba(255, 255, 255, 0.08)',
                      color: 'var(--text-muted)'
                    }}>
                      {(storeData.products || []).length}
                    </span>
                  </button>
                </div>

                {/* Tab Content */}
                {merchantTab === 'orders' ? (
                  <OrdersTable
                    orders={orders}
                    onRefresh={refreshOrders}
                    loading={ordersLoading}
                  />
                ) : (
                  <CatalogTable products={storeData.products || []} />
                )}
              </>
            )}
          </div>
        )}
      </main>

      {/* Clean Minimal Footer */}
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '18px 24px',
        textAlign: 'center',
        fontSize: '12px',
        color: 'var(--text-subtle)',
        background: 'rgba(10, 12, 16, 0.8)'
      }}>
        Payvlo • Universal Agentic Commerce Node (MCP + UAP)
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
