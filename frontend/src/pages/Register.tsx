import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { register as registerApi } from '@/api/authApi'
import { useMutation } from '@tanstack/react-query'
import loginBg from '@/assets/img1.jpg'
import { Lock, Mail, Shield, Headphones } from 'lucide-react'

type FormState = {
  username: string
  email: string
  password: string
  confirmPassword: string
}

type Errors = Record<string, string>

export default function Register() {
  const [form, setForm] = useState<FormState>({ username: '', email: '', password: '', confirmPassword: '' })
  const [errors, setErrors] = useState<Errors>({})
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: ({ username, email, password }: { username: string; email: string; password: string }) => registerApi(username, email, password),
  })

  const featureCards = [
    { title: '⚡ Faster Whisper STT', subtitle: 'Real-time speech transcription' },
    { title: '🔗 Smart Incident Correlation', subtitle: 'AI groups related emergency calls' },
    { title: '🧠 AI Severity Engine', subtitle: 'Predictive emergency prioritization' },
  ]

  const emergencyNumbers = [
    { label: '112', name: 'Emergency', tone: 'text-red-400', ring: 'bg-red-500/10' },
    { label: '100', name: 'Police', tone: 'text-sky-400', ring: 'bg-sky-500/10' },
    { label: '101', name: 'Fire', tone: 'text-orange-300', ring: 'bg-orange-500/10' },
    { label: '108', name: 'Ambulance', tone: 'text-emerald-400', ring: 'bg-emerald-500/10' },
    { label: '181', name: 'Women', tone: 'text-violet-400', ring: 'bg-violet-500/10' },
    { label: '1098', name: 'Child', tone: 'text-cyan-400', ring: 'bg-cyan-500/10' },
  ]

  function validateForm(): boolean {
    const newErrors: Errors = {}

    if (!form.username || form.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters'
    }

    if (!form.email || !form.email.includes('@')) {
      newErrors.email = 'Please enter a valid email address'
    }

    if (!form.password || form.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters'
    }

    if (form.password !== form.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErrors({})

    if (!validateForm()) {
      return
    }

    try {
      await mutation.mutateAsync({
        username: form.username,
        email: form.email,
        password: form.password,
      })
      navigate('/login', { state: { message: 'Registration successful! Please login with your credentials.' } })
    } catch (e: any) {
      console.error('register error', e)
      const errorMsg = e?.response?.data?.detail || e?.message || 'Registration failed'
      setErrors({ submit: errorMsg })
    }
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row overflow-hidden bg-[#090B12] text-white">
      <div
        className="relative w-full lg:w-[50%] overflow-hidden px-10 py-8"
        style={{
          backgroundImage: `linear-gradient(rgba(5,10,18,.82),rgba(5,10,18,.82)),url(${loginBg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(146,224,255,0.06),_transparent_20%),radial-gradient(circle_at_bottom_right,_rgba(239,68,68,0.08),_transparent_25%)]" />
        <div className="absolute left-[-90px] top-[18%] h-[420px] w-[420px] rounded-full bg-[#111827] opacity-35 blur-3xl" />
        <div className="absolute inset-x-0 bottom-0 h-[200px] bg-[radial-gradient(circle_at_center,_rgba(239,68,68,0.12),_transparent_70%)]" />
        <div className="relative z-10 flex h-full flex-col justify-between gap-10">
          <div className="space-y-8">
            <div className="space-y-3">
              <div className="flex items-end gap-3 text-4xl font-bold leading-none">
                <span>Emergency</span>
                <span className="text-[#ef4444]">IQ</span>
              </div>
              <div className="text-base text-zinc-300">AI Powered Emergency Dispatch Platform</div>
            </div>

            <div className="grid gap-4">
              {featureCards.map((card) => (
                <div key={card.title} className="transform rounded-2xl border border-white/10 bg-white/4 px-4 py-3 transition duration-200 ease-out hover:-translate-y-1 hover:border-white/20">
                  <div className="text-sm font-semibold text-white">{card.title}</div>
                  <div className="mt-1 text-sm text-zinc-300">{card.subtitle}</div>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              <div className="text-lg font-semibold">India Emergency Network</div>
              <div className="grid grid-cols-3 gap-3">
                {emergencyNumbers.map((item) => (
                  <div key={item.label} className={`group h-20 w-[110px] rounded-3xl border border-white/10 bg-white/5 p-3 transition duration-200 ease-out hover:-translate-y-1 hover:scale-[1.02] ${item.ring}`}>
                    <div className="text-2xl font-bold tracking-wide text-white">{item.label}</div>
                    <div className={`mt-2 text-sm font-semibold ${item.tone}`}>{item.name}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[28px] border border-white/10 bg-white/5 p-4 backdrop-blur-xl">
              <div className="grid grid-cols-2 gap-3 text-sm text-zinc-300">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />
                  <span>Secure</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />
                  <span>Reliable</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />
                  <span>AI Powered</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />
                  <span>Always Online</span>
                </div>
              </div>
            </div>
            <div className="text-sm text-zinc-400">© 2026 EmergencyIQ</div>
          </div>
        </div>
      </div>

      <div className="w-full lg:w-[50%] bg-[#F8FAFC] flex items-center justify-center px-8 py-10">
        <div className="w-full max-w-[460px]">
          <div className="rounded-[20px] border border-black/10 bg-white/90 p-8 shadow-[0_24px_64px_rgba(15,23,42,0.08)] backdrop-blur-[24px]">
            <div className="mb-6 text-center">
              <div className="text-[32px] font-bold text-slate-900">Create an account</div>
              <div className="text-sm text-slate-500">Get started with EmergencyIQ</div>
            </div>
            <form onSubmit={submit} className="space-y-4">
              {errors.submit && <div className="text-sm text-red-600">{errors.submit}</div>}
              <div>
                <label htmlFor="username" className="text-sm font-medium text-slate-700">Username</label>
                <input
                  id="username"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  placeholder="Username"
                  className="mt-1 w-full rounded-[12px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
                />
                {errors.username && <div className="mt-1 text-sm text-red-600">{errors.username}</div>}
              </div>
              <div>
                <label htmlFor="email" className="text-sm font-medium text-slate-700">Email</label>
                <input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="you@agency.example"
                  className="mt-1 w-full rounded-[12px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
                />
                {errors.email && <div className="mt-1 text-sm text-red-600">{errors.email}</div>}
              </div>
              <div>
                <label htmlFor="password" className="text-sm font-medium text-slate-700">Password</label>
                <input
                  id="password"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                  className="mt-1 w-full rounded-[12px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
                />
                {errors.password && <div className="mt-1 text-sm text-red-600">{errors.password}</div>}
              </div>
              <div>
                <label htmlFor="confirmPassword" className="text-sm font-medium text-slate-700">Confirm password</label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={form.confirmPassword}
                  onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                  placeholder="Confirm password"
                  className="mt-1 w-full rounded-[12px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
                />
                {errors.confirmPassword && <div className="mt-1 text-sm text-red-600">{errors.confirmPassword}</div>}
              </div>
                          <button
                type="submit"
                disabled={mutation.isPending}
                className="w-full rounded-[12px] bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-black transition disabled:opacity-60"
              >
                {mutation.isPending ? 'Creating account...' : 'Create account'}
              </button>
              <div className="text-center text-sm text-slate-500">
                Already have an account? <button type="button" onClick={() => navigate('/login')} className="font-semibold text-sky-600 hover:underline">Sign in</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
