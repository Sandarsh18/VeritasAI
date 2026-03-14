import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';

const schema = z.object({
  username_or_email: z.string().min(3, 'Username or email is required'),
  password: z.string().min(1, 'Password is required'),
  remember_me: z.boolean().optional(),
});

export default function Login() {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { username_or_email: '', password: '', remember_me: false },
  });

  if (isAuthenticated) return <Navigate to="/" replace />;

  const onSubmit = async (values) => {
    try {
      await login(values.username_or_email, values.password, values.remember_me);
      toast.success('Login successful');
      navigate('/');
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <main style={{ minHeight: 'calc(100vh - 64px)', display: 'grid', placeItems: 'center', padding: '2rem 1rem' }}>
      <section className="glass" style={{ width: '100%', maxWidth: 420, padding: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', marginBottom: 6 }}>🔍 VeritasAI</h1>
        <p style={{ opacity: 0.7, marginBottom: 18 }}>Welcome back</p>

        <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'grid', gap: 12 }}>
          <input
            {...register('username_or_email')}
            placeholder="Username or Email"
            style={{ padding: '12px 14px', borderRadius: 12, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }}
          />
          {errors.username_or_email && <small style={{ color: '#f87171' }}>{errors.username_or_email.message}</small>}

          <div style={{ position: 'relative' }}>
            <input
              {...register('password')}
              placeholder="Password"
              type={showPassword ? 'text' : 'password'}
              style={{ width: '100%', padding: '12px 44px 12px 14px', borderRadius: 12, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }}
            />
            <button type="button" onClick={() => setShowPassword(!showPassword)} style={{ position: 'absolute', right: 10, top: 10, background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {errors.password && <small style={{ color: '#f87171' }}>{errors.password.message}</small>}

          <label style={{ display: 'flex', gap: 8, fontSize: '0.9rem', opacity: 0.85 }}>
            <input type="checkbox" {...register('remember_me')} /> Remember me (30 days)
          </label>

          <button type="submit" disabled={isSubmitting} style={{ border: 'none', borderRadius: 12, padding: '12px', cursor: 'pointer', color: 'white', fontWeight: 700, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)' }}>
            {isSubmitting ? 'Signing in...' : 'Login'}
          </button>
        </form>

        <div style={{ margin: '16px 0', textAlign: 'center', opacity: 0.6 }}>──────── or ────────</div>
        <button onClick={() => navigate('/')} style={{ width: '100%', borderRadius: 10, border: '1px solid var(--border-dark)', padding: '10px', background: 'transparent', color: 'inherit', cursor: 'pointer' }}>
          Continue as Guest →
        </button>

        <p style={{ marginTop: 14, fontSize: '0.9rem', opacity: 0.8 }}>
          Don&apos;t have account? <Link to="/register" style={{ color: '#818cf8' }}>Sign Up</Link>
        </p>
      </section>
    </main>
  );
}
