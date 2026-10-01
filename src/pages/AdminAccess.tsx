import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Lock, Mail, Shield, User, KeyRound } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API_ENDPOINTS, sanitizeInput } from "@/config/api";
import { useAuth } from "@/contexts/AuthContext";

const AdminAccess = () => {
  const isRegistering = useLocation().pathname === "/admin/register";
  const navigate = useNavigate();
  const { adminLogin } = useAuth();
  const [form, setForm] = useState({
    name: "",
    username: "",
    email: "",
    password: "",
    setupKey: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      if (isRegistering) {
        const response = await fetch(API_ENDPOINTS.AUTH.ADMIN_REGISTER, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: sanitizeInput(form.name),
            username: sanitizeInput(form.username),
            email: sanitizeInput(form.email).toLowerCase(),
            password: form.password,
            setup_key: form.setupKey,
          }),
        });
        const data = await response.json() as { error?: string; message?: string };
        if (!response.ok) throw new Error(data.error || data.message || "Admin registration failed.");
        navigate("/admin/login", { replace: true, state: { message: data.message } });
      } else {
        await adminLogin(sanitizeInput(form.email).toLowerCase(), form.password);
        navigate("/admin", { replace: true });
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to complete admin access.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-20">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-md mx-auto"
          >
            <div className="text-center mb-8">
              <div className="w-16 h-16 rounded-2xl bg-primary/15 flex items-center justify-center mx-auto mb-4">
                <Shield className="w-8 h-8 text-primary" />
              </div>
              <h1 className="font-display text-3xl font-bold mb-2">
                {isRegistering ? "Create First Admin" : "Admin Sign In"}
              </h1>
              <p className="text-muted-foreground">
                {isRegistering
                  ? "Bootstrap the initial administrator account."
                  : "Sign in with your SoundWars administrator account."}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="glass rounded-2xl p-6 space-y-5">
              {isRegistering && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="admin-name">Full name</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input id="admin-name" className="pl-10" autoComplete="name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="admin-username">Username</Label>
                    <Input id="admin-username" autoComplete="username" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} required minLength={3} maxLength={30} />
                  </div>
                </>
              )}

              <div className="space-y-2">
                <Label htmlFor="admin-email">Email address</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input id="admin-email" type="email" className="pl-10" autoComplete="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="admin-password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input id="admin-password" type="password" className="pl-10" autoComplete={isRegistering ? "new-password" : "current-password"} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required minLength={8} />
                </div>
              </div>

              {isRegistering && (
                <div className="space-y-2">
                  <Label htmlFor="admin-setup-key">Admin setup key</Label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input id="admin-setup-key" type="password" className="pl-10" autoComplete="off" value={form.setupKey} onChange={(event) => setForm({ ...form, setupKey: event.target.value })} required />
                  </div>
                  <p className="text-xs text-muted-foreground">This key must match the server's ADMIN_SETUP_KEY and is required only for initial setup.</p>
                </div>
              )}

              {error && <p role="alert" className="text-sm text-destructive text-center">{error}</p>}

              <Button type="submit" variant="hero" size="lg" className="w-full" disabled={isLoading}>
                {isLoading
                  ? "Please wait..."
                  : isRegistering ? "Create Admin Account" : "Sign In as Admin"}
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                {isRegistering ? "Already have an admin account? " : "Need to set up the first admin? "}
                <Link to={isRegistering ? "/admin/login" : "/admin/register"} className="text-primary hover:underline">
                  {isRegistering ? "Admin sign in" : "Initial admin setup"}
                </Link>
              </p>
            </form>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default AdminAccess;