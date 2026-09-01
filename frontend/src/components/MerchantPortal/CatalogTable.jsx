import React, { useState } from 'react';
import { Package, Search, Tag, CheckCircle2, AlertCircle } from 'lucide-react';

export function CatalogTable({ products = [] }) {
  const [search, setSearch] = useState('');

  const filtered = products.filter((p) => {
    const q = search.toLowerCase();
    return (
      p.title.toLowerCase().includes(q) ||
      p.sku.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q)
    );
  });

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Package size={20} color="#38BDF8" />
            Live Synced Catalog ({products.length} Products)
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            These products are discoverable and purchasable by Claude Desktop, Antigravity, and UAP autonomous buyer bots.
          </p>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', width: '260px' }}>
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            className="form-control"
            placeholder="Search SKU or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '34px', fontSize: '13px', padding: '8px 12px 8px 34px' }}
          />
        </div>
      </div>

      {products.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
          No products in catalog. Click "Sync Catalog" to pull items from your store.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                <th style={{ padding: '12px 14px' }}>Product</th>
                <th style={{ padding: '12px 14px' }}>SKU</th>
                <th style={{ padding: '12px 14px' }}>Price</th>
                <th style={{ padding: '12px 14px' }}>Max Discount</th>
                <th style={{ padding: '12px 14px' }}>Stock</th>
                <th style={{ padding: '12px 14px' }}>Category</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr
                  key={p.product_id}
                  style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', transition: 'background 0.2s' }}
                >
                  <td style={{ padding: '12px 14px', fontWeight: 600, color: '#fff' }}>
                    {p.title}
                  </td>
                  <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', color: '#38BDF8', fontSize: '12px' }}>
                    {p.sku}
                  </td>
                  <td style={{ padding: '12px 14px', fontWeight: 700, color: '#fff' }}>
                    ₹{p.price_inr?.toFixed(2)}
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <span className="badge badge-primary" style={{ fontSize: '11px' }}>
                      {p.max_discount_percentage}%
                    </span>
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    {p.inventory_count > 0 ? (
                      <span style={{ color: '#10B981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle2 size={12} /> {p.inventory_count} in stock
                      </span>
                    ) : (
                      <span style={{ color: '#F43F5E', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <AlertCircle size={12} /> Out of stock
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '12px 14px', color: 'var(--text-muted)' }}>
                    {p.category}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
