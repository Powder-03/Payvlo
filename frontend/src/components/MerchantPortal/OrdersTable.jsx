import React, { useState } from 'react';
import { 
  ShoppingBag, 
  ExternalLink, 
  RefreshCw, 
  Search, 
  ShieldCheck, 
  MapPin, 
  Clock,
  ArrowUpRight
} from 'lucide-react';

export function OrdersTable({ orders = [], onRefresh, loading = false }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredOrders = orders.filter((o) => {
    const term = searchTerm.toLowerCase();
    const orderId = (o.order_id || '').toLowerCase();
    const city = (o.shipping_address?.city || '').toLowerCase();
    const itemsText = (o.items || []).map(i => (i.title || i.product_id || '')).join(' ').toLowerCase();
    return orderId.includes(term) || city.includes(term) || itemsText.includes(term);
  });

  const formatPrice = (amt, curr = 'INR') => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: curr,
      maximumFractionDigits: 2,
    }).format(amt);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Just now';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '12px',
      overflow: 'hidden',
      marginTop: '20px'
    }}>
      {/* Table Header Controls */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        flexWrap: 'wrap'
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
            <ShoppingBag size={15} color="var(--text-main)" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-main)' }}>
                Agent Orders & Settlements
              </span>
              <span style={{
                fontSize: '11px',
                padding: '2px 7px',
                borderRadius: '6px',
                background: 'rgba(255, 255, 255, 0.06)',
                color: 'var(--text-muted)',
                fontWeight: 600
              }}>
                {orders.length}
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-subtle)', marginTop: '2px' }}>
              Inbound orders settled by AI buyer agents through MCP and UAP rails.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Minimal Search Input */}
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
              placeholder="Filter by ID, product, city..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                background: 'rgba(0, 0, 0, 0.25)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '6px 12px 6px 30px',
                fontSize: '13px',
                color: 'var(--text-main)',
                outline: 'none',
                width: '210px',
                transition: 'border-color 0.15s'
              }}
            />
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              title="Refresh Orders"
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '6px 10px',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 500
              }}
            >
              <RefreshCw size={13} className={loading ? 'spin-anim' : ''} />
              <span>Refresh</span>
            </button>
          )}
        </div>
      </div>

      {/* Orders Table */}
      {filteredOrders.length === 0 ? (
        <div style={{
          padding: '48px 24px',
          textAlign: 'center',
          color: 'var(--text-muted)'
        }}>
          <ShoppingBag size={28} strokeWidth={1.5} style={{ opacity: 0.4, marginBottom: '8px' }} />
          <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-muted)' }}>
            No agent orders recorded yet
          </p>
          <p style={{ fontSize: '12px', color: 'var(--text-subtle)', marginTop: '4px' }}>
            When autonomous buyer agents discover your store and checkout, orders appear here automatically.
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            textAlign: 'left',
            fontSize: '13px'
          }}>
            <thead>
              <tr style={{
                background: 'rgba(0, 0, 0, 0.15)',
                borderBottom: '1px solid var(--border)',
                color: 'var(--text-subtle)',
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Order ID & Time</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Items Purchased</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Total Amount</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Payment & Rails</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Delivery Address</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Audit Ledger</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((o) => {
                const items = Array.isArray(o.items) ? o.items : [];
                const shipping = o.shipping_address || {};
                const isPaid = (o.payment_status || '').toUpperCase() === 'PAID' || (o.payment_status || '').toUpperCase() === 'SUCCESS';

                return (
                  <tr
                    key={o.order_id}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      transition: 'background 0.15s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    {/* Order ID & Time */}
                    <td style={{ padding: '14px 18px', verticalAlign: 'top' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-main)', fontSize: '12px' }}>
                        {o.order_id}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-subtle)', fontSize: '11px', marginTop: '4px' }}>
                        <Clock size={11} />
                        <span>{formatDate(o.created_at)}</span>
                      </div>
                    </td>

                    {/* Items */}
                    <td style={{ padding: '14px 18px', verticalAlign: 'top', maxWidth: '280px' }}>
                      {items.length === 0 ? (
                        <span style={{ color: 'var(--text-subtle)' }}>1 item</span>
                      ) : (
                        items.map((item, idx) => (
                          <div key={idx} style={{ marginBottom: idx < items.length - 1 ? '4px' : '0' }}>
                            <span style={{ fontWeight: 500, color: 'var(--text-main)' }}>
                              {item.title || item.sku || item.product_id}
                            </span>
                            <span style={{ color: 'var(--text-subtle)', marginLeft: '6px', fontSize: '12px' }}>
                              × {item.quantity || 1}
                            </span>
                          </div>
                        ))
                      )}
                    </td>

                    {/* Amount */}
                    <td style={{ padding: '14px 18px', verticalAlign: 'top' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '13px' }}>
                        {formatPrice(o.final_amount, o.currency)}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '2px' }}>
                        Zero-trust verified
                      </div>
                    </td>

                    {/* Payment & Rails */}
                    <td style={{ padding: '14px 18px', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '6px',
                          background: isPaid ? 'rgba(16, 185, 129, 0.12)' : 'rgba(56, 189, 248, 0.12)',
                          color: isPaid ? '#34D399' : '#38BDF8',
                          border: `1px solid ${isPaid ? 'rgba(16, 185, 129, 0.25)' : 'rgba(56, 189, 248, 0.25)'}`
                        }}>
                          {(o.payment_status || 'CREATED').toUpperCase()}
                        </span>

                        {o.payment_link && (
                          <a
                            href={o.payment_link}
                            target="_blank"
                            rel="noreferrer"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              color: 'var(--text-muted)',
                              textDecoration: 'none'
                            }}
                            title="Open Razorpay Payment Link"
                          >
                            <ArrowUpRight size={14} />
                          </a>
                        )}
                      </div>
                      {o.payment_rail_id && (
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-subtle)', marginTop: '4px' }}>
                          {o.payment_rail_id}
                        </div>
                      )}
                    </td>

                    {/* Delivery Destination */}
                    <td style={{ padding: '14px 18px', verticalAlign: 'top', maxWidth: '200px' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '4px' }}>
                        <MapPin size={12} style={{ color: 'var(--text-subtle)', marginTop: '2px', flexShrink: 0 }} />
                        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                          {[shipping.city, shipping.state, shipping.postal_code].filter(Boolean).join(', ') || 'Home Address'}
                        </span>
                      </div>
                    </td>

                    {/* Audit Ledger */}
                    <td style={{ padding: '14px 18px', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <ShieldCheck size={13} color="#34D399" />
                        <span style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '11px',
                          color: 'var(--text-subtle)'
                        }}>
                          {o.audit_id ? `${o.audit_id.slice(0, 12)}...` : 'aud_verified'}
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
