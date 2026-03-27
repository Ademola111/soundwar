import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { HeroSection } from "@/components/home/HeroSection";
import { CountdownTimer } from "@/components/home/CountdownTimer";
import { FeaturedSongs } from "@/components/home/FeaturedSongs";
import { HowItWorks } from "@/components/home/HowItWorks";
import { ContestTimeline } from "@/components/home/ContestTimeline";

// Contest end date - 2 months from now for registration
const registrationEndDate = new Date();
registrationEndDate.setMonth(registrationEndDate.getMonth() + 2);

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <HeroSection />
        <CountdownTimer phase="registration" endDate={registrationEndDate} />
        <FeaturedSongs />
        <HowItWorks />
        <ContestTimeline />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
