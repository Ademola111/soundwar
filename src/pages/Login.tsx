import { motion } from "framer-motion";
import { useState } from "react";
import { Music2, Mail, Lock } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { API_ENDPOINTS, sanitizeInput, VALIDATION_PATTERNS } from "@/config/api";

const Login = () => {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isResendingActivation, setIsResendingActivation] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { login } = useAuth();
  const { toast } = useToast();

  const resendActivation = async () => {
    setIsResendingActivation(true);
    try {
      await fetch(API_ENDPOINTS.AUTH.RESEND_ACTIVATION, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: sanitizeInput(formData.email.trim().toLowerCase()) }),
      });
      toast({
        title: "Activation Email Requested",
        description: "If the account is not active, a new activation link has been sent.",
      });
    } finally {
      setIsResendingActivation(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    const sanitizedEmail = sanitizeInput(formData.email.trim().toLowerCase());
    
    if (!VALIDATION_PATTERNS.email.test(sanitizedEmail)) {
      setError("Please enter a valid email address");
      return;
    }
    
    setIsLoading(true);
    
    try {
      const data = await login(sanitizedEmail, formData.password);
      toast({
        title: "Welcome back!",
        description: "You have successfully logged in.",
      });

      if (
        data?.user?.artist_profile &&
        (!data.user.artist_profile.is_paid || data.user.artist_profile.requires_season_payment)
      ) {
        toast({
          title: "Artist registration pending",
          description: "Complete payment before uploading your track.",
        });
        navigate("/payment");
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed. Please try again.");
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
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-md mx-auto"
          >
            {/* Header */}
            <div className="text-center mb-8">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-r from-[hsl(174,84%,50%)] to-[hsl(200,90%,50%)] flex items-center justify-center mx-auto mb-4">
                <Music2 className="w-8 h-8 text-[hsl(220,20%,4%)]" />
              </div>
              <h1 className="font-display text-3xl font-bold mb-2">Welcome Back</h1>
              <p className="text-muted-foreground">
                Sign in to continue to SoundWars
              </p>
            </div>

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="glass rounded-2xl p-6 space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    className="pl-10"
                    value={formData.email}
                    onChange={(e) => {
                      setFormData({ ...formData, email: e.target.value });
                      setError("");
                    }}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link to="/forgot-password" className="text-xs text-primary hover:underline">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter your password"
                    className="pl-10"
                    value={formData.password}
                    onChange={(e) => {
                      setFormData({ ...formData, password: e.target.value });
                      setError("");
                    }}
                    required
                  />
                </div>
              </div>

              {error && (
                <div className="space-y-2 text-center">
                  <p className="text-sm text-destructive">{error}</p>
                  {error.toLowerCase().includes("activate") && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={resendActivation}
                      disabled={isResendingActivation}
                    >
                      {isResendingActivation ? "Sending..." : "Resend activation email"}
                    </Button>
                  )}
                </div>
              )}

              <Button 
                type="submit" 
                variant="hero" 
                size="lg" 
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? "Signing in..." : "Sign In"}
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                Don't have an account?{" "}
                <Link to="/register" className="text-primary hover:underline">
                  Sign up
                </Link>
              </p>
              {/* <p className="text-center text-sm text-muted-foreground">
                Administrator?{" "}
                <Link to="/admin/login" className="text-primary hover:underline">
                  Admin sign in
                </Link>
              </p> */}
            </form>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Login;
