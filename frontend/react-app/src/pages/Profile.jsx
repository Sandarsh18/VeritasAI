import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { changePassword, getUserClaims, getUserStats } from '../services/api';

function initials(name = '') {
  return name.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
}

export default function Profile() {
  const { user, updateProfile, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [avatarColor, setAvatarColor] = useState(user?.avatar_color || '#6366f1');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    Promise.all([getUserStats(), getUserClaims({ limit: 50 })])
      .then(([statsData, claimsData]) => {
        setStats(statsData);
        setClaims(claimsData.claims || []);
      })
      .catch(() => {
        setStats(null);
        setClaims([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const bookmarked = useMemo(() => claims.filter((c) => c.bookmarked), [claims]);

  const handleProfileSave = async () => {
    try {
      await updateProfile({ full_name: fullName, avatar_color: avatarColor });
      toast.success('Profile updated');
    } catch {
      toast.error('Failed to update profile');
    }
  };

  const handlePasswordChange = async () => {
    if (!currentPassword || !newPassword) return;
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword('');
      setNewPassword('');
      toast.success('Password changed');
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Failed to change password');
    }
  };

  if (loading) {
    return <main style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem 1rem' }}><div className="skeleton" style={{ height: 280 }} /></main>;
  }

  return (
    <main style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem 1rem 4rem' }}>
      <section className="glass" style={{ padding: '1.2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: user?.avatar_color || '#6366f1', display: 'grid', placeItems: 'center', color: 'white', fontWeight: 800 }}>
            {initials(user?.full_name || user?.username)}
          </div>
          <div>
            <h2>{user?.full_name}</h2>
            <p style={{ opacity: 0.7 }}>@{user?.username} • Member since {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</p>
          </div>
        </div>

        <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', gap: 10 }}>
          <div className="glass" style={{ padding: 10 }}><strong>{stats?.total_claims || 0}</strong><p style={{ opacity: 0.7 }}>Claims</p></div>
          <div className="glass" style={{ padding: 10 }}><strong>{stats?.verdict_breakdown?.FALSE || 0}</strong><p style={{ opacity: 0.7 }}>FALSE</p></div>
          <div className="glass" style={{ padding: 10 }}><strong>{stats?.verdict_breakdown?.TRUE || 0}</strong><p style={{ opacity: 0.7 }}>TRUE</p></div>
          <div className="glass" style={{ padding: 10 }}><strong>{stats?.verdict_breakdown?.UNVERIFIED || 0}</strong><p style={{ opacity: 0.7 }}>UNVER.</p></div>
        </div>

        <div style={{ marginTop: 20 }}>
          <h3>🔖 Bookmarked Claims</h3>
          {bookmarked.length === 0 ? (
            <p style={{ opacity: 0.7, marginTop: 8 }}>🔍 You haven&apos;t verified any claims yet. Verify your first claim on home.</p>
          ) : (
            <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
              {bookmarked.slice(0, 8).map((c) => (
                <div key={c.id} className="glass" style={{ padding: 10 }}>
                  <p style={{ fontWeight: 500 }}>{c.text}</p>
                  <small style={{ opacity: 0.7 }}>{c.verdict} • {Math.round(c.confidence || 0)}%</small>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ marginTop: 20, display: 'grid', gap: 10 }}>
          <h3>⚙️ Edit Profile</h3>
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full Name" style={{ padding: 10, borderRadius: 10, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }} />
          <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>Avatar color <input type="color" value={avatarColor} onChange={(e) => setAvatarColor(e.target.value)} /></label>
          <button onClick={handleProfileSave} style={{ width: 180, border: 'none', borderRadius: 10, padding: '10px 12px', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: 'white', fontWeight: 600, cursor: 'pointer' }}>Save Profile</button>

          <h3 style={{ marginTop: 8 }}>🔑 Change Password</h3>
          <input value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} placeholder="Current password" type="password" style={{ padding: 10, borderRadius: 10, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }} />
          <input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="New password" type="password" style={{ padding: 10, borderRadius: 10, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }} />
          <button onClick={handlePasswordChange} style={{ width: 180, border: '1px solid var(--border-dark)', borderRadius: 10, padding: '10px 12px', background: 'transparent', color: 'inherit', cursor: 'pointer' }}>Update Password</button>

          <h3 style={{ marginTop: 8 }}>🚪 Logout</h3>
          <button onClick={logout} style={{ width: 120, border: '1px solid #ef4444', borderRadius: 10, padding: '10px 12px', background: 'transparent', color: '#f87171', cursor: 'pointer' }}>Logout</button>
        </div>
      </section>
    </main>
  );
}
