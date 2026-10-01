import { useEffect, useState } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { HeroSection } from "@/components/home/HeroSection";
import { CountdownTimer } from "@/components/home/CountdownTimer";
import { FeaturedSongs } from "@/components/home/FeaturedSongs";
import { HowItWorks } from "@/components/home/HowItWorks";
import { ContestTimeline } from "@/components/home/ContestTimeline";
import { API_ENDPOINTS } from "@/config/api";

type ScheduleState = "loading" | "ready" | "no-contest" | "unavailable";

const Index = () => {
  const [registrationEndDate, setRegistrationEndDate] = useState<Date | null>(null);
  const [scheduleState, setScheduleState] = useState<ScheduleState>("loading");

  useEffect(() => {
    const controller = new AbortController();

    const loadContestSchedule = async () => {
      try {
        const response = await fetch(API_ENDPOINTS.LEADERBOARD.BASE, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Failed to load contest schedule");

        const data = await response.json() as {
          contest: { submission_end_date?: string } | null;
        };

        if (!data.contest) {
          setScheduleState("no-contest");
          return;
        }

        const endDate = new Date(data.contest.submission_end_date || "");
        if (Number.isNaN(endDate.getTime())) {
          setScheduleState("unavailable");
          return;
        }

        setRegistrationEndDate(endDate);
        setScheduleState("ready");
      } catch {
        if (!controller.signal.aborted) setScheduleState("unavailable");
      }
    };

    void loadContestSchedule();
    return () => controller.abort();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <HeroSection />
        {scheduleState === "ready" && registrationEndDate ? (
          <CountdownTimer phase="registration" endDate={registrationEndDate} />
        ) : scheduleState === "loading" ? (
          <section className="py-20 text-center text-muted-foreground" role="status">
            Loading registration schedule...
          </section>
        ) : (
          <section className="py-20 text-center">
            <h2 className="font-display text-2xl font-bold mb-2">
              {scheduleState === "no-contest" ? "No Active Contest" : "Registration Schedule Unavailable"}
            </h2>
            <p className="text-muted-foreground">
              {scheduleState === "no-contest"
                ? "There is no active contest registration period right now."
                : "The registration deadline could not be loaded. Please try again later."}
            </p>
          </section>
        )}
        <FeaturedSongs />
        <HowItWorks />
        <ContestTimeline />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
