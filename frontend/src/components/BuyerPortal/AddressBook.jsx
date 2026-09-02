import React, { useState, useEffect } from 'react';
import { MapPin, Plus, Trash2, Home, Briefcase, Building, Check, Phone, Mail, FileText, X } from 'lucide-react';
import { api } from '../../services/api';

export function AddressBook({ user }) {
  const [addresses, setAddresses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  // Form State
  const [label, setLabel] = useState('Home');
  const [line1, setLine1] = useState('');
  const [line2, setLine2] = useState('');
  const [city, setCity] = useState('Bengaluru');
  const [state, setState] = useState('KA');
  const [postalCode, setPostalCode] = useState('560038');
  const [phone, setPhone] = useState('');
  const [deliveryNotes, setDeliveryNotes] = useState('');
  const [isDefault, setIsDefault] = useState(false);

  useEffect(() => {
    fetchAddresses();
  }, []);

  const fetchAddresses = async () => {
    setLoading(true);
    try {
      const list = await api.getAddresses();
      setAddresses(list);
    } catch (err) {
      console.error('Failed to fetch addresses:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAddress = async (e) => {
    e.preventDefault();
    setError('');

    if (!line2.trim()) {
      setError('Area / Landmark is required for accurate delivery.');
      return;
    }

    setSaving(true);

    try {
      await api.saveAddress({
        label,
        line1,
        line2: line2.trim(),
        city,
        state,
        postal_code: postalCode,
        country: 'IN',
        phone: phone || undefined,
        delivery_notes: deliveryNotes || undefined,
        is_default: isDefault,
      });
      setShowAddModal(false);
      resetForm();
      fetchAddresses();
    } catch (err) {
      setError(err.message || 'Failed to save address');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (addressId) => {
    if (!window.confirm('Delete this address?')) return;
    try {
      await api.deleteAddress(addressId);
      setAddresses(addresses.filter((a) => a.address_id !== addressId));
    } catch (err) {
      alert(err.message || 'Failed to delete address');
    }
  };

  const resetForm = () => {
    setLabel('Home');
    setLine1('');
    setLine2('');
    setCity('Bengaluru');
    setState('KA');
    setPostalCode('560038');
    setPhone('');
    setDeliveryNotes('');
    setIsDefault(false);
  };

  const getLabelIcon = (lbl) => {
    const l = lbl.toLowerCase();
    if (l.includes('home')) return <Home size={16} color="#38BDF8" />;
    if (l.includes('work') || l.includes('office')) return <Briefcase size={16} color="#818CF8" />;
    return <MapPin size={16} color="#10B981" />;
  };

  return (
    <div className="glass-panel" style={{ padding: '28px', marginBottom: '28px' }}>
      {/* Title & Action */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MapPin size={22} color="#38BDF8" />
            Address Book & Saved Shortcuts
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Save places you order to often so you can tell AI agents: <code style={{ color: '#38BDF8' }}>"Order to my Home address"</code>
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary btn-sm"
          style={{ padding: '8px 16px' }}
        >
          <Plus size={16} />
          Add New Address
        </button>
      </div>

      {/* Address Cards Grid */}
      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Loading saved locations...</p>
      ) : addresses.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '36px 16px',
          background: 'rgba(0, 0, 0, 0.2)',
          borderRadius: '12px',
          border: '1px dashed var(--border)'
        }}>
          <MapPin size={32} color="var(--text-muted)" style={{ margin: '0 auto 12px auto', display: 'block' }} />
          <h4 style={{ fontSize: '16px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
            No Saved Addresses Yet
          </h4>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Add your Home, Work, or Hostel address to enable 1-word order confirmations with AI agents.
          </p>
          <button onClick={() => setShowAddModal(true)} className="btn btn-secondary btn-sm">
            <Plus size={14} /> Add First Address
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {addresses.map((addr) => (
            <div
              key={addr.address_id}
              className="glass-panel-interactive"
              style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
            >
              <div>
                {/* Header with Label & Default Badge */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <span style={{
                    fontSize: '14px',
                    fontWeight: 700,
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    {getLabelIcon(addr.label)}
                    {addr.label}
                  </span>
                  {addr.is_default && (
                    <span className="badge badge-primary" style={{ fontSize: '10px', padding: '2px 6px' }}>
                      Default
                    </span>
                  )}
                </div>

                {/* Street Details */}
                <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.4, marginBottom: '6px' }}>
                  {addr.line1}
                  {addr.line2 && <span style={{ display: 'block', color: 'var(--text-muted)' }}>{addr.line2}</span>}
                </p>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
                  {addr.city}, {addr.state} - {addr.postal_code}, {addr.country}
                </p>

                {/* Phone & Notes */}
                {addr.phone && (
                  <p style={{ fontSize: '12px', color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                    <Phone size={12} /> {addr.phone}
                  </p>
                )}
                {addr.delivery_notes && (
                  <p style={{ fontSize: '11px', color: 'var(--text-subtle)', fontStyle: 'italic' }}>
                    Note: {addr.delivery_notes}
                  </p>
                )}
              </div>

              {/* Delete Button */}
              <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '10px' }}>
                <button
                  onClick={() => handleDelete(addr.address_id)}
                  className="btn btn-danger btn-sm"
                  style={{ padding: '4px 8px', fontSize: '11px' }}
                >
                  <Trash2 size={12} /> Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Address Modal */}
      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '540px' }}>
            <div className="modal-header">
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginBottom: '4px' }}>
                  Add Saved Location
                </h3>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  Create a named shortcut for your home, office, or frequent delivery point.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: '6px'
                }}
              >
                <X size={20} />
              </button>
            </div>

            {error && (
              <div style={{ padding: '8px 12px', background: 'rgba(244, 63, 94, 0.15)', color: '#F43F5E', borderRadius: '8px', fontSize: '13px', marginBottom: '14px', flexShrink: 0 }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSaveAddress} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
              <div className="modal-scroll-body">
                <div className="form-group">
                  <label>Address Label / Shortcut (e.g. Home, Work, Gym) <span style={{ color: '#F43F5E' }}>*</span></label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Home"
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Street Address & Flat / Building <span style={{ color: '#F43F5E' }}>*</span></label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Flat 402, Palm Grove Apartments, 100ft Road"
                    value={line1}
                    onChange={(e) => setLine1(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>
                    Area / Landmark <span style={{ color: '#F43F5E' }}>*</span>
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Near Metro Pillar 84, Opp. Starbucks"
                    value={line2}
                    onChange={(e) => setLine2(e.target.value)}
                    required
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>City <span style={{ color: '#F43F5E' }}>*</span></label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Bengaluru"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>State / PIN <span style={{ color: '#F43F5E' }}>*</span></label>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="KA"
                        value={state}
                        onChange={(e) => setState(e.target.value)}
                        required
                      />
                      <input
                        type="text"
                        className="form-control"
                        placeholder="560038"
                        value={postalCode}
                        onChange={(e) => setPostalCode(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label>Phone Number for Delivery</label>
                  <input
                    type="tel"
                    className="form-control"
                    placeholder="+919876543210"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Delivery / Gate Notes</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Leave with security at Gate 2"
                    value={deliveryNotes}
                    onChange={(e) => setDeliveryNotes(e.target.value)}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '10px', marginBottom: '8px' }}>
                  <input
                    type="checkbox"
                    id="isDefaultCheck"
                    checked={isDefault}
                    onChange={(e) => setIsDefault(e.target.checked)}
                    style={{ accentColor: '#38BDF8', width: '16px', height: '16px' }}
                  />
                  <label htmlFor="isDefaultCheck" style={{ fontSize: '13px', color: 'var(--text-muted)', cursor: 'pointer' }}>
                    Set as default address for AI agent checkouts
                  </label>
                </div>
              </div>

              {/* Sticky Action Footer */}
              <div className="modal-sticky-footer">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn btn-secondary btn-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="btn btn-primary btn-sm"
                >
                  {saving ? 'Saving...' : 'Save Address'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
