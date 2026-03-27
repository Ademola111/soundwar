import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Clock } from "lucide-react";

interface TimeLeft {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
}

const calculateTimeLeft = (targetDate: Date): TimeLeft => {
  const difference = targetDate.getTime() - new Date().getTime();
  
  if (difference <= 0) {
    return { days: 0, hours: 0, minutes: 0, seconds: 0 };
  }

  return {
    days: Math.floor(difference / (1000 * 60 * 60 * 24)),
    hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((difference / 1000 / 60) % 60),
    seconds: Math.floor((difference / 1000) % 60),
  };
};

interface CountdownTimerProps {
  phase: "registration" | "voting";
  endDate: Date;
}

export const CountdownTimer = ({ phase, endDate }: CountdownTimerProps) => {
  const [timeLeft, setTimeLeft] = useState<TimeLeft>(calculateTimeLeft(endDate));

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft(endDate));
    }, 1000);

    return () => clearInterval(timer);
  }, [endDate]);

  const timeUnits = [
    { label: "Days", value: timeLeft.days },
    { label: "Hours", value: timeLeft.hours },
    { label: "Minutes", value: timeLeft.minutes },
    { label: "Seconds", value: timeLeft.seconds },
  ];

  return (
    <section className="py-20 relative">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-4xl mx-auto text-center"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent/20 text-accent mb-6">
            <Clock className="w-4 h-4" />
            <span className="text-sm font-semibold">
              {phase === "registration" ? "Registration Ends In" : "Voting Ends In"}
            </span>
          </div>

          <h2 className="font-display text-3xl md:text-4xl font-bold mb-8">
            {phase === "registration" 
              ? "Don't Miss Your Chance to Compete!" 
              : "Cast Your Vote Before Time Runs Out!"
            }
          </h2>

          <div className="grid grid-cols-4 gap-4 max-w-2xl mx-auto">
            {timeUnits.map((unit, index) => (
              <motion.div
                key={unit.label}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="glass rounded-2xl p-6 glow-primary"
              >
                <div className="font-display text-4xl md:text-5xl font-bold text-gradient-primary">
                  {String(unit.value).padStart(2, "0")}
                </div>
                <div className="text-sm text-muted-foreground mt-2">{unit.label}</div>
              </motion.div>
            ))}
          </div>

          <p className="text-muted-foreground mt-8">
            {phase === "registration" 
              ? "Submit your track and join 500+ artists competing for the crown"
              : "Every vote counts! Help your favorite artist win"
            }
          </p>
        </motion.div>
      </div>
    </section>
  );
};
