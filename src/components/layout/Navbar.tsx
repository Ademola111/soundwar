import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Music2, Menu, X, Trophy, User, Upload, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useVoting } from "@/hooks/useVoting";
import { useSubmitEligibility } from "@/hooks/useSubmitEligibility";

const navItems = [
  { name: "Home", path: "/" },
  { name: "Leaderboard", path: "/leaderboard", icon: Trophy },
  { name: "Artists", path: "/artists", icon: User },
];

export const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();
  const { voteInfo, isLoading: isVoteStatusLoading } = useVoting();
  const { canSubmitSong } = useSubmitEligibility();
  const visibleNavItems = [
    ...navItems,
    ...(canSubmitSong ? [{ name: "Submit Song", path: "/submit", icon: Upload }] : []),
    ...(isAuthenticated ? [{ name: "My Profile", path: "/profile", icon: LayoutDashboard }] : []),
  ];

  const handleLogout = () => {
    logout();
    setIsOpen(false);
    navigate("/");
  };

  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className="fixed top-0 left-0 right-0 z-50 glass"
    >
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-10 h-10 rounded-lg bg-gradient-primary flex items-center justify-center group-hover:scale-110 transition-transform">
              <Music2 className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-display font-bold text-xl text-foreground">
              SoundWars
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {visibleNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${
                  location.pathname === item.path
                    ? "text-primary bg-primary/10"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                {item.name}
              </Link>
            ))}
          </div>

          {/* Auth Buttons */}
          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated ? (
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                Log Out
              </Button>
            ) : (
              <Link to="/login">
                <Button variant="ghost" size="sm">
                  Sign In
                </Button>
              </Link>
            )}
            {isAuthenticated ? (
              voteInfo.hasVoted ? (
                <Button variant="hero" size="sm" disabled>Voted</Button>
              ) : (
                <Link to="/leaderboard">
                  <Button variant="hero" size="sm" disabled={isVoteStatusLoading}>Vote Now</Button>
                </Link>
              )
            ) : (
              <Link to="/register">
                <Button variant="hero" size="sm">Join Contest</Button>
              </Link>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 text-foreground"
            onClick={() => setIsOpen(!isOpen)}
          >
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="md:hidden glass border-t border-border"
        >
          <div className="container mx-auto px-4 py-4 flex flex-col gap-2">
            {visibleNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  location.pathname === item.path
                    ? "text-primary bg-primary/10"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                {item.name}
              </Link>
            ))}
            <div className="flex gap-2 mt-4 pt-4 border-t border-border">
              {isAuthenticated ? (
                <Button variant="ghost" className="flex-1" onClick={handleLogout}>
                  Log Out
                </Button>
              ) : (
                <Link to="/login" className="flex-1" onClick={() => setIsOpen(false)}>
                  <Button variant="ghost" className="w-full">
                    Sign In
                  </Button>
                </Link>
              )}
              {isAuthenticated ? (
                voteInfo.hasVoted ? (
                  <Button variant="hero" className="flex-1" disabled>Voted</Button>
                ) : (
                  <Link to="/leaderboard" className="flex-1" onClick={() => setIsOpen(false)}>
                    <Button variant="hero" className="w-full" disabled={isVoteStatusLoading}>Vote Now</Button>
                  </Link>
                )
              ) : (
                <Link to="/register" className="flex-1" onClick={() => setIsOpen(false)}>
                  <Button variant="hero" className="w-full">Join Contest</Button>
                </Link>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </motion.nav>
  );
};
