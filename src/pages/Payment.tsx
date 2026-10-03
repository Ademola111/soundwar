import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { AlertCircle, Check, CreditCard, Shield } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { API_ENDPOINTS, APP_CONFIG, getAuthHeaders } from "@/config/api";

const Payment = () => {
  const { user, token, isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const artistProfile = user?.artist_profile;

  useEffect(() => {
    if (isAuthLoading) return;
    if (!isAuthenticated) {
      navigate("/login", { replace: true });
    } else if (artistProfile?.is_paid && !artistProfile.requires_season_payment) {
      navigate("/submit", { replace: true });
    }
  }, [artistProfile?.is_paid, artistProfile?.requires_season_payment, isAuthLoading, isAuthenticated, navigate]);

  const handlePayment = async () => {
    if (!token) {
      navigate("/login");
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      const txRef = `SW-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
      const response = await fetch(API_ENDPOINTS.PAYMENTS.INITIALIZE, {
        method: "POST",
        headers: getAuthHeaders(token),
        body: JSON.stringify({
          tx_ref: txRef,
          redirect_url: `${window.location.origin}/payment/success`,
          email: user?.email,
        }),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok || !data.payment_link) {
        throw new Error(data.error || data.message || "Unable to start payment right now.");
      }

      window.location.href = data.payment_link;
    } catch (paymentError) {
      setError(paymentError instanceof Error ? paymentError.message : "Unable to start payment right now.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const isArtist = Boolean(artistProfile);

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
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-r from-accent to-secondary flex items-center justify-center mx-auto mb-4">
                <CreditCard className="w-8 h-8 text-white" />
              </div>
              <h1 className="font-display text-3xl font-bold mb-2">Complete Payment</h1>
              <p className="text-muted-foreground">
                {artistProfile?.requires_season_payment
                  ? "Complete this season's participation payment before uploading your track."
                  : "Complete your artist registration payment to upload your track."}
              </p>
            </div>

            <div className="glass rounded-2xl p-6 space-y-6">
              {isArtist ? (
                <>
                  <div className="bg-gradient-to-br from-accent/20 to-secondary/20 rounded-xl p-6 border border-accent/30">
                    <div className="flex justify-between items-start gap-4 mb-6">
                      <div>
                        <h2 className="font-semibold text-lg">
                          {artistProfile?.requires_season_payment ? "Season Participation" : "Artist Registration"}
                        </h2>
                        <p className="text-sm text-muted-foreground">SoundWars Competition</p>
                      </div>
                      <p className="text-2xl font-bold text-accent whitespace-nowrap">
                        {APP_CONFIG.ARTIST_REGISTRATION_FEE_DISPLAY}
                      </p>
                    </div>
                    <div className="space-y-3 text-sm">
                      <p className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Submit your track to the competition</p>
                      <p className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Compete for the grand prize</p>
                    </div>
                  </div>

                  {error && (
                    <p role="alert" className="flex items-start gap-2 text-sm text-destructive">
                      <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                      {error}
                    </p>
                  )}

                  <Button
                    variant="hero"
                    size="lg"
                    className="w-full"
                    onClick={handlePayment}
                    disabled={isSubmitting || isAuthLoading}
                  >
                    {isSubmitting ? "Opening secure checkout..." : "Continue to Secure Payment"}
                  </Button>

                  <div className="flex items-center gap-2 justify-center text-xs text-muted-foreground">
                    <Shield className="w-4 h-4 text-primary" />
                    <span>Card details are entered securely on Flutterwave.</span>
                  </div>
                </>
              ) : (
                <div className="text-center space-y-4">
                  <p className="text-muted-foreground">Payment is available for artist accounts only.</p>
                  <Button variant="outline" className="w-full" onClick={() => navigate("/")}>
                    Return Home
                  </Button>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Payment;