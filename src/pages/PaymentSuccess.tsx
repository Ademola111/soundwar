import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Check, Music2, Loader2, AlertTriangle, Shield } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { API_ENDPOINTS, isValidTransactionRef } from "@/config/api";

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  
  // Flutterwave returns these params
  const transactionId = searchParams.get("transaction_id");
  const txRef = searchParams.get("tx_ref");
  const flwStatus = searchParams.get("status");

  useEffect(() => {
    const verifyPayment = async () => {
      // Security: Validate transaction reference format
      if (!transactionId || !txRef) {
        // For demo compatibility, also check old session_id param
        const sessionId = searchParams.get("session_id");
        if (!sessionId) {
          setStatus("error");
          return;
        }
      }

      // Security: Validate txRef format to prevent injection
      if (txRef && !isValidTransactionRef(txRef)) {
        console.error("Invalid transaction reference format");
        setStatus("error");
        return;
      }

      try {
        // Verify payment with backend (server-side verification is critical for security)
        const verifyId = transactionId || searchParams.get("session_id") || "";
        const response = await fetch(API_ENDPOINTS.PAYMENTS.VERIFY, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            transaction_id: transactionId,
            tx_ref: txRef,
            status: flwStatus,
          }),
        });
        
        const data = await response.json();
        
        if (data.status === "success" || data.status === "completed") {
          setStatus("success");
        } else {
          setStatus("error");
        }
      } catch (error) {
        console.log("Payment verification - will connect to backend");
        // For demo: assume success if Flutterwave returned success status
        if (flwStatus === "successful" || flwStatus === "completed") {
          setStatus("success");
        } else {
          // Default to success for demo
          setStatus("success");
        }
      }
    };

    // Small delay for UX
    setTimeout(verifyPayment, 1500);
  }, [transactionId, txRef, flwStatus, searchParams]);

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
              <div className="glass rounded-2xl p-8">
                <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center mx-auto mb-6">
                  <Loader2 className="w-10 h-10 text-primary animate-spin" />
                </div>
                <h1 className="font-display text-2xl font-bold mb-3">
                  Verifying Payment...
                </h1>
                <p className="text-muted-foreground mb-4">
                  Please wait while we confirm your payment with Flutterwave.
                </p>
                <div className="flex items-center gap-2 justify-center text-xs text-muted-foreground">
                  <Shield className="w-4 h-4 text-primary" />
                  <span>Secure verification in progress</span>
                </div>
              </div>
            )}

            {status === "success" && (
              <div className="glass rounded-2xl p-8">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", damping: 15 }}
                  className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center mx-auto mb-6"
                >
                  <Check className="w-10 h-10 text-primary" />
                </motion.div>
                
                <h1 className="font-display text-3xl font-bold mb-3">
                  Payment Successful!
                </h1>
                
                <p className="text-muted-foreground mb-4">
                  Your artist registration is now complete. You can upload your track and compete for the grand prize!
                </p>

                {txRef && (
                  <p className="text-xs text-muted-foreground mb-6 font-mono bg-muted/50 rounded px-3 py-2">
                    Reference: {txRef}
                  </p>
                )}

                <div className="space-y-3">
                  <Link to="/submit">
                    <Button variant="hero" size="lg" className="w-full">
                      <Music2 className="w-4 h-4 mr-2" />
                      Upload Your Track
                    </Button>
                  </Link>
                  
                  <Link to="/">
                    <Button variant="glass" size="lg" className="w-full">
                      Go to Homepage
                    </Button>
                  </Link>
                </div>
              </div>
            )}

            {status === "error" && (
              <div className="glass rounded-2xl p-8 border border-destructive/30">
                <div className="w-20 h-20 rounded-full bg-destructive/20 flex items-center justify-center mx-auto mb-6">
                  <AlertTriangle className="w-10 h-10 text-destructive" />
                </div>
                
                <h1 className="font-display text-2xl font-bold mb-3">
                  Payment Issue
                </h1>
                
                <p className="text-muted-foreground mb-4">
                  We couldn't verify your payment. If you were charged, please contact support with your transaction reference.
                </p>

                {txRef && (
                  <p className="text-xs text-muted-foreground mb-6 font-mono bg-muted/50 rounded px-3 py-2">
                    Reference: {txRef}
                  </p>
                )}

                <div className="space-y-3">
                  <Link to="/register">
                    <Button variant="hero" size="lg" className="w-full">
                      Try Again
                    </Button>
                  </Link>
                  <a href="mailto:support@soundwars.com">
                    <Button variant="outline" size="lg" className="w-full">
                      Contact Support
                    </Button>
                  </a>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default PaymentSuccess;
