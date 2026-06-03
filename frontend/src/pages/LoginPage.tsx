import { useState } from "react";
import { ShieldCheck, Lock, User, Eye, EyeOff } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { useNavigate } from "react-router-dom";

export function LoginPage() {
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("analyst123");
  const [showPwd, setShowPwd] = useState(false);
  const { login, isLoading, error } = useAuthStore();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await login(username, password);
    if (!useAuthStore.getState().error) navigate("/");
  }

  const demoUsers = [
    { username: "admin", password: "admin123", role: "Admin" },
    { username: "analyst", password: "analyst123", role: "Analyst" },
    { username: "operator", password: "operator123", role: "Operator" },
  ];

  return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600/20 rounded-2xl mb-4">
            <ShieldCheck className="text-blue-400" size={32} />
          </div>
          <h1 className="text-2xl font-bold text-white">SurveillanceIQ</h1>
          <p className="text-slate-400 text-sm mt-1">AI Surveillance Intelligence Platform</p>
        </div>

        {/* Card */}
        <div className="bg-[#0f1629] border border-[#1e2d4a] rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-white mb-6">Sign In</h2>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg p-3 mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 mb-1.5 block">Username</label>
              <div className="relative">
                <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  className="w-full bg-[#141c2e] border border-[#1e2d4a] text-white rounded-lg pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Username"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1.5 block">Password</label>
              <div className="relative">
                <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showPwd ? "text" : "password"}
                  className="w-full bg-[#141c2e] border border-[#1e2d4a] text-white rounded-lg pl-9 pr-10 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                />
                <button type="button" onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                  {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50 text-sm"
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-6 pt-5 border-t border-[#1e2d4a]">
            <p className="text-xs text-slate-500 mb-3">Demo accounts:</p>
            <div className="space-y-1.5">
              {demoUsers.map((u) => (
                <button key={u.username} onClick={() => { setUsername(u.username); setPassword(u.password); }}
                  className="w-full text-left flex justify-between items-center px-3 py-2 rounded-lg bg-[#141c2e] hover:bg-[#1a2540] transition-colors text-xs">
                  <span className="text-slate-300">{u.username} / {u.password}</span>
                  <span className="text-slate-500">{u.role}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
