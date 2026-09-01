import React, { useState } from 'react';
import { Store, ShoppingBag, Globe, Key, ArrowRight, ShieldCheck } from 'lucide-react';
import { api } from '../../services/api';

export function StoreWizard({ onStoreConnected }) {
  const [storeName, setStoreName] = useState('');
  const [storeId, setStoreId] = useState('');
  const [category, setCategory] = useState('Apparel & Fashion');
  const [currency, setCurrency] = useState('INR');
  const [maxDiscount, setMaxDiscount] = useState(20);
  const [txCap, setTxCap] = useState(25000);
  const [provider, setProvider] = useState('shopify');
  const [shopifyUrl, setShopifyUrl] = useState('https://urban-threads-sample.myshopify.com');
  const [apiEndpoint, setApiEndpoint] = useState('https://api.example.com/v1/products');
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
          title: 'name',
          price: 'price_inr',
          sku: 'item_code',
          inventory: 'stock_qty',
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
    <div className="glass-panel" style={{ padding: '36px', maxWidth: '720px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '28px' }}>
        <div style={{
          width: '48px', height: '48px', borderRadius: '12px',
          background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#10B981', margin: '0 auto 16px auto'
        }}>
          <Store size={24} />
        </div>
        <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
          Connect Your Merchant Store
        </h2>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
          Set your brand's discount ceilings and connect your Shopify or REST inventory to activate your autonomous AI agent card.
        </p>
      </div>

      {error && (
        <div style={{ padding: '12px', background: 'rgba(244, 63, 94, 0.15)', color: '#F43F5E', borderRadius: '8px', fontSize: '13px', marginBottom: '20px' }}>
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
              placeholder="e.g. Urban Style Apparel"
              value={storeName}
              onChange={(e) => handleNameChange(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Merchant ID (Slug for AI Agents)</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. urban_style_apparel"
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
              placeholder="Apparel & Fashion"
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
            <option value="shopify">Shopify Storefront / Admin API</option>
            <option value="custom_api">Custom REST API</option>
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
            <label>Custom REST Products Endpoint</label>
            <input
              type="url"
              className="form-control"
              placeholder="https://api.yourbrand.com/v1/products"
              value={apiEndpoint}
              onChange={(e) => setApiEndpoint(e.target.value)}
              required
            />
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="btn btn-purple"
          style={{ width: '100%', padding: '14px', marginTop: '12px', justifyContent: 'center' }}
        >
          {loading ? 'Connecting & Syncing Catalog...' : 'Connect Store & Activate AI Agent Card'}
          <ArrowRight size={16} />
        </button>
      </form>
    </div>
  );
}
