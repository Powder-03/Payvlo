import React, { useState } from 'react';
import { Package, Search } from 'lucide-react';

export function CatalogTable({ products = [] }) {
  const [search, setSearch] = useState('');

  const filtered = products.filter((p) => {
    const q = search.toLowerCase();
    return (
      (p.title || '').toLowerCase().includes(q) ||
      (p.sku || '').toLowerCase().includes(q) ||
      (p.category || '').toLowerCase().includes(q)
    );
  });

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '12px',
      overflow: 'hidden',
      marginTop: '20px'
    }}>
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '30px',
            height: '30px',
            borderRadius: '8px',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Package size={15} color="var(--text-main)" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-main)' }}>
                Synced Catalog
              </span>
              <span style={{
                fontSize: '11px',
                padding: '2px 7px',
                borderRadius: '6px',
                background: 'rgba(255, 255, 255, 0.06)',
                color: 'var(--text-muted)',
                fontWeight: 600
              }}>
                {products.length} items
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-subtle)', marginTop: '2px' }}>
              Products discoverable by AI buyer agents for quotation and checkout.
            </p>
          </div>
        </div>

        {/* Minimal Search */}
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{
            position: 'absolute',
            left: '10px',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-subtle)'
          }} />
          <input
            type="text"
            placeholder="Search SKU or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: 'rgba(0, 0, 0, 0.25)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '6px 12px 6px 30px',
              fontSize: '13px',
              color: 'var(--text-main)',
              outline: 'none',
              width: '210px'
            }}
          />
        </div>
      </div>

      {products.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)' }}>
          <Package size={28} strokeWidth={1.5} style={{ opacity: 0.4, marginBottom: '8px' }} />
          <p style={{ fontSize: '14px', fontWeight: 500 }}>No products in catalog</p>
          <p style={{ fontSize: '12px', color: 'var(--text-subtle)', marginTop: '4px' }}>
            Click "Sync Catalog" above to pull products from your store.
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{
                background: 'rgba(0, 0, 0, 0.15)',
                borderBottom: '1px solid var(--border)',
                color: 'var(--text-subtle)',
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Product</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>SKU</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Base Price</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Max Discount</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Stock</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Category</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr
                  key={p.product_id}
                  style={{
                    borderBottom: '1px solid var(--border)',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '12px 18px', fontWeight: 500, color: 'var(--text-main)' }}>
                    {p.title}
                  </td>
                  <td style={{ padding: '12px 18px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '12px' }}>
                    {p.sku}
                  </td>
                  <td style={{ padding: '12px 18px', fontWeight: 600, color: 'var(--text-main)' }}>
                    ₹{p.price_inr?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ padding: '12px 18px' }}>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: 500,
                      padding: '2px 7px',
                      borderRadius: '6px',
                      background: 'rgba(255, 255, 255, 0.06)',
                      color: 'var(--text-muted)'
                    }}>
                      {p.max_discount_percentage}%
                    </span>
                  </td>
                  <td style={{ padding: '12px 18px' }}>
                    {p.inventory_count > 0 ? (
                      <span style={{ color: '#34D399', fontSize: '12px', fontWeight: 500 }}>
                        {p.inventory_count} in stock
                      </span>
                    ) : (
                      <span style={{ color: '#F87171', fontSize: '12px', fontWeight: 500 }}>
                        Out of stock
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '12px 18px', color: 'var(--text-subtle)', fontSize: '12px' }}>
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
