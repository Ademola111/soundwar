import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { XCircle, ArrowLeft } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";

const PaymentCancel = () => {
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
            <div className="glass rounded-2xl p-8">
              <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center mx-auto mb-6">
                <XCircle className="w-10 h-10 text-muted-foreground" />
              </div>
              
              <h1 className="font-display text-2xl font-bold mb-3">
                Payment Cancelled
              </h1>
              
              <p className="text-muted-foreground mb-8">
                No worries! Your payment was not processed. You can return anytime to complete your registration.
              </p>

              <div className="space-y-3">
                <Link to="/register">
                  <Button variant="hero" size="lg" className="w-full">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Return to Registration
                  </Button>
                </Link>
                
                <Link to="/">
                  <Button variant="glass" size="lg" className="w-full">
                    Go to Homepage
                  </Button>
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default PaymentCancel;
