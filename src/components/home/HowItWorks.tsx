import { motion } from "framer-motion";
import { UserPlus, Upload, Vote, Trophy } from "lucide-react";

const steps = [
  {
    icon: UserPlus,
    title: "Create Account",
    description: "Sign up as an artist to submit songs or as a fan to vote for your favorites",
    color: "from-blue-500 to-cyan-500",
  },
  {
    icon: Upload,
    title: "Submit Your Track",
    description: "Artists upload their best song in MP3 format during the registration phase",
    color: "from-purple-500 to-pink-500",
  },
  {
    icon: Vote,
    title: "Vote for the Best",
    description: "Everyone gets ONE vote. Choose wisely and support your favorite artist",
    color: "from-orange-500 to-red-500",
  },
  {
    icon: Trophy,
    title: "Winner Takes All",
    description: "The song with the most votes at the end wins the SoundWars crown",
    color: "from-yellow-500 to-amber-500",
  },
];

export const HowItWorks = () => {
  return (
    <section className="py-20 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/5 to-transparent" />
      
      <div className="container mx-auto px-4 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
            How <span className="text-gradient-accent">It Works</span>
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Four simple steps to compete or support your favorite artists
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {steps.map((step, index) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className="relative"
            >
              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div className="hidden lg:block absolute top-12 left-[60%] w-[80%] h-0.5 bg-gradient-to-r from-border to-transparent" />
              )}
              
              <div className="text-center">
                {/* Step Number */}
                <div className="text-6xl font-display font-bold text-muted/30 mb-4">
                  {String(index + 1).padStart(2, "0")}
                </div>
                
                {/* Icon */}
                <div className={`w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center mb-4 shadow-lg`}>
                  <step.icon className="w-8 h-8 text-white" />
                </div>
                
                {/* Content */}
                <h3 className="font-display text-xl font-bold mb-2">{step.title}</h3>
                <p className="text-muted-foreground text-sm">{step.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
