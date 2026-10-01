import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { CheckCircle, XCircle, Music2 } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { API_ENDPOINTS } from "@/config/api";

const ActivateAccount = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      return;
    }

    const activate = async () => {
      try {
        const response = await fetch(API_ENDPOINTS.AUTH.ACTIVATE, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        setStatus(response.ok ? "success" : "error");
      } catch {
        setStatus("error");
      }
    };

    activate();
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-20">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-md mx-auto text-center"
          >
            {status === "loading" && (
              <>
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-r from-primary to-secondary flex items-center justify-center mx-auto mb-6">
                  <Music2 className="w-8 h-8 text-primary-foreground" />
                </div>
                <h1 className="font-display text-3xl font-bold mb-4">Activating Account</h1>
                <p className="text-muted-foreground">Please wait while we confirm your email address.</p>
              </>
            )}

            {status === "success" && (
              <>
                <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-6">
                  <CheckCircle className="w-8 h-8 text-green-500" />
                </div>
                <h1 className="font-display text-3xl font-bold mb-4">Account Activated</h1>
                <p className="text-muted-foreground mb-6">Your email has been confirmed. You can now sign in to SoundWars.</p>
                <Link to="/login">
                  <Button variant="hero" className="w-full">Go to Login</Button>
                </Link>
              </>
            )}

            {status === "error" && (
              <>
                <div className="w-16 h-16 rounded-full bg-destructive/20 flex items-center justify-center mx-auto mb-6">
                  <XCircle className="w-8 h-8 text-destructive" />
                </div>
                <h1 className="font-display text-3xl font-bold mb-4">Invalid or Expired Link</h1>
                <p className="text-muted-foreground mb-6">This activation link is invalid or has expired. Please request a new activation email.</p>
                <div className="space-y-3">
                  <Link to="/login">
                    <Button variant="hero" className="w-full">Go to Login</Button>
                  </Link>
                  <Link to="/register">
                    <Button variant="outline" className="w-full">Create an Account</Button>
                  </Link>
                </div>
              </>
            )}
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default ActivateAccount;
