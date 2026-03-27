import { motion } from "framer-motion";
import { Calendar, CheckCircle, Circle, Clock } from "lucide-react";

const phases = [
  {
    title: "Registration Open",
    description: "Artists can sign up and submit their tracks",
    duration: "Month 1-2",
    status: "active" as const,
  },
  {
    title: "Voting Period",
    description: "All users can vote for their favorite song",
    duration: "Month 3",
    status: "upcoming" as const,
  },
  {
    title: "Winner Announcement",
    description: "The champion is crowned!",
    duration: "End of Month 3",
    status: "upcoming" as const,
  },
];

const getStatusIcon = (status: "completed" | "active" | "upcoming") => {
  switch (status) {
    case "completed":
      return <CheckCircle className="w-6 h-6 text-primary" />;
    case "active":
      return <Clock className="w-6 h-6 text-accent animate-pulse" />;
    case "upcoming":
      return <Circle className="w-6 h-6 text-muted-foreground" />;
  }
};

export const ContestTimeline = () => {
  return (
    <section className="py-20 relative">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/20 text-primary mb-6">
            <Calendar className="w-4 h-4" />
            <span className="text-sm font-semibold">3-Month Competition</span>
          </div>
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
            Contest <span className="text-gradient-primary">Timeline</span>
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            A three-month journey from registration to crowning the winner
          </p>
        </motion.div>

        <div className="max-w-3xl mx-auto">
          {phases.map((phase, index) => (
            <motion.div
              key={phase.title}
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.15 }}
              className="relative flex gap-6 pb-12 last:pb-0"
            >
              {/* Timeline Line */}
              {index < phases.length - 1 && (
                <div className="absolute left-[14px] top-8 w-0.5 h-full bg-gradient-to-b from-border to-transparent" />
              )}
              
              {/* Icon */}
              <div className={`relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                phase.status === "active" ? "bg-accent/20 glow-accent" : "bg-muted"
              }`}>
                {getStatusIcon(phase.status)}
              </div>
              
              {/* Content */}
              <div className={`glass rounded-xl p-6 flex-1 ${
                phase.status === "active" ? "border border-accent/50 glow-accent" : ""
              }`}>
                <div className="flex flex-wrap items-center gap-3 mb-2">
                  <h3 className="font-display text-xl font-bold">{phase.title}</h3>
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    phase.status === "active" 
                      ? "bg-accent/20 text-accent" 
                      : "bg-muted text-muted-foreground"
                  }`}>
                    {phase.duration}
                  </span>
                </div>
                <p className="text-muted-foreground">{phase.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
