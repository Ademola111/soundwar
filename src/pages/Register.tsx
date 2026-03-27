import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { Music2, User, Mail, Lock, Mic2, Users, CreditCard, Check, DollarSign, AlertTriangle, Shield } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Link } from "react-router-dom";
import { API_ENDPOINTS, APP_CONFIG, FLUTTERWAVE_CONFIG, VALIDATION, sanitizeInput } from "@/config/api";
import { useToast } from "@/hooks/use-toast";

type UserType = "artist" | "voter";
type RegistrationStep = "details" | "payment" | "success" | "blocked";

// Security: Form validation
const validateForm = (data: typeof initialFormData, userType: UserType): string | null => {
  if (!data.name.trim() || data.name.length > VALIDATION.NAME_MAX_LENGTH) {
    return "Please enter a valid name (max 100 characters)";
  }
  if (!VALIDATION.EMAIL_REGEX.test(data.email)) {
    return "Please enter a valid email address";
  }
  if (data.password.length < VALIDATION.PASSWORD_MIN_LENGTH) {
    return `Password must be at least ${VALIDATION.PASSWORD_MIN_LENGTH} characters`;
  }
  if (data.password !== data.confirmPassword) {
    return "Passwords do not match";
  }
  if (userType === "artist") {
    if (!data.artistName.trim() || data.artistName.length > VALIDATION.ARTIST_NAME_MAX_LENGTH) {
      return "Please enter a valid artist name (max 50 characters)";
    }
    if (!data.genre.trim() || data.genre.length > VALIDATION.GENRE_MAX_LENGTH) {
      return "Please enter a valid genre (max 30 characters)";
    }
  }
  return null;
};

const initialFormData = {
  name: "",
  email: "",
  password: "",
  confirmPassword: "",
  artistName: "",
  genre: "",
};

const Register = () => {
  const [userType, setUserType] = useState<UserType>("voter");
  const [step, setStep] = useState<RegistrationStep>("details");
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState(initialFormData);
  const [isWinner, setIsWinner] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Security: Validate form inputs
    const validationError = validateForm(formData, userType);
    if (validationError) {
      toast({
        title: "Validation Error",
        description: validationError,
        variant: "destructive",
      });
      return;
    }
    
    setIsLoading(true);
    
    try {
      // Sanitize inputs before sending
      const sanitizedData = {
        name: sanitizeInput(formData.name),
        email: sanitizeInput(formData.email),
        password: formData.password, // Don't sanitize password
        role: userType,
        artistName: userType === "artist" ? sanitizeInput(formData.artistName) : undefined,
        genre: userType === "artist" ? sanitizeInput(formData.genre) : undefined,
      };

      const response = await fetch(API_ENDPOINTS.AUTH.REGISTER, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sanitizedData),
      });
      
      const data = await response.json();
      
      // Security: Check if artist is a past winner (blocked from participation)
      if (data.is_past_winner) {
        setIsWinner(true);
        setStep("blocked");
        return;
      }
      
      if (data.requires_payment && userType === "artist") {
        setStep("payment");
      } else {
        setStep("success");
      }
    } catch (error) {
      console.log("Registration - will connect to backend:", { userType });
      // For demo: proceed to payment step for artists
      if (userType === "artist") {
        setStep("payment");
      } else {
        setStep("success");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handlePayment = async () => {
    setIsLoading(true);
    
    try {
      // Generate unique transaction reference
      const txRef = `SW-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      // Initialize Flutterwave payment
      const response = await fetch(API_ENDPOINTS.PAYMENTS.INITIALIZE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          contest_id: 1,
          tx_ref: txRef,
          amount: APP_CONFIG.ARTIST_REGISTRATION_FEE,
          currency: APP_CONFIG.CURRENCY,
          redirect_url: `${window.location.origin}/payment/success`,
          customer: {
            email: sanitizeInput(formData.email),
            name: sanitizeInput(formData.name),
          },
          customizations: {
            title: "SoundWars Artist Registration",
            description: "Contest participation fee",
            logo: `${window.location.origin}/favicon.ico`,
          },
        }),
      });
      
      const data = await response.json();
      
      if (data.payment_link) {
        // Redirect to Flutterwave payment page
        window.location.href = data.payment_link;
      }
    } catch (error) {
      console.log("Payment - will connect to Flutterwave:", { fee: APP_CONFIG.ARTIST_REGISTRATION_FEE });
      // For demo: proceed to success
      setStep("success");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-20">
        <div className="container mx-auto px-4">
          <AnimatePresence mode="wait">
            {step === "details" && (
              <motion.div
                key="details"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -30 }}
                className="max-w-md mx-auto"
              >
                {/* Header */}
                <div className="text-center mb-8">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-r from-primary to-secondary flex items-center justify-center mx-auto mb-4">
                    <Music2 className="w-8 h-8 text-primary-foreground" />
                  </div>
                  <h1 className="font-display text-3xl font-bold mb-2">Join SoundWars</h1>
                  <p className="text-muted-foreground">
                    Create your account to compete or vote
                  </p>
                </div>

                {/* Progress Steps - Show for artists */}
                {userType === "artist" && (
                  <div className="flex items-center justify-center gap-2 mb-8">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-sm font-bold text-primary-foreground">
                        1
                      </div>
                      <span className="text-sm font-medium">Details</span>
                    </div>
                    <div className="w-8 h-[2px] bg-muted" />
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-bold text-muted-foreground">
                        2
                      </div>
                      <span className="text-sm text-muted-foreground">Payment</span>
                    </div>
                  </div>
                )}

                {/* User Type Toggle */}
                <div className="glass rounded-xl p-2 flex gap-2 mb-8">
                  <button
                    onClick={() => setUserType("voter")}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-semibold transition-all ${
                      userType === "voter"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Users className="w-4 h-4" />
                    I Want to Vote
                  </button>
                  <button
                    onClick={() => setUserType("artist")}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-semibold transition-all ${
                      userType === "artist"
                        ? "bg-gradient-to-r from-accent to-secondary text-white"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Mic2 className="w-4 h-4" />
                    I'm an Artist
                  </button>
                </div>

                {/* Artist Fee Notice */}
                {userType === "artist" && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="glass rounded-xl p-4 mb-6 border border-accent/30"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center flex-shrink-0">
                        <DollarSign className="w-5 h-5 text-accent" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-sm mb-1">Artist Registration Fee</h3>
                        <p className="text-sm text-muted-foreground">
                          A one-time fee of <span className="text-accent font-bold">{APP_CONFIG.ARTIST_REGISTRATION_FEE_DISPLAY}</span> is required to participate in the competition. This covers platform costs and contributes to the prize pool.
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Registration Form */}
                <form onSubmit={handleSubmit} className="glass rounded-2xl p-6 space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="name"
                        placeholder="Enter your name"
                        className="pl-10"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        required
                      />
                    </div>
                  </div>

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
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        required
                      />
                    </div>
                  </div>

                  {userType === "artist" && (
                    <>
                      <div className="space-y-2">
                        <Label htmlFor="artistName">Artist / Stage Name</Label>
                        <div className="relative">
                          <Mic2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <Input
                            id="artistName"
                            placeholder="Your artist name"
                            className="pl-10"
                            value={formData.artistName}
                            onChange={(e) => setFormData({ ...formData, artistName: e.target.value })}
                            required
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="genre">Music Genre</Label>
                        <Input
                          id="genre"
                          placeholder="e.g., Electronic, Hip-Hop, Pop"
                          value={formData.genre}
                          onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
                          required
                        />
                      </div>
                    </>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="password"
                        type="password"
                        placeholder="Create a password"
                        className="pl-10"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="confirmPassword"
                        type="password"
                        placeholder="Confirm your password"
                        className="pl-10"
                        value={formData.confirmPassword}
                        onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                        required
                      />
                    </div>
                  </div>

                  <Button 
                    type="submit" 
                    variant="hero" 
                    size="lg" 
                    className="w-full"
                    disabled={isLoading}
                  >
                    {isLoading ? "Processing..." : userType === "artist" ? "Continue to Payment" : "Create Account"}
                  </Button>

                  <p className="text-center text-sm text-muted-foreground">
                    Already have an account?{" "}
                    <Link to="/login" className="text-primary hover:underline">
                      Sign in
                    </Link>
                  </p>
                </form>
              </motion.div>
            )}

            {step === "payment" && (
              <motion.div
                key="payment"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -30 }}
                className="max-w-md mx-auto"
              >
                {/* Header */}
                <div className="text-center mb-8">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-r from-accent to-secondary flex items-center justify-center mx-auto mb-4">
                    <CreditCard className="w-8 h-8 text-white" />
                  </div>
                  <h1 className="font-display text-3xl font-bold mb-2">Complete Payment</h1>
                  <p className="text-muted-foreground">
                    Pay the registration fee to enter the competition
                  </p>
                </div>

                {/* Progress Steps */}
                <div className="flex items-center justify-center gap-2 mb-8">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                      <Check className="w-4 h-4 text-primary-foreground" />
                    </div>
                    <span className="text-sm font-medium">Details</span>
                  </div>
                  <div className="w-8 h-[2px] bg-primary" />
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-sm font-bold text-white">
                      2
                    </div>
                    <span className="text-sm font-medium text-accent">Payment</span>
                  </div>
                </div>

                {/* Payment Card */}
                <div className="glass rounded-2xl p-6 space-y-6">
                  <div className="bg-gradient-to-br from-accent/20 to-secondary/20 rounded-xl p-6 border border-accent/30">
                    <div className="flex justify-between items-start mb-6">
                      <div>
                        <h3 className="font-semibold text-lg">Artist Registration</h3>
                        <p className="text-sm text-muted-foreground">SoundWars Competition 2025</p>
                      </div>
                      <div className="text-right">
                        <p className="text-3xl font-bold text-accent">{APP_CONFIG.ARTIST_REGISTRATION_FEE_DISPLAY}</p>
                        <p className="text-xs text-muted-foreground">One-time fee</p>
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 text-sm">
                        <Check className="w-4 h-4 text-primary" />
                        <span>Submit your track to the competition</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Check className="w-4 h-4 text-primary" />
                        <span>Get featured on the platform</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Check className="w-4 h-4 text-primary" />
                        <span>Compete for the grand prize</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Check className="w-4 h-4 text-primary" />
                        <span>Artist profile & analytics</span>
                      </div>
                    </div>
                  </div>

                  <Button 
                    variant="hero" 
                    size="lg" 
                    className="w-full"
                    onClick={handlePayment}
                    disabled={isLoading}
                  >
                    {isLoading ? "Redirecting to Payment..." : `Pay ${APP_CONFIG.ARTIST_REGISTRATION_FEE_DISPLAY} with Flutterwave`}
                  </Button>

                  {/* Security Notice */}
                  <div className="flex items-center gap-2 justify-center text-xs text-muted-foreground">
                    <Shield className="w-4 h-4 text-primary" />
                    <span>Secure payment powered by Flutterwave. Your payment information is encrypted.</span>
                  </div>

                  <button 
                    onClick={() => setStep("details")}
                    className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    ← Back to registration details
                  </button>
                </div>
              </motion.div>
            )}

            {step === "blocked" && (
              <motion.div
                key="blocked"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="max-w-md mx-auto text-center"
              >
                <div className="glass rounded-2xl p-8 border border-destructive/30">
                  <div className="w-20 h-20 rounded-full bg-destructive/20 flex items-center justify-center mx-auto mb-6">
                    <AlertTriangle className="w-10 h-10 text-destructive" />
                  </div>
                  
                  <h1 className="font-display text-3xl font-bold mb-3 text-destructive">
                    Contest Entry Blocked
                  </h1>
                  
                  <p className="text-muted-foreground mb-4">
                    Our records show you are a <span className="font-bold text-primary">previous contest winner</span>. 
                  </p>
                  
                  <p className="text-sm text-muted-foreground mb-8">
                    To give other artists a fair chance, past winners cannot participate in contests for {APP_CONFIG.WINNER_CONTEST_COOLDOWN_MONTHS} months after their win. Thank you for your understanding!
                  </p>

                  <div className="space-y-3">
                    <Link to="/">
                      <Button variant="glass" size="lg" className="w-full">
                        Go to Homepage
                      </Button>
                    </Link>
                    <Link to="/leaderboard">
                      <Button variant="outline" size="lg" className="w-full">
                        View Current Contest
                      </Button>
                    </Link>
                  </div>
                </div>
              </motion.div>
            )}

            {step === "success" && (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="max-w-md mx-auto text-center"
              >
                <div className="glass rounded-2xl p-8">
                  <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center mx-auto mb-6">
                    <Check className="w-10 h-10 text-primary" />
                  </div>
                  
                  <h1 className="font-display text-3xl font-bold mb-3">
                    {userType === "artist" ? "Welcome, Artist!" : "Welcome to SoundWars!"}
                  </h1>
                  
                  <p className="text-muted-foreground mb-8">
                    {userType === "artist" 
                      ? "Your registration is complete. You can now upload your track and compete for the title!"
                      : "Your account has been created. Start exploring and vote for your favorite songs!"
                    }
                  </p>

                  <div className="space-y-3">
                    {userType === "artist" ? (
                      <Link to="/submit">
                        <Button variant="hero" size="lg" className="w-full">
                          Upload Your Track
                        </Button>
                      </Link>
                    ) : (
                      <Link to="/leaderboard">
                        <Button variant="hero" size="lg" className="w-full">
                          Browse Songs & Vote
                        </Button>
                      </Link>
                    )}
                    
                    <Link to="/">
                      <Button variant="glass" size="lg" className="w-full">
                        Go to Homepage
                      </Button>
                    </Link>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Register;
