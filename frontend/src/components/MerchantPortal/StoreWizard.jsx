import React, { useState } from 'react';
import { Store, ArrowRight, Sparkles } from 'lucide-react';
import { api } from '../../services/api';

export function StoreWizard({ onStoreConnected }) {
  const [storeName, setStoreName] = useState('');
  const [storeId, setStoreId] = useState('');
  const [category, setCategory] = useState('Health & Supplements');
  const [currency, setCurrency] = useState('INR');
  const [maxDiscount, setMaxDiscount] = useState(15);
  const [txCap, setTxCap] = useState(25000);
  const [provider, setProvider] = useState('custom_api');
  const [shopifyUrl, setShopifyUrl] = useState('https://urban-threads-sample.myshopify.com');
  const [apiEndpoint, setApiEndpoint] = useState(`${window.location.origin}/api/v1/external-stores/muscleblaze/products.json`);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleNameChange = (val) => {
    setStoreName(val);
    const slug = val
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
    setStoreId(slug);
  };

  const applyPreset = (preset) => {
    if (preset === 'muscleblaze') {
      setStoreName('MuscleBlaze Performance');
      setStoreId('muscleblaze');
      setCategory('Health & Supplements');
      setMaxDiscount(20);
      setTxCap(25000);
      setProvider('custom_api');
      setApiEndpoint(`${window.location.origin}/api/v1/external-stores/muscleblaze/products.json`);
    } else if (preset === 'beastlife') {
      setStoreName('BeastLife Nutrition');
      setStoreId('beastlife_d2c');
      setCategory('Health & Supplements');
      setMaxDiscount(15);
      setTxCap(25000);
      setProvider('custom_api');
      setApiEndpoint(`${window.location.origin}/api/v1/external-stores/beastlife/products.json`);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let syncConfig = { provider, auto_sync: true };
      if (provider === 'shopify') {
        syncConfig.endpoint_url = shopifyUrl;
      } else if (provider === 'custom_api') {
        syncConfig.endpoint_url = apiEndpoint;
        syncConfig.field_mapping = {
          title: 'title',
          price: 'price_inr',
          sku: 'sku',
          inventory: 'inventory_count',
          category: 'category',
          description: 'description',
        };
      }

      const res = await api.applyStore({
        merchant_id: storeId,
        merchant_name: storeName,
        category,
        currency,
        max_discount_percentage: parseFloat(maxDiscount),
        per_tx_spend_cap: parseFloat(txCap),
        daily_merchant_spend_cap: parseFloat(txCap) * 10,
        sync_config: syncConfig,
      });

      onStoreConnected(res.merchant);
    } catch (err) {
      setError(err.message || 'Failed to connect store');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '12px',
      padding: '28px',
      maxWidth: '680px',
      margin: '0 auto'
    }}>
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '10px',
          background: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 12px auto'
        }}>
          <Store size={20} color="var(--text-main)" />
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>
          Connect Merchant Store
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-subtle)', marginTop: '4px' }}>
          Set your spend guardrails and connect your catalog to activate agentic checkout.
        </p>
      </div>

      {/* Fast Setup Presets */}
      <div style={{
        background: 'rgba(0, 0, 0, 0.2)',
        border: '1px solid var(--border)',
        borderRadius: '9px',
        padding: '12px 16px',
        marginBottom: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
          <Sparkles size={13} color="#34D399" />
          <span>Quick 1-Click Store Presets:</span>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => applyPreset('muscleblaze')}
            style={{
              background: storeId === 'muscleblaze' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--text-main)',
              cursor: 'pointer'
            }}
          >
            MuscleBlaze Performance
          </button>
          <button
            type="button"
            onClick={() => applyPreset('beastlife')}
            style={{
              background: storeId === 'beastlife_d2c' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--text-main)',
              cursor: 'pointer'
            }}
          >
            BeastLife Nutrition
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '10px 14px', background: 'rgba(248, 113, 113, 0.1)', color: '#F87171', border: '1px solid rgba(248, 113, 113, 0.2)', borderRadius: '7px', fontSize: '12px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label>Brand / Store Name</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. MuscleBlaze Performance"
              value={storeName}
              onChange={(e) => handleNameChange(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Merchant Slug</label>
            <input
              type="text"
              className="form-control"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Category</label>
            <input
              type="text"
              className="form-control"
              placeholder="Health & Supplements"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Currency</label>
            <select
              className="form-control"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              <option value="INR">INR (₹)</option>
              <option value="USD">USD ($)</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Max Store Discount Ceiling (%)</label>
            <input
              type="number"
              className="form-control"
              value={maxDiscount}
              min="0"
              max="100"
              step="0.5"
              onChange={(e) => setMaxDiscount(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Max Single Tx Spend Cap (₹)</label>
            <input
              type="number"
              className="form-control"
              value={txCap}
              min="100"
              onChange={(e) => setTxCap(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label>Catalog Provider</label>
          <select
            className="form-control"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
          >
            <option value="custom_api">Custom REST API</option>
            <option value="shopify">Shopify (/products.json)</option>
            <option value="direct">Direct Product Seed</option>
          </select>
        </div>

        {provider === 'shopify' && (
          <div className="form-group">
            <label>Shopify Store URL (/products.json)</label>
            <input
              type="url"
              className="form-control"
              placeholder="https://your-store.myshopify.com"
              value={shopifyUrl}
              onChange={(e) => setShopifyUrl(e.target.value)}
              required
            />
          </div>
        )}

        {provider === 'custom_api' && (
          <div className="form-group">
            <label>Catalog REST API Endpoint</label>
            <input
              type="url"
              className="form-control"
              placeholder="https://payvlo.onrender.com/api/v1/external-stores/muscleblaze/products.json"
              value={apiEndpoint}
              onChange={(e) => setApiEndpoint(e.target.value)}
              required
            />
            <span style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '4px', display: 'block' }}>
              Built-in live endpoints: <code>/api/v1/external-stores/muscleblaze/products.json</code> or <code>/api/v1/external-stores/beastlife/products.json</code>
            </span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary"
          style={{ width: '100%', padding: '10px', marginTop: '14px', fontSize: '13px' }}
        >
          {loading ? 'Connecting & Syncing...' : 'Connect Store & Sync Catalog'}
          <ArrowRight size={14} />
        </button>
      </form>
    </div>
  );
}
