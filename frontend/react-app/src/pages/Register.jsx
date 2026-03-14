import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import Confetti from 'react-confetti';
import toast from 'react-hot-toast';
import { checkUsername } from '../services/api';
import { useAuth } from '../context/AuthContext';

const schema = z.object({
  full_name: z.string().min(2, 'Full name is required'),
  email: z.string().email('Enter a valid email'),
  username: z.string().min(3).max(20).regex(/^[A-Za-z0-9_]+$/, 'Use letters, numbers, underscore only'),
  password: z.string().min(8, 'Minimum 8 characters').regex(/[0-9]/, 'Include at least one number'),
  confirm_password: z.string().min(8),
  avatar_color: z.string().min(4),
}).refine((v) => v.password === v.confirm_password, { message: 'Passwords must match', path: ['confirm_password'] });

function getPasswordStrength(password) {
  let score = 0;
  if (password.length >= 8) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  const labels = ['Weak', 'Fair', 'Strong', 'Very Strong'];
  return { score, label: labels[Math.max(0, score - 1)] || 'Weak' };
}

export default function Register() {
  const navigate = useNavigate();
  const { register: registerUser, login, isAuthenticated } = useAuth();
  const [isAvailable, setIsAvailable] = useState(null);
  const [showConfetti, setShowConfetti] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    mode: 'onBlur',
    defaultValues: { avatar_color: '#6366f1' },
  });

  const username = watch('username');
  const password = watch('password') || '';
  const strength = useMemo(() => getPasswordStrength(password), [password]);

  useEffect(() => {
    if (!username || username.length < 3) {
      setIsAvailable(null);
      return;
    }
    const timeout = setTimeout(async () => {
      try {
        const data = await checkUsername(username);
        setIsAvailable(!!data.available);
      } catch {
        setIsAvailable(null);
      }
    }, 500);
    return () => clearTimeout(timeout);
  }, [username]);

  if (isAuthenticated) return <Navigate to="/" replace />;

  const onSubmit = async (values) => {
    try {
      await registerUser(values);
      await login(values.username, values.password, true);
      localStorage.setItem('veritasai_first_login_done', '1');
      setShowConfetti(true);
      toast.success('Account created successfully');
      setTimeout(() => navigate('/'), 1200);
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Registration failed');
    }
  };

  return (
    <main style={{ minHeight: 'calc(100vh - 64px)', display: 'grid', placeItems: 'center', padding: '2rem 1rem' }}>
      {showConfetti && <Confetti recycle={false} numberOfPieces={180} />}
      <section className="glass" style={{ width: '100%', maxWidth: 460, padding: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', marginBottom: 6 }}>🔍 Join VeritasAI</h1>
        <p style={{ opacity: 0.7, marginBottom: 18 }}>Create your account</p>

        <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'grid', gap: 10 }}>
          <input {...register('full_name')} placeholder="Full Name" style={{ padding: '11px', borderRadius: 12, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }} />
          {errors.full_name && <small style={{ color: '#f87171' }}>{errors.full_name.message}</small>}

          <input {...register('email')} placeholder="Email" style={{ padding: '11px', borderRadius: 12, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }} />
          {errors.email && <small style={{ color: '#f87171' }}>{errors.email.message}</small>}

          <input {...register('username')} placeholder="Username" style={{ padding: '11px', borderRadius: 12, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }} />
          {isAvailable === true && <small style={{ color: '#34d399' }}>Username available</small>}
          {isAvailable === false && <small style={{ color: '#f87171' }}>Username already taken</small>}
          {errors.username && <small style={{ color: '#f87171' }}>{errors.username.message}</small>}

          <input type="password" {...register('password')} placeholder="Password" style={{ padding: '11px', borderRadius: 12, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }} />
          <input type="password" {...register('confirm_password')} placeholder="Confirm Password" style={{ padding: '11px', borderRadius: 12, border: '1px solid var(--border-dark)', background: 'transparent', color: 'inherit' }} />
          {(errors.password || errors.confirm_password) && <small style={{ color: '#f87171' }}>{errors.password?.message || errors.confirm_password?.message}</small>}

          <label style={{ fontSize: '0.85rem', opacity: 0.8 }}>Avatar Color</label>
          <input type="color" {...register('avatar_color')} style={{ width: 60, height: 36, background: 'transparent', border: 'none' }} />

          <div style={{ marginTop: 4 }}>
            <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>Password strength: {'█'.repeat(Math.max(1, strength.score))}{'░'.repeat(4 - Math.max(1, strength.score))} {strength.label}</div>
          </div>

          <button type="submit" disabled={isSubmitting} style={{ marginTop: 8, border: 'none', borderRadius: 12, padding: '12px', cursor: 'pointer', color: 'white', fontWeight: 700, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)' }}>
            {isSubmitting ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <p style={{ marginTop: 14, fontSize: '0.9rem', opacity: 0.8 }}>
          Already have account? <Link to="/login" style={{ color: '#818cf8' }}>Login</Link>
        </p>
      </section>
    </main>
  );
}
